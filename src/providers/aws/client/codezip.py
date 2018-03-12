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

import logging
import os
import shutil
import src.utils as utils
import zipfile

MAX_PAYLOAD_SIZE = 50 * 1024 * 1024
MAX_S3_PAYLOAD_SIZE = 250 * 1024 * 1024
aws_src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lambda_code_files_path = aws_src_path + "/cloud/lambda/"

def create_code_zip(function_name, zip_file_path, env_vars=None, script=None, extra_payload=None, image_file=None, deployment_bucket=None):
    # Set lambda function name
    supervisor_file_name = function_name + '.py'
    # Copy file to avoid messing with the repo files
    # We have to rename the file because the function name affects the handler name
    shutil.copy(lambda_code_files_path + 'scarsupervisor.py', supervisor_file_name)
    # Zip the function file
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # AWSLambda function code
        zf.write(supervisor_file_name)
        utils.delete_file(supervisor_file_name)
        # Udocker script code
        zf.write(lambda_code_files_path + 'udocker', 'udocker')
        # Udocker libs
        zf.write(lambda_code_files_path + 'udocker-1.1.0-RC2.tar.gz', 'udocker-1.1.0-RC2.tar.gz')

        if script:
            zf.write(script, 'init_script.sh')
            env_vars['INIT_SCRIPT_PATH'] = "/var/task/init_script.sh"
            
    if extra_payload:
        zip_folder(zip_file_path, extra_payload)
        env_vars['EXTRA_PAYLOAD'] = "/var/task/extra/"

    # Add docker image file
    if image_file and deployment_bucket:
        add_file_to_zip(zip_file_path, image_file, function_name)
    # Check if the payload size fits within the aws limits
    
    if((not deployment_bucket) and (os.path.getsize(zip_file_path) > MAX_PAYLOAD_SIZE)):
        error_message = "Error: Payload size greater than 50MB.\nPlease specify an S3 bucket to deploy the function.\n"
        payload_size_error(zip_file_path, error_message)
    
    if(os.path.getsize(zip_file_path) > MAX_S3_PAYLOAD_SIZE):            
        error_message = "Error: Payload size greater than 250MB.\nPlease reduce the payload size and try again.\n"
        payload_size_error(zip_file_path, error_message)


def payload_size_error(zip_file_path, message):
    logging.error(message)
    print(message)
    utils.delete_file(zip_file_path)
    utils.finish_failed_execution()
    
def add_file_to_zip(zip_path, file_path, file_name):
    with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_path, 'extra/' + file_name)

def zip_folder(zip_path, target_dir):            
    with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
        rootlen = len(target_dir) + 1
        for base, _, files in os.walk(target_dir):
            for file in files:
                fn = os.path.join(base, file)
                zf.write(fn, 'extra/' + fn[rootlen:])    
    