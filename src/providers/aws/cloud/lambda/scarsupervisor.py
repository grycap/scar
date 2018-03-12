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

import boto3
import logging
import json
import os
import re
import shutil
import subprocess
import traceback
import tarfile
import socket

loglevel = logging.INFO
logger = logging.getLogger()
logger.setLevel(loglevel)

udocker_bin = "/var/task/udocker"
container_name = "lambda_cont"
s3_input_file_name = ""
script_exec = "/bin/sh"
request_id = ""
input_folder = ""
output_folder = ""

logger.info('SCAR: Loading lambda function')
#######################################
#        S3 RELATED FUNCTIONS         #
#######################################
def is_s3_event(event):
    if check_key_existence_in_dictionary('Records', event):
        # Check if the event is an S3 event
        return event['Records'][0]['eventSource'] == "aws:s3"
    return False

def get_s3_record(event):
    if check_key_existence_in_dictionary('Records', event):
        if len(event['Records']) > 1:
            logger.warning("Multiple records detected. Only processing the first one.")
        record = event['Records'][0]
        if check_key_existence_in_dictionary('s3', record):
            return record['s3']    
    
def get_s3_client():
    return boto3.client('s3')

def get_s3_bucket_name(s3_record):
    return s3_record['bucket']['name']

def get_s3_file_key(s3_record):
    return s3_record['object']['key']
    
def download_input_from_s3(s3_record):
    '''Downloads the file from the S3 bucket and returns the path were the download is placed'''
    bucket_name = get_s3_bucket_name(s3_record)
    file_key = get_s3_file_key(s3_record)
    download_path = '/tmp/%s/%s' % (request_id, file_key)
    logger.info("Downloading item from bucket %s with key %s" % (bucket_name, file_key))
    os.makedirs(os.path.dirname(download_path), exist_ok=True)      
    with open(download_path, 'wb') as data:
        get_s3_client().download_fileobj(bucket_name, file_key, data)
    logger.info("Successfully downloaded item from bucket '%s' with key '%s' in path '%s'" % 
                (bucket_name, file_key, download_path))
    if (is_recursive()):
        if "recursive/" in file_key:
            extract_tar_gz(download_path)
            download_path = input_folder
            delete_file_from_s3(s3_record)
    return download_path

def delete_file_from_s3(s3_record):
    bucket_name = get_s3_bucket_name(s3_record)
    file_key = get_s3_file_key(s3_record)
    get_s3_client().delete_object(Bucket=bucket_name, Key=file_key)

def upload_output_to_s3(s3_record):
    bucket_name = get_s3_bucket_name(s3_record)
    output_files_path = get_all_files_in_directory(output_folder)
    for file_path in output_files_path:
        file_key = "output/%s" % file_path.replace(output_folder+"/", "")
        upload_file_to_s3(bucket_name, file_path, file_key) 

def upload_recursive_output_to_s3(s3_record):
    bucket_name = get_s3_bucket_name(s3_record)
    tar_gz_output_path = create_tar_gz()   
    file_key = "recursive/%s" % tar_gz_output_path.replace(output_folder+"/", "")                        
    upload_file_to_s3(bucket_name, tar_gz_output_path, file_key) 
        
def upload_file_to_s3(bucket_name, file_path, file_key):
    logger.info("Uploading file  '%s' to bucket '%s'" % (file_key, bucket_name))
    with open(file_path, 'rb') as data:
        get_s3_client().upload_fileobj(data, bucket_name, file_key)
    logger.info("Changing ACLs for public-read for object in bucket %s with key %s" % (bucket_name, file_key))
    obj = boto3.resource('s3').Object(bucket_name, file_key)
    obj.Acl().put(ACL='public-read')

#######################################
#      LAMBDA RELATED FUNCTIONS       #
#######################################
def get_invocation_remaining_seconds(context):
    return int(context.get_remaining_time_in_millis() / 1000) - int(os.environ['TIMEOUT_THRESHOLD'])

def launch_recursive_lambda(event, function_name):
    if(is_s3_event(event)):
        upload_recursive_output_to_s3(get_s3_record(event))
    else:              
        logger.info("Recursively launching lambda function.")
        relaunch_lambda(event, function_name)

def relaunch_lambda(event, func_name):
    client = boto3.client('lambda', region_name='us-east-1')
    client.invoke(FunctionName=func_name,
                  InvocationType='Event',
                  LogType='None',
                  Payload=json.dumps(event))
        
def is_recursive():
    return ('RECURSIVE' in os.environ) and eval(os.environ['RECURSIVE'])    
    
def create_event_file(file_content):
    event_file_path = "/tmp/%s/" % request_id
    os.makedirs(event_file_path, exist_ok=True)     
    create_file_with_content(event_file_path + "/event.json", file_content)
    
def pre_process(event):
    create_event_file(json.dumps(event))
    prepare_udocker_environment()
    prepare_udocker_container(os.environ['IMAGE_ID'])
    check_s3_event_records(event)
    
