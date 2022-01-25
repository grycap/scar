# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zipfile import ZipFile
from scar.utils import FileUtils, SysUtils


def _extract_udocker_zip(supervisor_zip_path) -> None:
    file_path = ""
    with ZipFile(supervisor_zip_path) as thezip:
        for file in thezip.namelist():
            if file.endswith("udocker.zip"):
                file_path = FileUtils.join_paths(FileUtils.get_tmp_dir(), file)
                thezip.extract(file, FileUtils.get_tmp_dir())
                break
    return file_path


class Udocker():

    _CONTAINER_NAME = "udocker_container"

    def __init__(self, resources_info: str, tmp_payload_folder_path: str, supervisor_zip_path: str):
        self.resources_info = resources_info
        self._tmp_payload_folder_path = tmp_payload_folder_path
        self._udocker_dir = FileUtils.join_paths(self._tmp_payload_folder_path, "udocker")
        self._udocker_dir_orig = ""
        self._udocker_code = FileUtils.join_paths(self._udocker_dir, "udocker.py")
        self._udocker_exec = ['python3', self._udocker_code]
        self._install_udocker(supervisor_zip_path)

    def _install_udocker(self, supervisor_zip_path: str) -> None:
        udocker_zip_path = _extract_udocker_zip(supervisor_zip_path)
        with ZipFile(udocker_zip_path) as thezip:
            thezip.extractall(self._tmp_payload_folder_path)

    def _save_tmp_udocker_env(self):
        # Avoid override global variables
        if SysUtils.is_variable_in_environment("UDOCKER_DIR"):
            self._udocker_dir_orig = SysUtils.get_environment_variable("UDOCKER_DIR")
        # Set temporal global vars
        SysUtils.set_environment_variable("UDOCKER_DIR", self._udocker_dir)

    def _restore_udocker_env(self):
        if self._udocker_dir_orig:
            SysUtils.set_environment_variable("UDOCKER_DIR", self._udocker_dir_orig)
        else:
            SysUtils.delete_environment_variable("UDOCKER_DIR")

    def _set_udocker_local_registry(self):
        self.resources_info['lambda']['environment']['Variables']['UDOCKER_REPOS'] = '/var/task/udocker/repos/'
        self.resources_info['lambda']['environment']['Variables']['UDOCKER_LAYERS'] = '/var/task/udocker/layers/'


    def prepare_udocker_image(self):
        self._save_tmp_udocker_env()
        cmd_out = SysUtils.execute_command_with_msg(self._udocker_exec + ["load", "-i",
                                                                          self.resources_info.get('lambda').get('container').get('image_file')],
                                                    cli_msg="Loading image file")
        # Get the image name from the command output
        self.resources_info['lambda']['container']['image'] = cmd_out.split('\n')[1]
        self._set_udocker_local_registry()
        self._restore_udocker_env()
