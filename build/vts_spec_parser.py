#!/usr/bin/env python3.4
#
# Copyright (C) 2017 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import fnmatch
import os
import shutil
import subprocess
import sys

# TODO(trong): use proper packaging without referencing modules from source.
ANDROID_BUILD_TOP = os.environ.get('ANDROID_BUILD_TOP')
if not ANDROID_BUILD_TOP:
    print 'Run "lunch" command first.'
    sys.exit(1)

TEST_VTS_DIR = os.path.join(ANDROID_BUILD_TOP, 'test', 'vts')
sys.path.append(TEST_VTS_DIR)
from proto import ComponentSpecificationMessage_pb2 as CompSpecMsg
from google.protobuf import text_format


class VtsSpecParser(object):
    """Provides an API to generate a parse .vts spec files."""
    HW_IFACE_DIR = os.path.join(ANDROID_BUILD_TOP, 'hardware', 'interfaces')

    def __init__(self, tmp_dir='./tmp'):
        """VtsSpecParser constructor.

        For every unique pair of (hal name, hal version) available under
        hardware/interfaces, generates .vts files using hidl-gen.

        Args:
            tmp_dir: string, temporary directory to which to write .vts files.
        """
        self._tmp_dir = tmp_dir
        hal_list = self.HalNamesAndVersions()

        print "Generating .vts specs."
        for target in hal_list:
            hal_name = target[0]
            hal_version = target[1]
            self.GenerateVtsSpecs(hal_name, hal_version)

    def __del__(self):
        """VtsSpecParser destructor.

        Removes all temporary files that were generated.
        """
        print "Removing temp files."
        if os.path.exists(self._tmp_dir):
            shutil.rmtree(self._tmp_dir)

    def GenerateVtsSpecs(self, hal_name, hal_version):
        """Generates VTS specs.

        Uses hidl-gen to generate .vts files under a tmp directory.

        Args:
          hal_name: string, name of the hal, e.g. 'vibrator'.
          hal_version: string, version of the hal, e.g '7.4'
          tmp_dir: string, location to which to write tmp files.
        """
        hidl_gen_cmd = ('hidl-gen -o {TEMP_DIR} -L vts '
                        '-r android.hardware:{HW_IFACE_DIR} '
                        '-r android.hidl:{ANDROID_BUILD_TOP}/system/libhidl/transport '
                        'android.hardware.{HAL_NAME}@{HAL_VERSION}').format(
                            TEMP_DIR=self._tmp_dir,
                            HW_IFACE_DIR=self.HW_IFACE_DIR,
                            ANDROID_BUILD_TOP=ANDROID_BUILD_TOP,
                            HAL_NAME=hal_name,
                            HAL_VERSION=hal_version)
        subprocess.call(hidl_gen_cmd, shell=True)

    def HalNamesAndVersions(self):
        """Returns a list of hals and version present under hardware/interfaces.

        Returns:
          List of tuples of strings containing hal names and hal versions.
          For example, [('vibrator', '1.3'), ('sensors', '1.7')]
        """
        result = []
        for base, dirs, files in os.walk(self.HW_IFACE_DIR):
            pattern = self.HW_IFACE_DIR + '*/[0-9].[0-9]'
            if fnmatch.fnmatch(base, pattern) and 'example' not in base:
                hal_dir = os.path.relpath(base, self.HW_IFACE_DIR)
                (hal_name, hal_version) = os.path.split(hal_dir)
                hal_name = hal_name.replace('/', '.')
                result.append((hal_name, hal_version))
        return sorted(result)

    def VtsSpecNames(self, hal_name, hal_version):
        """Returns list of .vts file names for given hal name and version.

        hal_name: string, name of the hal, e.g. 'vibrator'.
        hal_version: string, version of the hal, e.g '7.4'

        Returns:
          list of string, .vts files for given hal name and version,
              e.g. ['Vibrator.vts', 'types.vts']
        """
        vts_spec_dir = os.path.join(self._tmp_dir, 'android', 'hardware',
                                    hal_name.replace('.', '/'), hal_version)
        vts_spec_names = filter(lambda x: x.endswith('.vts'),
                                os.listdir(vts_spec_dir))
        return sorted(vts_spec_names)

    def VtsSpecProtos(self, hal_name, hal_version):
        """Returns list of .vts protos for given hal name and version.

        hal_name: string, name of the hal, e.g. 'vibrator'.
        hal_version: string, version of the hal, e.g '7.4'

        Returns:
          list of ComponentSpecificationMessages
        """
        vts_spec_dir = os.path.join(self._tmp_dir, 'android', 'hardware',
                                    hal_name.replace('.', '/'), hal_version)
        vts_spec_protos = []
        for vts_spec in self.VtsSpecNames(hal_name, hal_version):
            spec_proto = CompSpecMsg.ComponentSpecificationMessage()
            vts_spec_path = os.path.join(vts_spec_dir, vts_spec)
            with open(vts_spec_path, 'r') as spec_file:
                spec_string = spec_file.read()
                text_format.Merge(spec_string, spec_proto)

            vts_spec_protos.append(spec_proto)
        return vts_spec_protos