def check_s3_event_records(event):
    if(is_s3_event(event)):
        s3_record = get_s3_record(event)
        if s3_record:
            global s3_input_file_name
            s3_input_file_name = download_input_from_s3(s3_record)
    
def post_process(event):
    if(is_s3_event(event)):
        upload_output_to_s3(get_s3_record(event))
    # Delete all the temporal folders created for the invocation
    shutil.rmtree("/tmp/%s" % request_id)
    
def prepare_output(context):
    stdout = "Log group name: %s\n" % context.log_group_name
    stdout += "Log stream name: %s\n" % context.log_stream_name
    stdout += "---------------------------------------------------------------------------\n"
    return stdout

def set_request_id(context):
    global request_id
    request_id = context.aws_request_id

def set_invocation_input_output_folders():
    global input_folder
    global output_folder
    input_folder = '/tmp/%s/input' % request_id
    output_folder = '/tmp/%s/output' % request_id
    
#######################################
#      UDOCKER RELATED FUNCTIONS      #
#######################################
def prepare_udocker_environment():
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

def prepare_udocker_container(container_image_id):
    # Check if the container is already downloaded
    cmd_out = subprocess.check_output([udocker_bin, "images"]).decode("utf-8")
    if container_image_id not in cmd_out:
        logger.info("Pulling container '%s' from Docker Hub" % container_image_id)
        # If the container doesn't exist
        subprocess.call([udocker_bin, "pull", container_image_id])
    else:
        logger.info("Container image '%s' already available" % container_image_id)
    # Download and create container
    cmd_out = subprocess.check_output([udocker_bin, "ps"]).decode("utf-8")
    if container_name not in cmd_out:
        logger.info("Creating container with name '%s' based on image '%s'." % (container_name, container_image_id))
        subprocess.call([udocker_bin, "create", "--name=%s" % container_name, container_image_id])
        # Set container execution engine to Fakechroot
        subprocess.call([udocker_bin, "setup", "--execmode=F1", container_name])
    else:
        logger.info("Container '" + container_name + "' already available")

def add_udocker_container_variable(variables, key, value):
    variables.append('--env')
    variables.append(key + '=' + value)

def add_user_defined_variables_to_udocker_container_variables(variables):
    for key in os.environ.keys():
        # Find global variables with the specified prefix
        if re.match("CONT_VAR_.*", key):
            add_udocker_container_variable(variables, key.replace("CONT_VAR_", ""), os.environ[key])    
            
def add_iam_credentials_to_udocker_container_variables(variables):
        # Add IAM credentials
    if not check_key_existence_in_dictionary('CONT_VAR_AWS_ACCESS_KEY_ID', os.environ):
        add_udocker_container_variable(variables, "AWS_ACCESS_KEY_ID", os.environ["AWS_ACCESS_KEY_ID"])
    if not check_key_existence_in_dictionary('CONT_VAR_AWS_SECRET_ACCESS_KEY', os.environ):
        add_udocker_container_variable(variables, "AWS_SECRET_ACCESS_KEY", os.environ["AWS_SECRET_ACCESS_KEY"])       

def add_session_and_security_token_to_udocker_container_variables(variables):
    # Always add Session and security tokens
    add_udocker_container_variable(variables, "AWS_SESSION_TOKEN", os.environ["AWS_SESSION_TOKEN"])
    add_udocker_container_variable(variables, "AWS_SECURITY_TOKEN", os.environ["AWS_SECURITY_TOKEN"])
            
def add_input_file_path_to_udocker_container_variables(variables):
    if s3_input_file_name and s3_input_file_name != "":
        add_udocker_container_variable(variables, "SCAR_INPUT_FILE", s3_input_file_name)      
            
def add_instance_ip_to_udocker_container_variables(variables):
    add_udocker_container_variable(variables, "INSTANCE_IP", socket.gethostbyname(socket.gethostname()))
    
def add_extra_payload_path_to_udocker_container_variables(variables):
    if check_key_existence_in_dictionary('EXTRA_PAYLOAD', os.environ):
        add_udocker_container_variable(variables, "EXTRA_PAYLOAD", os.environ["EXTRA_PAYLOAD"])
            
def get_udocker_container_global_variables():
    variables = []
    add_user_defined_variables_to_udocker_container_variables(variables)
    add_iam_credentials_to_udocker_container_variables(variables)
    add_session_and_security_token_to_udocker_container_variables(variables)
    add_input_file_path_to_udocker_container_variables(variables)
    add_instance_ip_to_udocker_container_variables(variables)
    add_extra_payload_path_to_udocker_container_variables(variables)    
    return variables

def append_script_to_udocker_command(script, command):
    script_path = "/tmp/%s/script.sh" % request_id
    script_content = undo_escape_string(script)
    create_file_with_content(script_path, script_content)
    command.extend(["--entrypoint=%s %s" % (script_exec, script_path), container_name])

