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
from subprocess import call, check_output, Popen, signal, STDOUT, TimeoutExpired
import traceback
import tarfile

loglevel = logging.INFO
logger = logging.getLogger()
logger.setLevel(loglevel)
logger.info('SCAR: Loading supervisor')

udocker_bin = "/tmp/udocker/udocker"
container_name = "lambda_cont"
s3_input_file_name = ""
    
def prepare_environment(self, aws_request_id):
    # Install udocker in /tmp
    os.makedirs("/tmp/udocker", exist_ok=True)    
    call(["cp", "/var/task/udocker", udocker_bin])
    call(["chmod", "u+rx", udocker_bin])
    os.makedirs("/tmp/home/.udocker", exist_ok=True)    
    os.makedirs("/tmp/%s/output" % aws_request_id, exist_ok=True)
    if ('INIT_SCRIPT_PATH' in os.environ) and os.environ['INIT_SCRIPT_PATH']:
        call(["cp", "/var/task/init_script.sh", "/tmp/%s/init_script.sh" % aws_request_id])
    
def prepare_container(self, container_image):
    # Check if the container is already downloaded
    cmd_out = check_output([udocker_bin, "images"]).decode("utf-8")
    if container_image not in cmd_out:
        logger.info("SCAR: Pulling container '%s' from Docker Hub" % container_image)
        # If the container doesn't exist
        call([udocker_bin, "pull", container_image])
    else:
        logger.info("SCAR: Container image '%s' already available" % container_image)
    # Download and create container
    cmd_out = check_output([udocker_bin, "ps"]).decode("utf-8")
    if container_name not in cmd_out:
        logger.info("SCAR: Creating container with name '%s' based on image '%s'." % (container_name, container_image))
        call([udocker_bin, "create", "--name=%s" % container_name, container_image])
        # Set container execution engine to Fakechroot
        call([udocker_bin, "setup", "--execmode=F1", container_name])
    else:
        logger.info("SCAR: Container '" + container_name + "' already available")
            
def add_global_variable(self, variables, key, value):
    variables.append('--env')
    variables.append(key + '=' + value)
    return variables
            
def get_global_variables(self):
    variables = []
    for key in os.environ.keys():
        # Find global variables with the specified prefix
        if re.match("CONT_VAR_.*", key):
            variables = self.add_global_variable(variables, key.replace("CONT_VAR_", ""), os.environ[key])
    # Add IAM credentials
    if not ('CONT_VAR_AWS_ACCESS_KEY_ID' in os.environ):
        variables = self.add_global_variable(variables, "AWS_ACCESS_KEY_ID", os.environ["AWS_ACCESS_KEY_ID"])
    if not ('CONT_VAR_AWS_SECRET_ACCESS_KEY' in os.environ):
        variables = self.add_global_variable(variables, "AWS_SECRET_ACCESS_KEY", os.environ["AWS_SECRET_ACCESS_KEY"])
    # Always add Session and security tokens
    variables = self.add_global_variable(variables, "AWS_SESSION_TOKEN", os.environ["AWS_SESSION_TOKEN"])
    variables = self.add_global_variable(variables, "AWS_SECURITY_TOKEN", os.environ["AWS_SECURITY_TOKEN"])
    if s3_input_file_name and s3_input_file_name != "":
        variables = self.add_global_variable(variables, "SCAR_INPUT_FILE", s3_input_file_name)
    return variables
    
def prepare_output(self, context):
    stdout = "SCAR: Log group name: %s\n" % context.log_group_name
    stdout += "SCAR: Log stream name: %s\n" % context.log_stream_name
    stdout += "---------------------------------------------------------------------------\n"
    return stdout
    
def create_file(self, content, path):
    with open(path, "w") as f:
        f.write(content)
    
def create_event_file(self, event, request_id):
    event_file_path = "/tmp/%s/" % request_id
    os.makedirs(event_file_path, exist_ok=True)     
    self.create_file(event, event_file_path + "/event.json")
    
def pre_process(self, event, context):
    self.create_event_file(json.dumps(event), context.aws_request_id)
    self.prepare_environment(context.aws_request_id)
    self.prepare_container(os.environ['IMAGE_ID'])
    self.check_event_records(event, context)
    
