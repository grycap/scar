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
"""Module with methods and classes to create the function deployment package."""

from zipfile import ZipFile
from scar.providers.aws.udocker import Udocker
from scar.providers.aws.validators import AWSValidator
from scar.exceptions import exception
import scar.logger as logger
from scar.http.request import get_file
from scar.utils import FileUtils, lazy_property, GitHubUtils, \
                       GITHUB_USER, GITHUB_SUPERVISOR_PROJECT


_INIT_SCRIPT_NAME = "init_script.sh"


class FunctionPackager():
    """Class to manage the deployment package creation."""

    @lazy_property
    def udocker(self):
        """Udocker client"""
        udocker = Udocker(self.aws, self.scar_tmp_function_folder_path, self._supervisor_zip_path)
        return udocker

    def __init__(self, aws_properties):
        self.aws = aws_properties
#         self.scar_tmp_function_folder = FileUtils.create_tmp_dir()
#         self.scar_tmp_function_folder_path = self.scar_tmp_function_folder.name
#         self._supervisor_zip_path = FileUtils.join_paths(self.aws.lambdaf.tmp_folder_path, 'faas.zip')
        self.package_args = {}

    @exception(logger)
    def create_zip(self, tmp_folder):
        """Creates the lambda function deployment package."""
        zip_path = FileUtils.join_paths(tmp_folder, 'faas.zip')
        self._download_faas_supervisor_zip(zip_path)
        self._extract_handler_code(tmp_folder, zip_path)
        self._manage_udocker_images()
        self._add_init_script()
        self._add_extra_payload()
        self._zip_scar_folder()
        self._check_code_size()
        return zip_path

    def _download_faas_supervisor_zip(self, zip_path) -> None:
        supervisor_zip_url = GitHubUtils.get_source_code_url(
            GITHUB_USER,
            GITHUB_SUPERVISOR_PROJECT,
            self.aws.get('lambda').get('supervisor').get('version'))
        with open(zip_path, "wb") as thezip:
            thezip.write(get_file(supervisor_zip_url))

    def _extract_handler_code(self, tmp_folder, zip_path) -> None:
        function_handler_dest = FileUtils.join_paths(tmp_folder,
                                                     f"{self.aws.get('lambda').get('name')}.py")
        file_path = ""
        with ZipFile(zip_path) as thezip:
            for file in thezip.namelist():
                if file.endswith("function_handler.py"):
                    file_path = FileUtils.join_paths(tmp_folder, file)
                    thezip.extract(file, tmp_folder)
                    break
        FileUtils.copy_file(file_path, function_handler_dest)

    def _manage_udocker_images(self):
        if hasattr(self.aws.lambdaf, "image") and \
           hasattr(self.aws, "s3") and \
           hasattr(self.aws.s3, "deployment_bucket"):
            self.udocker.download_udocker_image()
        if hasattr(self.aws.lambdaf, "image_file"):
            if hasattr(self.aws, "config_path"):
                self.aws.lambdaf.image_file = FileUtils.join_paths(self.aws.config_path,
                                                                   self.aws.lambdaf.image_file)
            self.udocker.prepare_udocker_image()

    def _add_init_script(self):
        if hasattr(self.aws.lambdaf, "init_script"):
            if hasattr(self.aws, "config_path"):
                self.aws.lambdaf.init_script = FileUtils.join_paths(self.aws.config_path,
                                                                    self.aws.lambdaf.init_script)
            FileUtils.copy_file(self.aws.lambdaf.init_script,
                                FileUtils.join_paths(self.scar_tmp_function_folder_path, _INIT_SCRIPT_NAME))
            self.aws.lambdaf.environment['Variables']['INIT_SCRIPT_PATH'] = \
                                        f"/var/task/{_INIT_SCRIPT_NAME}"

    def _add_extra_payload(self):
        if hasattr(self.aws.lambdaf, "extra_payload"):
            logger.info("Adding extra payload from {0}".format(self.aws.lambdaf.extra_payload))
            FileUtils.copy_dir(self.aws.lambdaf.extra_payload, self.scar_tmp_function_folder_path)
            self.aws.lambdaf.environment['Variables']['EXTRA_PAYLOAD'] = "/var/task"

    def _zip_scar_folder(self):
        FileUtils.zip_folder(self.aws.lambdaf.zip_file_path,
                             self.scar_tmp_function_folder_path,
                             "Creating function package")

    def _check_code_size(self):
        # Check if the code size fits within the AWS limits
        if hasattr(self.aws, "s3") and hasattr(self.aws.s3, "deployment_bucket"):
            AWSValidator.validate_s3_code_size(self.scar_tmp_function_folder_path,
                                               self.aws.lambdaf.max_s3_payload_size)
        else:
            AWSValidator.validate_function_code_size(self.scar_tmp_function_folder_path,
                                                     self.aws.lambdaf.max_payload_size)