def append_udocker_container_variables_to_udocker_command(command):
    container_vars = ["--env", "REQUEST_ID=%s" % request_id]
    command.extend(container_vars)        
    # Add global variables (if any)
    global_variables = get_udocker_container_global_variables()
    if global_variables:
        command.extend(global_variables)
        
def append_args_to_udocker_command(cmd_args, command):
    command.append(container_name)
    # Parse list of strings
    parsed_args = cmd_args[1:-1].replace('"', '').split(', ')
    command.extend(parsed_args)
    
def append_init_script_to_udocker_command(command):
    init_script_path = "/tmp/%s/init_script.sh" % request_id
    shutil.copyfile("/var/task/init_script.sh", init_script_path)    
    command.extend(["--entrypoint=%s %s" % (script_exec, init_script_path), container_name])
    
def append_udocker_container_volumes_to_udocker_command(command):
    container_volumes = ["-v", "/tmp/%s" % request_id, "-v", "/dev", "-v", "/proc", "-v", "/etc/hosts", "--nosysdirs"]
    if check_key_existence_in_dictionary('EXTRA_PAYLOAD', os.environ):
        container_volumes.extend(["-v", "/var/task/extra"])
    command.extend(container_volumes)    

def create_udocker_command(event):
    # Create the udocker container execution command
    command = [udocker_bin, "--quiet", "run"]
    append_udocker_container_volumes_to_udocker_command(command)
    append_udocker_container_variables_to_udocker_command(command)
    # Container running script
    if check_key_existence_in_dictionary('script', event): 
        append_script_to_udocker_command(event['script'], command)
    # Container with args
    elif check_key_existence_in_dictionary('cmd_args', event):
        append_args_to_udocker_command(event['cmd_args'], command)
    # Script to be executed every time (if defined)
    elif check_key_existence_in_dictionary('INIT_SCRIPT_PATH', os.environ):
        append_init_script_to_udocker_command(command)
    # Only container
    else:
        command.append(container_name)
    return command

def kill_udocker_process(process):
    logger.info("Stopping udocker container")
    # Using SIGKILL instead of SIGTERM to ensure the process finalization 
    os.killpg(os.getpgid(process.pid), subprocess.signal.SIGKILL)
    
def launch_udocker_container(event, context, command):
    lambda_output = "/tmp/%s/lambda-stdout.txt" % request_id
    remaining_seconds = get_invocation_remaining_seconds(context)
    logger.info("Executing udocker container. Timeout set to %s seconds" % str(remaining_seconds))
    with subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=open(lambda_output, "w"), preexec_fn=os.setsid) as process:
        try:
            process.wait(timeout=remaining_seconds)
        except subprocess.TimeoutExpired:
            kill_udocker_process(process)
            # Processing recursive function
            if (is_recursive()):
                launch_recursive_lambda(event, context.function_name)
            else:
                logger.warning("Container timeout")
    return lambda_output

def read_udocker_output_file(output_file_path):
    with open(output_file_path, 'r') as content_file:
        return content_file.read()    

#######################################
#           USEFUL FUNCTIONS          #
#######################################
def check_key_existence_in_dictionary(key, dictionary):
    return (key in dictionary) and dictionary[key]

def create_file_with_content(path, content):
    with open(path, "w") as f:
        f.write(content)
                    
def undo_escape_string(value):
    value = value.replace("\\/", "\\").replace('\\n', '\n')
    value = value.replace('\\"', '"').replace("\\/", "\/")
    value = value.replace("\\b", "\b").replace("\\f", "\f")
    return value.replace("\\r", "\r").replace("\\t", "\t")

def get_all_files_in_directory(dir_path):
    files = []
    for dirname, _, filenames in os.walk(dir_path):
        for filename in filenames:
            files.append(os.path.join(dirname, filename))
    return files

def create_tar_gz():
    destination_tar_path = "%s/tmp-output.tar.gz" % output_folder
    files_to_archive = get_all_files_in_directory(output_folder)
    with tarfile.open(destination_tar_path, "w:gz") as tar:
        for file_path in files_to_archive:
            tar.add(file_path, arcname=os.path.basename(file_path))
    return destination_tar_path
        
def extract_tar_gz(tar_path):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=input_folder)
    logging.info("Succesfully extracted '%s' in path '%s'" % (tar_path, input_folder))
            
#######################################
#         LAMBDA MAIN FUNCTION        #
#######################################
def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event))
    set_request_id(context)
    set_invocation_input_output_folders()
    stdout = ""
    stdout += prepare_output(context)
    try:
        pre_process(event)
        # Create container execution command
        command = create_udocker_command(event)
        logger.debug("Udocker command: %s" % command)
        # Execute container
        output_file_path = launch_udocker_container(event, context, command)                                       
        stdout += read_udocker_output_file(output_file_path)
        post_process(event)
   
    except Exception:
        logger.error("Exception launched:\n %s" % traceback.format_exc())
        stdout += "SCAR ERROR: Exception launched:\n %s" % traceback.format_exc()
    logger.info(stdout)
    return stdout