def check_event_records(self, event, context):
    request_id = context.aws_request_id
    if(is_s3_event(event)):
        s3_record = get_s3_record(event)
        s3_input_file_name = download_input(s3_record, request_id)
    
def post_process(self, event, context):
    request_id = context.aws_request_id
    if(is_s3_event(event)):
        upload_output(event['Records'][0]['s3'], request_id)
    # Delete all the temporal folders created for the invocation
    # call(["rm", "-rf", "/tmp/%s" % request_id])
                    
def undo_escape_string(self, value):
    value = value.replace("\\/", "\\").replace('\\n', '\n')
    value = value.replace('\\"', '"').replace("\\/", "\/")
    value = value.replace("\\b", "\b").replace("\\f", "\f")
    return value.replace("\\r", "\r").replace("\\t", "\t")                    
                    
def create_command(self, event, context):
    # Create container execution command
    command = [udocker_bin, "--quiet", "run"]
    container_dirs = ["-v", "/tmp/%s" % context.aws_request_id, "-v", "/dev", "-v", "/proc", "-v", "/etc/hosts", "--nosysdirs"]
    container_vars = ["--env", "REQUEST_ID=%s" % context.aws_request_id]
    command.extend(container_dirs)
    command.extend(container_vars)
        
    # Add global variables (if any)
    global_variables = self.get_global_variables()
    if global_variables:
        command.extend(global_variables)
    
    # Set the script executable 
    script_exec = "/bin/sh"
    # Container running script
    script_path = "/tmp/%s/script.sh" % context.aws_request_id
    if ('script' in event) and event['script']:
        script_content = self.undo_escape_string(event['script'])
        self.create_file(script_content, script_path)
        command.extend(["--entrypoint=%s %s" % (script_exec, script_path), container_name])
    # Container with args
    elif ('cmd_args' in event) and event['cmd_args']:
        # Parse list of strings
        args = event['cmd_args'][1:-1].replace('"', '').split(', ')
        command.append(container_name)
        command.extend(args)
    # Script to be executed every time (if defined)
    elif ('INIT_SCRIPT_PATH' in os.environ) and os.environ['INIT_SCRIPT_PATH']:
        command.extend(["--entrypoint=%s %s" % (script_exec, "/tmp/%s/init_script.sh" % context.aws_request_id), container_name])
    # Only container
    else:
        command.append(container_name)
    return command
    
def relaunch_lambda(self, event, func_name):
    client = boto3.client('lambda', region_name='us-east-1')
    client.invoke(FunctionName=func_name,
                  InvocationType='Event',
                  LogType='None',
                  Payload=json.dumps(event))
        
def launch_recursive_lambda(self, event, context):
    if(is_s3_event(event)):
        upload_recursive_output(event['Records'][0]['s3'], context.aws_request_id)
    else:              
        logger.info("SCAR: Recursively launching lambda function.")
        self.relaunch_lambda(event, context.function_name)
        
def kill_udocker_process(self, process):
    logger.info("SCAR: Stopping container with name '%s'." % (self.container_name))
    # Using SIGKILL instead of SIGTERM to ensure the process finalization 
    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        
def is_recursive():
    return ('RECURSIVE' in os.environ) and eval(os.environ['RECURSIVE'])

def is_s3_event(event):
    if ('Records' in event) and event['Records']:
        # Check if the event is an S3 event
        return event['Records'][0]['eventSource'] == "aws:s3"
    else:
        return False

def create_tar_gz(folder_to_archive, destination_tar_path):
    output_files_path = get_all_files_in_directory(folder_to_archive) 
    with tarfile.open(destination_tar_path, "w:gz") as tar:
        for file_path in output_files_path:
            tar.add(file_path, arcname=os.path.basename(file_path))
        
def extract_tar_gz(tar_path, destination_path):
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.extractall(path=destination_path)
    call(["ls", "-la", destination_path])   
            
def get_all_files_in_directory(dir_path):
    files = []
    for dirname, dirnames, filenames in os.walk(dir_path):
        for filename in filenames:
            files.append(os.path.join(dirname, filename))
    return files                   
        
