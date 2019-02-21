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

from io import BytesIO
from scar.parser.cfgfile import ConfigFileParser
from zipfile import ZipFile
import scar.http.request as request
import scar.utils as utils

def udocker_env(func):
    '''
    Decorator used to avoid losing the definition of the udocker
    environment variables (if the are any) 
    '''
    def wrapper(*args, **kwargs):
        Udocker.save_tmp_udocker_env()
        func(*args, **kwargs)
        Udocker.restore_udocker_env()
    return wrapper

class Udocker():
    
    # Needed here to store the config dir location
    # when overriding udocker config
    udocker_dir = ""
    udocker_tmp_folder =  utils.create_tmp_dir()
    udocker_tmp_folder_path = udocker_tmp_folder.name 
    udocker_install_dir = utils.join_paths(udocker_tmp_folder_path, "udocker")    

    def __init__(self, aws_properties):
        self.aws = aws_properties
        self._initialize_udocker()
        
    def _initialize_udocker(self):
        self.udocker_code = utils.join_paths(self.udocker_install_dir, "udocker.py")
        self.udocker_exec = ['python3', self.udocker_code]
        self._install_udocker()               
    
    def _install_udocker(self):
        with ZipFile(BytesIO(self._download_udocker_zip())) as thezip:
            thezip.extractall(self.udocker_tmp_folder_path)

    def _download_udocker_zip(self):
        return request.get_file(ConfigFileParser().get_udocker_zip_url())  

    @classmethod
    def save_tmp_udocker_env(cls):
        #Avoid override global variables
        if utils.is_variable_in_environment("UDOCKER_DIR"):
            cls.udocker_dir = utils.get_environment_variable("UDOCKER_DIR")
        # Set temporal global vars
        utils.set_environment_variable("UDOCKER_DIR", cls.udocker_install_dir)
 
    @classmethod        
    def restore_udocker_env(cls):
        if cls.udocker_dir:
            utils.set_environment_variable("UDOCKER_DIR")
        else:
            utils.delete_environment_variable("UDOCKER_DIR")   

    def _set_udocker_local_registry(self):
        self.aws._lambda.environment['Variables']['UDOCKER_REPOS'] = '/var/task/udocker/repos/'
        self.aws._lambda.environment['Variables']['UDOCKER_LAYERS'] = '/var/task/udocker/layers/'

    @udocker_env         
    def download_udocker_image(self):
        utils.execute_command_with_msg(self.udocker_exec + ["pull", self.aws._lambda.image],
                                       cli_msg="Downloading container image")
        self._create_udocker_container()
        self._set_udocker_local_registry()
        
    def _create_udocker_container(self):
        '''
        Check if the container fits in the limits of the S3 deployments.
        '''
        if(utils.get_tree_size(self.udocker_install_dir) < self.aws._lambda.max_s3_payload_size/2):
            utils.execute_command_with_msg(self.udocker_exec + ["create", "--name=lambda_cont", self.aws._lambda.image],
                                           cli_msg="Creating container structure")
        if(utils.get_tree_size(self.udocker_install_dir) > self.aws._lambda.max_s3_payload_size):
            utils.delete_folder(utils.join_paths(self.udocker_install_dir, "containers"))
         
    @udocker_env        
    def prepare_udocker_image(self):
        image_path = utils.join_paths(self.udocker_tmp_folder_path, "udocker_image.tar.gz")
        utils.copy_file(self.aws._lambda.image_file, image_path)
        self.aws._lambda.image = utils.execute_command_with_msg(self.udocker_exec + ["load", "-i", image_path],
                                                                cli_msg="Loading image file")
        self._create_udocker_container()
        self.aws._lambda.environment['Variables']['IMAGE_ID'] = self.aws._lambda.image
        self._set_udocker_local_registry()        
