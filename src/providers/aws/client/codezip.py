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
from distutils import dir_util

MAX_PAYLOAD_SIZE = 50 * 1024 * 1024
MAX_S3_PAYLOAD_SIZE = 250 * 1024 * 1024
aws_src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lambda_code_files_path = aws_src_path + "/cloud/lambda/"
scar_temporal_folder = "/tmp/scar/"
udocker_exec = "/tmp/scar/udockerb"
udocker_tarball = ""
udocker_dir = ""
zip_file_path = "/tmp/function.zip"

def add_mandatory_files(function_name, env_vars):
    os.makedirs(scar_temporal_folder, exist_ok=True)
    shutil.copy(lambda_code_files_path + 'scarsupervisor.py', scar_temporal_folder + function_name + '.py')
    shutil.copy(lambda_code_files_path + 'udockerb', udocker_exec)
    env_vars['UDOCKER_DIR'] = "/tmp/home/udocker"
    env_vars['UDOCKER_LIB'] = "/var/task/udocker/lib/"
    env_vars['UDOCKER_BIN'] = "/var/task/udocker/bin/"

def create_code_zip(function_name, env_vars, script=None, extra_payload=None, image_id=None, image_file=None, deployment_bucket=None, file_key=None):
    clean_tmp_folders()
    add_mandatory_files(function_name, env_vars)
    create_udocker_files()
    if (image_id and image_id != "") and (deployment_bucket and deployment_bucket != ""):
        download_udocker_image(image_id, env_vars)
    
    if image_file and image_file != "":
        prepare_udocker_image(image_file, env_vars)
        
    if script and script != "":
        shutil.copy(script, scar_temporal_folder + "init_script.sh")
        env_vars['INIT_SCRIPT_PATH'] = "/var/task/init_script.sh"

    if extra_payload and extra_payload != "":
        logger.info("Adding extra payload from %s" % extra_payload)
        dir_util.copy_tree(extra_payload, scar_temporal_folder)     
               
    zip_scar_folder()
    
    # Check if the payload size fits within the aws limits   
    if((not deployment_bucket) and (os.path.getsize(zip_file_path) > MAX_PAYLOAD_SIZE)):
        error_msg = "Payload size greater than 50MB.\nPlease reduce the payload size and try again."
        payload_size_error(zip_file_path, error_msg)
        
    if deployment_bucket and deployment_bucket != "":
        upload_file_to_S3_bucket(zip_file_path, deployment_bucket, file_key)
    
    clean_tmp_folders()
    
def clean_tmp_folders():
    # Delete created temporal files
    if os.path.isdir(scar_temporal_folder):
        shutil.rmtree(scar_temporal_folder, ignore_errors=True)
    
def zip_scar_folder():
    execute_command(["zip", "-r9y", zip_file_path, "."], cmd_wd=scar_temporal_folder, cli_msg="Creating function package")
    
def set_tmp_udocker_env():
    #Avoid override global variables
    if utils.has_dict_prop_value(os.environ, 'UDOCKER_TARBALL'):
        udocker_tarball = os.environ['UDOCKER_TARBALL']
    if utils.has_dict_prop_value(os.environ, 'UDOCKER_DIR'):
        udocker_dir = os.environ['UDOCKER_DIR']
    # Set temporal global vars
    os.environ['UDOCKER_TARBALL'] = lambda_code_files_path + "udocker-1.1.0-RC2.tar.gz"
    os.environ['UDOCKER_DIR'] = "/tmp/scar/udocker"        
    
def restore_udocker_env():
    if udocker_tarball != "":
        os.environ['UDOCKER_TARBALL'] = udocker_tarball
    if udocker_dir != "":
        os.environ['UDOCKER_DIR'] = udocker_dir      
    
def execute_command(command, cmd_wd=None, cli_msg=None):
    cmd_out = subprocess.check_output(command, cwd=cmd_wd).decode("utf-8")
    logger.info(cli_msg, cmd_out)
    return cmd_out[:-1]
    
def create_udocker_files():
    set_tmp_udocker_env()
    execute_command(["python3", udocker_exec, "help"], cli_msg="Setting udocker environment")
    restore_udocker_env()

def prepare_udocker_image(image_file, env_vars):
    set_tmp_udocker_env()
    shutil.copy(image_file, "/tmp/udocker_image.tar.gz")
    cmd_out = execute_command(["python3", udocker_exec, "load", "-i", "/tmp/udocker_image.tar.gz"], cli_msg="Loading image file")
    create_udocker_container(cmd_out)
    env_vars['IMAGE_ID'] = cmd_out
    env_vars['UDOCKER_REPOS'] = "/var/task/udocker/repos/"
    env_vars['UDOCKER_LAYERS'] = "/var/task/udocker/layers/"    
    restore_udocker_env()

def create_udocker_container(image_id):
    if(utils.get_tree_size(scar_temporal_folder) < MAX_S3_PAYLOAD_SIZE/2):
        execute_command(["python3", udocker_exec, "create", "--name=lambda_cont", image_id], cli_msg="Creating container structure")
    if(utils.get_tree_size(scar_temporal_folder) > MAX_S3_PAYLOAD_SIZE):
        shutil.rmtree(scar_temporal_folder + "udocker/containers/")    
    
def download_udocker_image(image_id, env_vars):
    set_tmp_udocker_env()
    execute_command(["python3", udocker_exec, "pull", image_id], cli_msg="Downloading container image")
    create_udocker_container(image_id)
    env_vars['UDOCKER_REPOS'] = "/var/task/udocker/repos/"
    env_vars['UDOCKER_LAYERS'] = "/var/task/udocker/layers/"
    restore_udocker_env()
    
def upload_file_to_S3_bucket(image_file, deployment_bucket, file_key):
    if(utils.get_tree_size(scar_temporal_folder) > MAX_S3_PAYLOAD_SIZE):         
        error_msg = "Uncompressed image size greater than 250MB.\nPlease reduce the uncompressed image and try again."
        logger.error(error_msg)
        utils.finish_failed_execution()
    
    logger.info("Uploading '%s' to the '%s' S3 bucket" % (image_file, deployment_bucket))
    file_data = utils.get_file_as_byte_array(image_file)
    S3().upload_file(deployment_bucket, file_key, file_data)

def payload_size_error(zip_file_path, message):
    logger.error(message)
    utils.delete_file(zip_file_path)
    utils.finish_failed_execution()
    