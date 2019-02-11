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

from distutils import dir_util
from scar.providers.aws.validators import AWSValidator
from zipfile import ZipFile
import io
import os
import scar.exceptions as excp
import scar.http.request as request
import scar.logger as logger
import scar.utils as utils
import shutil
import subprocess

MAX_PAYLOAD_SIZE = 50 * 1024 * 1024
MAX_S3_PAYLOAD_SIZE = 250 * 1024 * 1024

def udocker_env(func):
    '''
    Decorator used to avoid losing the definition of the udocker
    environment variables (if any) 
    '''
    def wrapper(*args, **kwargs):
        FunctionPackageCreator.save_tmp_udocker_env()
        func(*args, **kwargs)
        FunctionPackageCreator.restore_udocker_env()
    return wrapper

class FunctionPackageCreator():
    
    udocker_url = 'https://github.com/grycap/faas-supervisor/raw/master/extra/udocker.zip'
    
    aws_src_path = os.path.dirname(os.path.abspath(__file__))
    lambda_code_file_path = utils.join_paths(aws_src_path, "cloud")
    function_handler_source = utils.join_paths(lambda_code_file_path, "function_handler.py")
    udocker_zip_path = utils.join_paths(lambda_code_file_path, "layer", "udocker.zip")    
    udocker_tarball = ""
    udocker_dir = ""
    init_script_name = "init_script.sh"
    init_script_path = "/var/task/{0}".format(init_script_name)
    extra_payload_path = "/var/task"
    
    def __init__(self, package_props):
        self.properties  = package_props
        
        self.scar_tmp_folder =  utils.create_tmp_dir()
        self.scar_tmp_folder_path =  self.scar_tmp_folder.name
        self.udocker_tmp_folder =  utils.create_tmp_dir()
        self.udocker_tmp_folder_path = self.udocker_tmp_folder.name
        
        self.udocker_dest = utils.join_paths(self.udocker_tmp_folder_path, "udockerb")
        self.udocker_exec = [self.udocker_dest]
            
        self.function_handler_name = "{0}.py".format(self.properties['FunctionName'])
        self.function_handler_dest = utils.join_paths(self.scar_tmp_folder_path, self.function_handler_name)
    
    @excp.exception(logger)
    def prepare_lambda_code(self):
        self.clean_tmp_folders()
        self.add_mandatory_files()
        
        self.install_tmp_udocker();
        if 'DeploymentBucket' in self.properties and 'ImageId' in self.properties:
            self.download_udocker_image()
        if 'ImageFile' in self.properties:
            self.prepare_udocker_image()
            
        self.add_init_script() 
        self.add_extra_payload()
        self.zip_scar_folder()
        self.check_code_size()

    def install_tmp_udocker(self):
        udocker_zip = request.get_file(self.udocker_url)
        with ZipFile(io.BytesIO(udocker_zip)) as thezip:
            thezip.extractall(self.udocker_tmp_folder_path)

    def add_mandatory_files(self):
        shutil.copy(utils.resource_path(self.function_handler_source), self.function_handler_dest)
        utils.execute_command(['chmod', '0664', self.function_handler_dest])
     
    @udocker_env     
    def create_udocker_files(self):
        self.execute_command(self.udocker_exec + ["help"], cli_msg="Packing udocker files")
     
    def add_init_script(self):
        if 'Script' in self.properties:
            shutil.copy(self.properties['Script'], utils.join_paths(self.scar_tmp_folder_path, self.init_script_name))
            self.properties['EnvironmentVariables']['INIT_SCRIPT_PATH'] = self.init_script_path        
     
    def add_extra_payload(self):
        if 'ExtraPayload' in self.properties:
            logger.info("Adding extra payload from {0}".format(self.properties['ExtraPayload']))
            dir_util.copy_tree(self.properties['ExtraPayload'], self.scar_tmp_folder_path)
            self.set_environment_variable('EXTRA_PAYLOAD', self.extra_payload_path)         
        
    def check_code_size(self):
        # Check if the code size fits within the aws limits   
        if 'DeploymentBucket' in self.properties:
            AWSValidator.validate_s3_code_size(self.scar_tmp_folder_path, MAX_S3_PAYLOAD_SIZE)
        else:
            AWSValidator.validate_function_code_size(self.scar_tmp_folder_path, MAX_PAYLOAD_SIZE)        

    def clean_tmp_folders(self):
        if os.path.isfile(self.properties['ZipFilePath']):    
            utils.delete_file(self.properties['ZipFilePath'])

    def zip_scar_folder(self):
        zip_exe = utils.resource_path("src/bin/zip", bin_path='/usr/bin/zip')
        self.execute_command([zip_exe, "-r9y", self.properties['ZipFilePath'], "."],
                             cmd_wd=self.scar_tmp_folder_path,
                             cli_msg="Creating function package")

    @classmethod
    def save_tmp_udocker_env(cls):
        #Avoid override global variables
        if utils.is_value_in_dict(os.environ, 'UDOCKER_DIR'):
            cls.udocker_dir = os.environ['UDOCKER_DIR']
        # Set temporal global vars
        utils.set_environment_variable('UDOCKER_DIR', cls.udocker_tmp_folder_path)

    @classmethod        
    def restore_udocker_env(cls):
        cls.restore_environ_var('UDOCKER_DIR', cls.udocker_dir)
        
    @classmethod
    def restore_environ_var(cls, key, var):
        if var:
            utils.set_environment_variable(key, var)
        else:
            del os.environ[key]
        
    def execute_command(self, command, cmd_wd=None, cli_msg=None):
        cmd_out = subprocess.check_output(command, cwd=cmd_wd).decode("utf-8")
        logger.info(cli_msg, cmd_out)
        return cmd_out[:-1]
        
    @udocker_env        
    def prepare_udocker_image(self):
        image_path = utils.join_paths(self.os_tmp_folder, "udocker_image.tar.gz")
        shutil.copy(self.properties['ImageFile'], image_path)
        cmd_out = self.execute_command(self.udocker_exec + ["load", "-i", image_path], cli_msg="Loading image file")
        self.create_udocker_container(cmd_out)
        self.set_environment_variable('IMAGE_ID', cmd_out)
        self.set_udocker_local_registry()
    
    @udocker_env         
    def download_udocker_image(self):
        self.execute_command(self.udocker_exec + ["pull", self.properties['ImageId']], cli_msg="Downloading container image")
        self.create_udocker_container(self.properties['ImageId'])
        self.set_udocker_local_registry()
        
    def create_udocker_container(self, image_id):
        if(utils.get_tree_size(self.scar_tmp_folder_path) < MAX_S3_PAYLOAD_SIZE/2):
            self.execute_command(self.udocker_exec + ["create", "--name=lambda_cont", image_id], cli_msg="Creating container structure")
        if(utils.get_tree_size(self.scar_tmp_folder_path) > MAX_S3_PAYLOAD_SIZE):
            shutil.rmtree(utils.join_paths(self.scar_tmp_folder_path, "udocker/containers/"))        
        
    def set_udocker_local_registry(self):
        self.set_environment_variable('UDOCKER_REPOS', '/var/task/udocker/repos/')
        self.set_environment_variable('UDOCKER_LAYERS', '/var/task/udocker/layers/')        

    def set_environment_variable(self, key, val):
        if key and val:
            self.properties['EnvironmentVariables'][key] = val
