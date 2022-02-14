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
from _ast import Or
"""Module with methods and classes to create the function deployment package."""

from typing import Dict
from zipfile import ZipFile
import ntpath
from scar.providers.aws.udocker import Udocker
from scar.providers.aws.validators import AWSValidator
from scar.exceptions import exception
import scar.logger as logger
from scar.utils import FileUtils

def clean_function_config(function_cfg: Dict):
    # Rm full path from the init_script
    if 'init_script' in function_cfg and function_cfg.get('init_script', True):
        function_cfg['init_script'] = ntpath.basename(function_cfg['init_script'])
    # Rm the config path
    function_cfg.pop('config_path', None)
    return function_cfg

def create_function_config(resources_info):
    function_cfg = {'storage_providers': FileUtils.load_tmp_config_file().get('storage_providers', {})}
    function_cfg.update(resources_info.get('lambda'))
    clean_function_config(function_cfg)
    # Add Batch specific info
    if resources_info.get('lambda').get("execution_mode") == "batch":
        function_cfg.update({"batch": {
                             "multi_node_parallel": resources_info.get('batch').get("multi_node_parallel")
                             }})
    # Add ECR specific info
    if resources_info.get('lambda').get('runtime') == "image" and resources_info.get('ecr', {}).get("delete_image") is not None:
        function_cfg.update({"ecr": {
                             "delete_image": resources_info.get('ecr').get("delete_image")
                             }})
    return function_cfg


class FunctionPackager():
    """Class to manage the deployment package creation."""

    def __init__(self, resources_info: Dict, supervisor_zip_path: str):
        self.resources_info = resources_info
        self.supervisor_zip_path = supervisor_zip_path
        # Temporal folder to store the supervisor and udocker files
        self.tmp_payload_folder = FileUtils.create_tmp_dir()

    @exception(logger)
    def create_zip(self, lambda_payload_path: str) -> None:
        """Creates the lambda function deployment package."""
        self._extract_handler_code()
        self._manage_udocker_images()
        self._add_init_script()
        self._add_extra_payload()
        self._copy_function_configuration()
        self._zip_scar_folder(lambda_payload_path)
        self._check_code_size()

    def _extract_handler_code(self) -> None:
        function_handler_dest = FileUtils.join_paths(self.tmp_payload_folder.name, f"{self.resources_info.get('lambda').get('name')}.py")
        file_path = ""
        with ZipFile(self.supervisor_zip_path) as thezip:
            for file in thezip.namelist():
                if file.endswith("function_handler.py"):
                    file_path = FileUtils.join_paths(FileUtils.get_tmp_dir(), file)
                    # Extracts the complete folder structure and the file (cannot avoid)
                    thezip.extract(file, FileUtils.get_tmp_dir())
                    break
        if file_path:
            # Copy only the handler to the payload folder
            FileUtils.copy_file(file_path, function_handler_dest)

    def _copy_function_configuration(self):
        cfg_file_path = FileUtils.join_paths(self.tmp_payload_folder.name, "function_config.yaml")
        function_cfg = create_function_config(self.resources_info)
        FileUtils.write_yaml(cfg_file_path, function_cfg)

    def _manage_udocker_images(self):
        if self.resources_info.get('lambda').get('container').get('image_file', False) or \
           self.resources_info.get('lambda').get('deployment').get('bucket', False):
            Udocker(self.resources_info, self.tmp_payload_folder.name, self.supervisor_zip_path).prepare_udocker_image()

    def _add_init_script(self) -> None:
        """Copy the init script defined by the user to the payload folder."""
        if self.resources_info.get('lambda').get('init_script', False):
            init_script_path = self.resources_info.get('lambda').get('init_script')
            FileUtils.copy_file(init_script_path,
                                FileUtils.join_paths(self.tmp_payload_folder.name,
                                                     FileUtils.get_file_name(init_script_path)))

    def _add_extra_payload(self) -> None:
        if self.resources_info.get('lambda').get('extra_payload', False):
            payload_path = self.resources_info.get('lambda').get('extra_payload')
            logger.info(f"Adding extra payload '{payload_path}'")
            if FileUtils.is_file(payload_path):
                FileUtils.copy_file(self.resources_info.get('lambda').get('extra_payload'),
                                    self.tmp_payload_folder.name)
            else:
                FileUtils.copy_dir(self.resources_info.get('lambda').get('extra_payload'),
                                   self.tmp_payload_folder.name)
            del(self.resources_info['lambda']['extra_payload'])

    def _zip_scar_folder(self, lambda_payload_path: str) -> None:
        """Zips the tmp folder with all the function's files and
        save it in the expected path of the payload."""
        FileUtils.zip_folder(lambda_payload_path,
                             self.tmp_payload_folder.name,
                             "Creating function package.")

    def _check_code_size(self):
        # Check if the code size fits within the AWS limits
        if self.resources_info.get('lambda').get('deployment').get('bucket', False):
            AWSValidator.validate_s3_code_size(self.tmp_payload_folder.name,
                                               self.resources_info.get('lambda').get('deployment').get('max_s3_payload_size'))
        else:
            AWSValidator.validate_function_code_size(self.tmp_payload_folder.name,
                                                     self.resources_info.get('lambda').get('deployment').get('max_payload_size'))
