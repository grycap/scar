# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import shutil
import src.logger as logger
import src.utils as utils
import subprocess
import tempfile
from distutils import dir_util
import src.exceptions as excp
from src.providers.aws.validators import AWSValidator

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
    
    src_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    aws_src_path = os.path.dirname(os.path.abspath(__file__))
    lambda_code_files_path = utils.join_paths(aws_src_path, "cloud/lambda/")
    os_tmp_folder = tempfile.gettempdir()
    scar_temporal_folder = utils.join_paths(os_tmp_folder, "scar/")
    
    supervisor_source = utils.join_paths(lambda_code_files_path, "scarsupervisor.py")
    
    udocker_file = "udockerb" if utils.is_binary_execution() else "udockerpy"
    udocker_source = utils.join_paths(lambda_code_files_path, udocker_file)
    udocker_dest = utils.join_paths(scar_temporal_folder, "udockerb")
    
    udocker_exec = [udocker_dest]
    udocker_tarball = ""
    udocker_dir = ""
    init_script_name = "init_script.sh"
    init_script_path = "/var/task/{0}".format(init_script_name)
    extra_payload_path = "/var/task"
    
    def __init__(self, package_props):
        self.properties  = package_props
        self.lambda_code_name = "{0}.py".format(self.properties['FunctionName'])
        self.supervisor_dest = utils.join_paths(self.scar_temporal_folder, self.lambda_code_name)
    
    @excp.exception(logger)
    def prepare_lambda_code(self):
        self.clean_tmp_folders()
        self.add_mandatory_files()
        
        if 'DeploymentBucket' in self.properties and 'ImageId' in self.properties:
            self.download_udocker_image()
        if 'ImageFile' in self.properties:
            self.prepare_udocker_image()
            
        self.add_init_script() 
        self.add_extra_payload()
        self.zip_scar_folder()
        self.check_code_size()

    def add_mandatory_files(self):
        os.makedirs(self.scar_temporal_folder, exist_ok=True)
        shutil.copy(utils.resource_path(self.supervisor_source), self.supervisor_dest)
        self.execute_command(['chmod', '0664', self.supervisor_dest])
        shutil.copy(utils.resource_path(self.udocker_source), self.udocker_dest)
        self.execute_command(['chmod', '0775', self.udocker_dest])
        
        os.makedirs(utils.join_paths(self.scar_temporal_folder, "src"), exist_ok=True)
        os.makedirs(utils.join_paths(self.scar_temporal_folder, "src", "clients"), exist_ok=True)
        
        files = ["utils.py", "exceptions.py"]
        for file in files:
            file_source = utils.resource_path(utils.join_paths(self.src_path, file))
            self.file_dest = utils.join_paths(self.scar_temporal_folder, "src/{0}".format(file))
            shutil.copy(file_source, self.file_dest)
            self.execute_command(['chmod', '0664', self.file_dest])
            
        files = ["apigateway.py", "batch.py", "lambdafunction.py", "s3.py", "udocker.py"]
        for file in files:
            file_source = utils.resource_path(utils.join_paths(self.lambda_code_files_path, 'clients', file))
            self.file_dest = utils.join_paths(self.scar_temporal_folder, "src/clients/{0}".format(file))
            shutil.copy(file_source, self.file_dest)
            self.execute_command(['chmod', '0664', self.file_dest])             
        
        self.set_environment_variable('UDOCKER_DIR', "/tmp/home/udocker")
        self.set_environment_variable('UDOCKER_LIB', "/var/task/udocker/lib/")
        self.set_environment_variable('UDOCKER_BIN', "/var/task/udocker/bin/")
        self.create_udocker_files()
     
    @udocker_env     
    def create_udocker_files(self):
        self.execute_command(self.udocker_exec + ["help"], cli_msg="Packing udocker files")
     
    def add_init_script(self):
        if 'Script' in self.properties:
            shutil.copy(self.properties['Script'], utils.join_paths(self.scar_temporal_folder, self.init_script_name))
            self.properties['EnvironmentVariables']['INIT_SCRIPT_PATH'] = self.init_script_path        
     
    def add_extra_payload(self):
        if 'ExtraPayload' in self.properties:
            logger.info("Adding extra payload from {0}".format(self.properties['ExtraPayload']))
            dir_util.copy_tree(self.properties['ExtraPayload'], self.scar_temporal_folder)
            self.set_environment_variable('EXTRA_PAYLOAD', self.extra_payload_path)         
        
    def check_code_size(self):
        # Check if the code size fits within the aws limits   
        if 'DeploymentBucket' in self.properties:
            AWSValidator.validate_s3_code_size(self.scar_temporal_folder, MAX_S3_PAYLOAD_SIZE)
        else:
            AWSValidator.validate_function_code_size(self.scar_temporal_folder, MAX_PAYLOAD_SIZE)        
        
    def clean_tmp_folders(self):
        if os.path.isfile(self.properties['ZipFilePath']):    
            utils.delete_file(self.properties['ZipFilePath'])
        # Delete created temporal files
        if os.path.isdir(self.scar_temporal_folder):
            shutil.rmtree(self.scar_temporal_folder, ignore_errors=True)
        
    def zip_scar_folder(self):
        zip_exe = utils.resource_path("src/bin/zip", bin_path='/usr/bin/zip')
        self.execute_command([zip_exe, "-r9y", self.properties['ZipFilePath'], "."],
                             cmd_wd=self.scar_temporal_folder,
                             cli_msg="Creating function package")
        
    @classmethod
    def save_tmp_udocker_env(cls):
        #Avoid override global variables
        if utils.is_value_in_dict(os.environ, 'UDOCKER_TARBALL'):
            cls.udocker_tarball = os.environ['UDOCKER_TARBALL']
        if utils.is_value_in_dict(os.environ, 'UDOCKER_DIR'):
            cls.udocker_dir = os.environ['UDOCKER_DIR']
        # Set temporal global vars
        udocker_tarball = utils.resource_path(utils.join_paths(cls.lambda_code_files_path, "udocker-1.1.0-RC2.tar.gz"))
        utils.set_environment_variable('UDOCKER_TARBALL', udocker_tarball)
        utils.set_environment_variable('UDOCKER_DIR', utils.join_paths(cls.scar_temporal_folder, "udocker"))
        
    @classmethod        
    def restore_udocker_env(cls):
        cls.restore_environ_var('UDOCKER_TARBALL', cls.udocker_tarball)
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
        if(utils.get_tree_size(self.scar_temporal_folder) < MAX_S3_PAYLOAD_SIZE/2):
            self.execute_command(self.udocker_exec + ["create", "--name=lambda_cont", image_id], cli_msg="Creating container structure")
        if(utils.get_tree_size(self.scar_temporal_folder) > MAX_S3_PAYLOAD_SIZE):
            shutil.rmtree(utils.join_paths(self.scar_temporal_folder, "udocker/containers/"))        
        
    def set_udocker_local_registry(self):
        self.set_environment_variable('UDOCKER_REPOS', '/var/task/udocker/repos/')
        self.set_environment_variable('UDOCKER_LAYERS', '/var/task/udocker/layers/')        

    def set_environment_variable(self, key, val):
        if key and val:
            self.properties['EnvironmentVariables'][key] = val
     