def get_s3_record(self, event):
    if ('Records' in event) and event['Records']:
        if len(event['Records']) > 1:
            logger.warning("SCAR: MULTIPLE RECORDS DETECTED. ONLY PROCESSING THE FIRST ONE.")
        record = event['Records'][0]
        if('s3' in record) and record['s3']:
            return record['s3']    
    
def get_s3_client(self):
    return boto3.client('s3')

def get_s3_bucket_name(self, s3_record):
    return s3_record['bucket']['name']
    
def download_input(self, s3_record, request_id):
    '''Downloads the file from the S3 bucket and returns the path were the download is placed'''
    bucket_name = self.get_bucket_name(s3_record)
    file_key = s3_record['object']['key']
    download_path = '/tmp/%s/%s' % (request_id, file_key)
    logger.info("SCAR: Downloading item from bucket %s with key %s" % (bucket_name, file_key))
    os.makedirs(os.path.dirname(download_path), exist_ok=True)       
    with open(download_path, 'wb') as data:
        self.get_s3_client().download_fileobj(bucket_name, file_key, data)
    logger.info("SCAR: Successfully downloaded item from bucket %s with key %s" % (bucket_name, file_key))
    if (is_recursive()):
        if "recursive/" in file_key:
            extract_tar_gz(download_path, '/tmp/%s/input' % request_id)
            download_path = download_path.replace("recursive/", "input/");
            download_path = os.path.dirname(download_path)
    return download_path

def upload_output(self, s3_record, request_id):
    bucket_name = self.get_bucket_name(s3_record)
    output_folder = "/tmp/%s/output/" % request_id
    output_files_path = get_all_files_in_directory(output_folder)
    for file_path in output_files_path:
        file_key = "output/%s" % file_path.replace(output_folder, "")
        self.upload_file_to_s3(bucket_name, file_path, file_key) 

def upload_recursive_output(self, s3_record, request_id):
    bucket_name = self.get_bucket_name(s3_record)
    output_folder = "/tmp/%s/output/" % request_id
    tmp_output = "/tmp/%s/output/tmp-output.tar.gz" % request_id
    create_tar_gz(output_folder, tmp_output)   
    file_key = "recursive/%s" % tmp_output.replace(output_folder, "")                        
    self.upload_file_to_s3(bucket_name, tmp_output, file_key) 
        
def upload_file_to_s3(self, bucket_name, file_path, file_key):
    logger.info("SCAR: Uploading file to bucket %s with key %s" % (bucket_name, file_key))
    with open(file_path, 'rb') as data:
        self.get_s3_client().upload_fileobj(data, bucket_name, file_key)
    logger.info("SCAR: Changing ACLs for public-read for object in bucket %s with key %s" % (bucket_name, file_key))
    s3_resource = boto3.resource('s3')
    obj = s3_resource.Object(bucket_name, file_key)
    obj.Acl().put(ACL='public-read')         

def lambda_handler(event, context):
    logger.info("SCAR: Received event: " + json.dumps(event))
    stdout = prepare_output(context)
    try:
        pre_process(event, context)
        # Create container execution command
        command = create_command(event, context)
        # print ("Udocker command: %s" % command)

        # Execute container
        lambda_output = "/tmp/%s/lambda-stdout.txt" % context.aws_request_id
        remaining_seconds = int(context.get_remaining_time_in_millis() / 1000) - int(os.environ['TIME_THRESHOLD'])
        logger.info("SCAR: Executing the container. Timeout set to %s seconds" % str(remaining_seconds))
        with Popen(command, stderr=STDOUT, stdout=open(lambda_output, "w"), preexec_fn=os.setsid) as process:
            try:
                process.wait(timeout=remaining_seconds)
            except TimeoutExpired:
                kill_udocker_process(process)
                # Processing recursive function
                if (is_recursive()):
                    launch_recursive_lambda(event, context)
                else:
                    logger.warning("SCAR: Container timeout")                                       
 

        if stdout is not None:
            stdout += check_output(["cat", lambda_output]).decode("utf-8")
        post_process(event, context)

    except Exception:
        if stdout is None:
            stdout = "SCAR ERROR: Exception launched:\n %s" % traceback.format_exc()
        else:
            stdout += "SCAR ERROR: Exception launched:\n %s" % traceback.format_exc()
    print(stdout)
    return stdout