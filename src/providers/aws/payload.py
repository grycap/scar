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

from .s3 import S3
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

class FunctionPackageCreator():
    
    src_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    aws_src_path = os.path.dirname(os.path.abspath(__file__))
    lambda_code_files_path = utils.join_paths(aws_src_path, "cloud/lambda/")
    os_tmp_folder = tempfile.gettempdir()
    scar_temporal_folder = utils.join_paths(os_tmp_folder, "scar/")
    udocker_exec = utils.join_paths(scar_temporal_folder, "udockerb")
    udocker_tarball = ""
    udocker_dir = ""
    
    def __init__(self, package_props):
        self.properties  = package_props
    
    def add_mandatory_files(self, env_vars):
        os.makedirs(self.scar_temporal_folder, exist_ok=True)
        shutil.copy(utils.join_paths(self.lambda_code_files_path, "scarsupervisor.py"), 
                    utils.join_paths(self.scar_temporal_folder, "{0}.py".format(self.properties['FunctionName'])))
        shutil.copy(utils.join_paths(self.lambda_code_files_path, "udockerb"), self.udocker_exec)
        
        os.makedirs(utils.join_paths(self.scar_temporal_folder, "src"), exist_ok=True)
        shutil.copy(utils.join_paths(self.lambda_code_files_path, "__init__.py"),
                    utils.join_paths(self.scar_temporal_folder, "src/__init__.py"))
        shutil.copy(utils.join_paths(self.src_path, "utils.py"),
                    utils.join_paths(self.scar_temporal_folder, "src/utils.py"))
        shutil.copy(utils.join_paths(self.src_path, "exceptions.py"),
                    utils.join_paths(self.scar_temporal_folder, "src/exceptions.py"))                
        
        env_vars['UDOCKER_DIR'] = "/tmp/home/udocker"
        env_vars['UDOCKER_LIB'] = "/var/task/udocker/lib/"
        env_vars['UDOCKER_BIN'] = "/var/task/udocker/bin/"
        self.create_udocker_files()
    
    @excp.exception(logger)
    def prepare_lambda_payload(self):
        self.clean_tmp_folders()
        self.add_mandatory_files(self.properties['EnvironmentVariables'])
        
        if 'DeploymentBucket' in self.properties and 'ImageId' in self.properties:
            self.download_udocker_image(self.properties['ImageId'], self.properties['EnvironmentVariables'])
        
        if 'ImageFile' in self.properties:
            self.prepare_udocker_image(self.properties['ImageFile'], self.properties['EnvironmentVariables'])
            
        if 'Script' in self.properties:
            shutil.copy(self.properties['Script'], utils.join_paths(self.scar_temporal_folder, "init_script.sh"))
            self.properties['EnvironmentVariables']['INIT_SCRIPT_PATH'] = "/var/task/init_script.sh"
    
        if 'ExtraPayload' in self.properties:
            logger.info("Adding extra payload from %s" % self.properties['ExtraPayload'])
            self.properties['EnvironmentVariables']['EXTRA_PAYLOAD'] = "/var/task"
            dir_util.copy_tree(self.properties['ExtraPayload'], self.scar_temporal_folder)     
                   
        self.zip_scar_folder()
        
        # Check if the payload size fits within the aws limits   
        if 'DeploymentBucket' in self.properties:
            AWSValidator.validate_s3_code_size(self.scar_temporal_folder, MAX_S3_PAYLOAD_SIZE)
            self.upload_file_to_S3_bucket(self.properties['DeploymentBucket'], self.properties['FileKey'])
        else:
            AWSValidator.validate_function_code_size(self.scar_temporal_folder, MAX_PAYLOAD_SIZE)
        
    def clean_tmp_folders(self):
        if os.path.isfile(self.properties['ZipFilePath']):    
            utils.delete_file(self.properties['ZipFilePath'])
        # Delete created temporal files
        if os.path.isdir(self.scar_temporal_folder):
            shutil.rmtree(self.scar_temporal_folder, ignore_errors=True)
        
    def zip_scar_folder(self):
        self.execute_command(["zip", "-r9y", self.properties['ZipFilePath'], "."],
                             cmd_wd=self.scar_temporal_folder,
                             cli_msg="Creating function package")
        
    def set_tmp_udocker_env(self):
        #Avoid override global variables
        if utils.has_dict_prop_value(os.environ, 'UDOCKER_TARBALL'):
            self.udocker_tarball = os.environ['UDOCKER_TARBALL']
        if utils.has_dict_prop_value(os.environ, 'UDOCKER_DIR'):
            self.udocker_dir = os.environ['UDOCKER_DIR']
        # Set temporal global vars
        os.environ['UDOCKER_TARBALL'] = self.lambda_code_files_path + "udocker-1.1.0-RC2.tar.gz"
        os.environ['UDOCKER_DIR'] = self.scar_temporal_folder + "/udocker"        
        
    def restore_udocker_env(self):
        if self.udocker_tarball != "":
            os.environ['UDOCKER_TARBALL'] = self.udocker_tarball
        if self.udocker_dir != "":
            os.environ['UDOCKER_DIR'] = self.udocker_dir      
        
    def execute_command(self, command, cmd_wd=None, cli_msg=None):
        cmd_out = subprocess.check_output(command, cwd=cmd_wd).decode("utf-8")
        logger.info(cli_msg, cmd_out)
        return cmd_out[:-1]
        
    def create_udocker_files(self):
        self.set_tmp_udocker_env()
        self.execute_command(["python3", self.udocker_exec, "help"], cli_msg="Packing udocker files")
        self.restore_udocker_env()
    
    def prepare_udocker_image(self, image_file, env_vars):
        self.set_tmp_udocker_env()
        shutil.copy(image_file, self.os_tmp_folder + "/udocker_image.tar.gz")
        cmd_out = self.execute_command(["python3", self.udocker_exec, "load", "-i", self.os_tmp_folder + "/udocker_image.tar.gz"], cli_msg="Loading image file")
        self.create_udocker_container(cmd_out)
        env_vars['IMAGE_ID'] = cmd_out
        env_vars['UDOCKER_REPOS'] = "/var/task/udocker/repos/"
        env_vars['UDOCKER_LAYERS'] = "/var/task/udocker/layers/"    
        self.restore_udocker_env()
    
    def create_udocker_container(self, image_id):
        if(utils.get_tree_size(self.scar_temporal_folder) < MAX_S3_PAYLOAD_SIZE/2):
            self.execute_command(["python3", self.udocker_exec, "create", "--name=lambda_cont", image_id], cli_msg="Creating container structure")
        if(utils.get_tree_size(self.scar_temporal_folder) > MAX_S3_PAYLOAD_SIZE):
            shutil.rmtree(self.scar_temporal_folder + "/udocker/containers/")    
        
    def download_udocker_image(self, image_id, env_vars):
        self.set_tmp_udocker_env()
        self.execute_command(["python3", self.udocker_exec, '--debug', "pull", image_id], cli_msg="Downloading container image")
        self.create_udocker_container(image_id)
        env_vars['UDOCKER_REPOS'] = "/var/task/udocker/repos/"
        env_vars['UDOCKER_LAYERS'] = "/var/task/udocker/layers/"
        self.restore_udocker_env()
        
    def upload_file_to_S3_bucket(self, deployment_bucket, file_key):
        logger.info("Uploading '{0}' to the '{1}' S3 bucket.".format(self.properties['ZipFilePath'], deployment_bucket))
        file_data = utils.read_file(self.properties['ZipFilePath'], 'rb')
        S3().upload_file(deployment_bucket, file_key, file_data)
    
