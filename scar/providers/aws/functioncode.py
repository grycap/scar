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

from scar.providers.aws.udocker import Udocker
from scar.providers.aws.validators import AWSValidator
import scar.exceptions as excp
import scar.logger as logger
import scar.utils as utils

class FunctionPackager():
    
    @utils.lazy_property
    def udocker(self):
        udocker = Udocker(self.aws, self.scar_tmp_folder_path)
        return udocker
    
    def __init__(self, aws_properties):
        self.aws = aws_properties
        self._initialize_paths()
        
    def _initialize_paths(self):
        self.scar_tmp_folder =  utils.create_tmp_dir()
        self.scar_tmp_folder_path =  self.scar_tmp_folder.name
        self.function_handler_source = utils.join_paths(utils.get_scar_root_path(), "scar", "providers", "aws", "cloud", "function_handler.py")        
        self.function_handler_name = "{0}.py".format(self.aws._lambda.name)
        self.function_handler_dest = utils.join_paths(self.scar_tmp_folder_path, self.function_handler_name)
        self.package_args = {}
    
    @excp.exception(logger)
    def create_zip(self):
        self._clean_tmp_folders()
        self._add_mandatory_files()
        self._manage_udocker_images()
        self._add_init_script() 
        self._add_extra_payload()
        self._zip_scar_folder()
        self._check_code_size()
        #self._clean_tmp_folders()

    def _clean_tmp_folders(self):
        utils.delete_file(self.aws._lambda.zip_file_path)

    def _add_mandatory_files(self):
        '''Copy function handler'''
        utils.copy_file(self.function_handler_source, self.function_handler_dest)
        #utils.execute_command(['chmod', '0664', self.function_handler_dest])
     
    def _manage_udocker_images(self):
        if hasattr(self.aws._lambda, "image") and \
           hasattr(self.aws, "s3") and \
           hasattr(self.aws.s3, "deployment_bucket"):
            self.udocker.download_udocker_image()
        if hasattr(self.aws._lambda, "image_file"):
            if hasattr(self.aws, "config_path"):
                self.aws._lambda.image_file = utils.join_paths(self.aws.config_path, self.aws._lambda.image_file)
            self.udocker.prepare_udocker_image()        
     
    def _add_init_script(self):
        if hasattr(self.aws._lambda, "init_script"):
            if hasattr(self.aws, "config_path"):
                self.aws._lambda.init_script = utils.join_paths(self.aws.config_path, self.aws._lambda.init_script)
            init_script_name = "init_script.sh"
            utils.copy_file(self.aws._lambda.init_script, utils.join_paths(self.scar_tmp_folder_path, init_script_name))
            self.aws._lambda.environment['Variables']['INIT_SCRIPT_PATH'] = "/var/task/{0}".format(init_script_name)
     
    def _add_extra_payload(self):
        if hasattr(self.aws._lambda, "extra_payload"):
            logger.info("Adding extra payload from {0}".format(self.aws._lambda.extra_payload))
            utils.copy_dir(self.aws._lambda.extra_payload, self.scar_tmp_folder_path)
            self.aws._lambda.environment['Variables']['EXTRA_PAYLOAD'] = "/var/task"
        
    def _zip_scar_folder(self):
        utils.zip_folder(self.aws._lambda.zip_file_path, self.scar_tmp_folder_path, "Creating function package")
        
    def _check_code_size(self):
        # Check if the code size fits within the AWS limits   
        if hasattr(self.aws, "s3") and hasattr(self.aws.s3, "deployment_bucket"):
            AWSValidator.validate_s3_code_size(self.scar_tmp_folder_path, self.aws._lambda.max_s3_payload_size)
        else:
            AWSValidator.validate_function_code_size(self.scar_tmp_folder_path, self.aws._lambda.max_payload_size)        
