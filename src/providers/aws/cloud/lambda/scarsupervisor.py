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
import uuid
import base64

loglevel = logging.INFO
logger = logging.getLogger()
logger.setLevel(loglevel)
logger.info('SCAR: Loading lambda function')

lambda_instance = None

def lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.'''
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

#######################################
#        S3 RELATED FUNCTIONS         #
#######################################
class S3():
    
    @lazy_property
    def client(self):
        client = boto3.client('s3')
        return client
    
    def __init__(self):
        if check_key_in_dictionary('Records', lambda_instance.event):
            self.record = self.get_s3_record()
            self.input_bucket = self.record['bucket']['name']
            self.file_key = self.record['object']['key']
            self.file_name = os.path.basename(self.file_key)
            self.file_download_path = '{0}/{1}'.format(lambda_instance.input_folder, self.file_name)
            #self.file_download_path = '{0}/{1}'.format(lambda_instance.input_folder, uuid.uuid4().hex)      

    def get_s3_record(self):
        if len(lambda_instance.event['Records']) > 1:
            logger.warning("Multiple records detected. Only processing the first one.")
            
        record = lambda_instance.event['Records'][0]
        if check_key_in_dictionary('s3', record):
            return record['s3']

    def download_input(self):
        '''Downloads the file from the S3 bucket and returns the path were the download is placed'''
        logger.info("Downloading item from bucket '{0}' with key '{1}'".format(self.input_bucket, self.file_key))
        if not os.path.isdir(self.file_download_path):
            os.makedirs(os.path.dirname(self.file_download_path), exist_ok=True)
        with open(self.file_download_path, 'wb') as data:
            self.client.download_fileobj(self.input_bucket, self.file_key, data)
        logger.info("Successful download of file '{0}' from bucket '{1}' in path '{2}'".format(self.file_key, 
                                                                                               self.input_bucket,
                                                                                               self.file_download_path))
        return self.file_download_path
  
    def delete_file(self):
        self.client.delete_object(Bucket=self.input_bucket, Key=self.file_key)

    def get_file_key(self, function_name=None, folder=None, file_name=None):
        if function_name:
            return "{0}/{1}/{2}/{3}".format(function_name, folder, lambda_instance.request_id, file_name)
        else:
            return "{0}/{1}/{2}".format(folder, lambda_instance.request_id, file_name)

    def upload_output(self, bucket_name, bucket_folder=None):
        output_files_path = get_all_files_in_directory(lambda_instance.output_folder)
        logger.debug("UPLOADING FILES {0}".format(output_files_path))
        for file_path in output_files_path:
            file_name = file_path.replace("{0}/".format(lambda_instance.output_folder), "")
            if bucket_folder:
                file_key = self.get_file_key(folder=bucket_folder,
                                             file_name=file_name)
            else:
                file_key = self.get_file_key(function_name=lambda_instance.function_name,
                                             folder='output',
                                             file_name=file_name)
            self.upload_file(bucket_name, file_path, file_key)
            
    def upload_file(self, bucket_name, file_path, file_key):
        logger.info("Uploading file  '{0}' to bucket '{1}'".format(file_key, bucket_name))
        with open(file_path, 'rb') as data:
            self.client.upload_fileobj(data, bucket_name, file_key)
        logger.info("Changing ACLs for public-read for object in bucket {0} with key {1}".format(bucket_name, file_key))
        obj = boto3.resource('s3').Object(bucket_name, file_key)
        obj.Acl().put(ACL='public-read')
    
    def download_file_to_memory(self, bucket_name, file_key):
        obj = boto3.resource('s3').Object(bucket_name=bucket_name, key=file_key)
        print ("Reading item from bucket {0} with key {1}".format(bucket_name, file_key))
        return obj.get()["Body"].read()

#######################################
#    API GATEWAY RELATED FUNCTIONS    #
#######################################

class HTTP():
    
    def is_post_request_with_body(self):
        return lambda_instance.event['httpMethod'] == 'POST' and lambda_instance.event['body'] is not None
    
    def save_post_body(self):
        if self.is_post_request_with_body():
            body = base64.b64decode(lambda_instance.event['body'])
            body_file_name = uuid.uuid4().hex
            file_path = "/tmp/{0}/{1}".format(lambda_instance.request_id, body_file_name)
            logger.info("Received file from POST request and saved it in path '{0}'".format(file_path))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)  
            with open(file_path, 'wb') as data:
                data.write(body)
            return file_path

class Lambda():

    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.request_id = context.aws_request_id
        self.function_name = context.function_name
        self.temporal_folder = "/tmp/{0}".format(self.request_id)
        self.input_folder = "{0}/input".format(self.temporal_folder)
        self.output_folder = "{0}/output".format(self.temporal_folder)
        self.permanent_folder = "/var/task"         
        self.log_group_name = self.context.log_group_name
        self.log_stream_name = self.context.log_stream_name            

    @lazy_property
    def output_bucket(self):
        output_bucket = get_environment_variable('OUTPUT_BUCKET')
        return output_bucket
    
    @lazy_property
    def output_bucket_folder(self):
        output_folder = get_environment_variable('OUTPUT_FOLDER')
        return output_folder
    
    @lazy_property
    def input_bucket(self):
        input_bucket = get_environment_variable('INPUT_BUCKET')
        return input_bucket
    
    def has_output_bucket(self):
        return is_variable_in_environment('OUTPUT_BUCKET')

    def has_output_bucket_folder(self):
        return is_variable_in_environment('OUTPUT_FOLDER')
    
    def has_input_bucket(self):
        return is_variable_in_environment('INPUT_BUCKET')

    def get_invocation_remaining_seconds(self):
        return int(self.context.get_remaining_time_in_millis() / 1000) - int(get_environment_variable('TIMEOUT_THRESHOLD'))            
        
#######################################
#          UDOCKER FUNCTIONS          #
#######################################

class Udocker():

    udocker_exec = "/var/task/udockerb"
    container_name = "udocker_container"
    script_exec = "/bin/sh"

    def __init__(self, scar_input_file):
        self.container_output_file = "{0}/container-stdout.txt".format(lambda_instance.temporal_folder)
        self.scar_input_file = scar_input_file
        
        if is_variable_in_environment("IMAGE_ID"):
            self.container_image_id = get_environment_variable("IMAGE_ID")
            self.set_udocker_commands()
        else:
            raise Exception("Container image id not specified.")
    
    def set_udocker_commands(self):
        self.cmd_udocker = [self.udocker_exec]
        self.cmd_get_images = self.cmd_udocker + ["images"]
        self.cmd_load_image = self.cmd_udocker + ["load", "-i", self.container_image_id]
        self.cmd_download_image = self.cmd_udocker + ["pull", self.container_image_id]
        self.cmd_list_containers = self.cmd_udocker + ["ps"]
        self.cmd_create_container = self.cmd_udocker + ["create", "--name={0}".format(self.container_name), self.container_image_id]
        self.cmd_set_execution_mode = self.cmd_udocker + ["setup", "--execmode=F1", self.container_name]
        self.cmd_container_execution = self.cmd_udocker + ["--quiet", "run"]
        
    def is_container_image_downloaded(self):
        cmd_out = execute_command_and_return_output(self.cmd_get_images)
        return self.container_image_id in cmd_out              

    def create_image(self):
        if self.is_container_image_downloaded():
            logger.info("Container image '{0}' already available".format(self.container_image_id))
        else:                     
            if is_variable_in_environment("IMAGE_FILE"):
                self.load_local_container_image()
            else:
                self.download_container_image()        

    def load_local_container_image(self):
        logger.info("Loading container image '{0}'".format(self.container_image_id))
        execute_command(self.cmd_load_image)
        
    def download_container_image(self):
        logger.info("Pulling container '{0}' from Docker Hub".format(self.container_image_id))
        execute_command(self.cmd_download_image)

    def is_container_available(self):
        cmd_out = execute_command_and_return_output(self.cmd_list_containers)
        return self.container_name in cmd_out      

    def create_container(self):
        if self.is_container_available():
            logger.info("Container already available")
        else:
            logger.info("Creating container based on image '{0}'.".format(self.container_image_id))
            execute_command(self.cmd_create_container)
            execute_command(self.cmd_set_execution_mode)

    def create_command(self):
        self.add_container_volumes()
        self.add_container_environment_variables()
        # Container running script
        if check_key_in_dictionary('script', lambda_instance.event): 
            self.add_script_as_entrypoint()
        # Container with args
        elif check_key_in_dictionary('cmd_args', lambda_instance.event):
            self.add_args()
        # Script to be executed every time (if defined)
        elif is_variable_in_environment('INIT_SCRIPT_PATH'):
            self.add_init_script()
        # Only container
        else:
            self.cmd_container_execution += [self.container_name]
    
    def add_container_volumes(self):
        self.cmd_container_execution += ["-v", lambda_instance.temporal_folder]
        self.cmd_container_execution += ["-v", "/dev", "-v", "/proc", "-v", "/etc/hosts", "--nosysdirs"]
        if is_variable_in_environment('EXTRA_PAYLOAD'):
            self.cmd_container_execution += ["-v", lambda_instance.permanent_folder]

    def add_container_environment_variable(self, key, value):
        self.cmd_container_execution += self.parse_container_environment_variable(key, value)
            
    def add_container_environment_variables(self):
        self.cmd_container_execution += self.parse_container_environment_variable("REQUEST_ID", lambda_instance.request_id)
        self.cmd_container_execution += self.parse_container_environment_variable("INSTANCE_IP", 
                                                                                  socket.gethostbyname(socket.gethostname()))        
        self.cmd_container_execution += self.get_user_defined_variables()
        self.cmd_container_execution += self.get_iam_credentials()        
        self.cmd_container_execution += self.get_session_and_security_token()
        self.cmd_container_execution += self.get_input_file()
        self.cmd_container_execution += self.get_extra_payload_path()
        self.cmd_container_execution += self.get_lambda_output_variable()
       
    def parse_container_environment_variable(self, key, value):
        var = []
        if key and value and key != "" and value != "":
            var += ["--env", str(key) + '=' + str(value)]
        return var
        
    def get_user_defined_variables(self):
        user_vars = []
        for key in os.environ.keys():
            # Find global variables with the specified prefix
            if re.match("CONT_VAR_.*", key):
                user_vars += self.parse_container_environment_variable(key.replace("CONT_VAR_", ""),
                                                                       get_environment_variable(key)) 
        return user_vars                      

    def get_iam_credentials(self):
        creds = []
        iam_creds = {'CONT_VAR_AWS_ACCESS_KEY_ID':'AWS_ACCESS_KEY_ID', 
                     'CONT_VAR_AWS_SECRET_ACCESS_KEY':'AWS_SECRET_ACCESS_KEY'}
        # Add IAM credentials
        for key,value in iam_creds.items():
            if not is_variable_in_environment(key):
                creds += self.parse_container_environment_variable(value, 
                                                                   get_environment_variable(value))
        return creds
    
    def get_session_and_security_token(self):
        tokens = []
        # Always add Session and security tokens
        tokens += self.parse_container_environment_variable("AWS_SESSION_TOKEN",
                                                            get_environment_variable("AWS_SESSION_TOKEN"))
        tokens += self.parse_container_environment_variable("AWS_SECURITY_TOKEN",
                                                            get_environment_variable("AWS_SECURITY_TOKEN"))
        return tokens
            
    def get_input_file(self):
        file = []
        if self.scar_input_file and self.scar_input_file != "":
            file += self.parse_container_environment_variable("SCAR_INPUT_FILE", self.scar_input_file)
        return file
            
    def get_extra_payload_path(self):
        ppath = []
        if is_variable_in_environment('EXTRA_PAYLOAD'):
            ppath += self.parse_container_environment_variable("EXTRA_PAYLOAD", 
                                                               get_environment_variable("EXTRA_PAYLOAD"))
        return ppath
          
    def get_lambda_output_variable(self):
        out_lambda = []
        if is_variable_in_environment('OUTPUT_LAMBDA'):
            set_environment_variable("OUTPUT_LAMBDA_FILE", "/tmp/{0}/lambda_output".format(lambda_instance.request_id))
            out_lambda += self.parse_container_environment_variable("OUTPUT_LAMBDA_FILE", 
                                                                    get_environment_variable("EXTRA_PAYLOAD"))
        return out_lambda      
            
    def add_script_as_entrypoint(self):
        script_path = "{0}/script.sh".format(lambda_instance.temporal_folder)
        script_content = undo_escape_string(lambda_instance.event['script'])
        create_file_with_content(script_path, script_content)
        self.cmd_container_execution += ["--entrypoint={0} {1}".format(self.script_exec, script_path), self.container_name]

    def add_args(self):
        self.cmd_container_execution += [self.container_name]
        # Parse list of strings
        args = lambda_instance.event['cmd_args']
        parsed_args = args[1:-1].replace('"', '').split(', ')
        self.cmd_container_execution += parsed_args
    
    def add_init_script(self):
        init_script_path = "{0}/init_script.sh".format(lambda_instance.temporal_folder)
        shutil.copyfile("{0}/init_script.sh".format(lambda_instance.permanent_folder), init_script_path)    
        self.cmd_container_execution += ["--entrypoint={0} {1}".format(self.script_exec, init_script_path), self.container_name]
    
    def launch_udocker_container(self):
        remaining_seconds = lambda_instance.get_invocation_remaining_seconds()
        logger.info("Executing udocker container. Timeout set to {0} seconds".format(remaining_seconds))
        logger.debug("Udocker command: {0}".format(self.cmd_container_execution))
        with subprocess.Popen(self.cmd_container_execution, 
                              stderr=subprocess.STDOUT, 
                              stdout=open(self.container_output_file, "w"), 
                              preexec_fn=os.setsid) as process:
            try:
                process.wait(timeout=remaining_seconds)
            except subprocess.TimeoutExpired:
                kill_process(process)
                logger.warning("Container timeout")
                raise
        
        if os.path.isfile(self.container_output_file):
            return read_file(self.container_output_file)
        
#####################################################################################################################

class Supervisor():
    
    scar_input_file = None
    response = {}
    status_code = 200
    body = {}
    
    @lazy_property
    def s3(self):
        s3 = S3()
        return s3
    
    @lazy_property
    def http(self):
        http = HTTP()
        return http
    
    @lazy_property
    def udocker(self):
        udocker = Udocker(self.scar_input_file)
        return udocker
    
    def __init__(self):
        self.create_temporal_folders()
        self.create_event_file()

    def is_s3_event(self):
        if check_key_in_dictionary('Records', lambda_instance.event):
            # Check if the event is an S3 event
            return lambda_instance.event['Records'][0]['eventSource'] == "aws:s3"
        return False
           
    def is_http_event(self):
        return 'httpMethod' in lambda_instance.event           
           
    def parse_input(self):
        if self.is_s3_event():
            self.input_bucket = self.s3.input_bucket
            logger.debug("INPUT BUCKET SET TO {0}".format(self.input_bucket))
            self.scar_input_file = self.s3.download_input()
            logger.debug("INPUT FILE SET TO {0}".format(self.scar_input_file))
        elif self.is_http_event():
            self.scar_input_file = self.http.save_post_body()
            logger.debug("INPUT FILE SET TO {0}".format(self.scar_input_file))
        
    def prepare_udocker(self):
        self.udocker.create_image()
        self.udocker.create_container()
        self.udocker.create_command()
        
    def execute_udocker(self):
        try:
            udocker_output = self.udocker.launch_udocker_container()
            logger.info("CONTAINER OUTPUT: " + udocker_output)
            self.body["udocker_output"] = udocker_output            
        except subprocess.TimeoutExpired:
            logger.warning("Container execution timed out")
                
    def has_input_bucket(self):
        return hasattr(self, "input_bucket") and self.input_bucket and self.input_bucket != "" 

    def upload_to_bucket(self):
        bucket_name = None
        bucket_folder = None
        if lambda_instance.has_output_bucket():
            bucket_name = lambda_instance.output_bucket
            logger.debug("OUTPUT BUCKET SET TO {0}".format(bucket_name))
            if lambda_instance.has_output_bucket_folder():
                bucket_folder = lambda_instance.output_bucket_folder
                logger.debug("OUTPUT FOLDER SET TO {0}".format(bucket_folder))
        elif lambda_instance.has_input_bucket():
            bucket_name = lambda_instance.input_bucket
            logger.debug("OUTPUT BUCKET SET TO {0}".format(bucket_name))
        if bucket_name:
            self.s3.upload_output(bucket_name, bucket_folder)

    def parse_output(self):
        # Check if we have to store the result in a bucket
        self.upload_to_bucket()
        # Create the function response
        self.create_response()
        self.clean_instance_files()
        
    def create_response(self):
        return {"statusCode" : self.status_code, 
                "headers" : { 
                    "amz-lambda-request-id": lambda_instance.request_id, 
                    "amz-log-group-name": lambda_instance.log_group_name, 
                    "amz-log-stream-name": lambda_instance.log_stream_name },
                "body" : json.dumps(self.body),
                "isBase64Encoded" : False                
                }
        
    def clean_instance_files(self):
        # Delete all the temporal folders created for the invocation
        shutil.rmtree("/tmp/%s" % lambda_instance.request_id)        
        
    def create_temporal_folders(self):
        create_folder(lambda_instance.temporal_folder)
        create_folder(lambda_instance.input_folder)
        create_folder(lambda_instance.output_folder)
    
    def create_event_file(self):
        create_file_with_content("{0}/event.json".format(lambda_instance.temporal_folder),
                                 json.dumps(lambda_instance.event))        
        
#######################################
#           USEFUL FUNCTIONS          #
#######################################
def create_folder(folder_name):
    if not os.path.isdir(folder_name):
        os.makedirs(folder_name, exist_ok=True)

def kill_process(self, process):
    logger.info("Stopping process '{0}'".format(process))
    # Using SIGKILL instead of SIGTERM to ensure the process finalization 
    os.killpg(os.getpgid(process.pid), subprocess.signal.SIGKILL)

def read_file(file_path):
    with open(file_path, 'r') as content_file:
        return content_file.read() 

def execute_command(command):
    subprocess.call(command)
    
def execute_command_and_return_output(command):
    return subprocess.check_output(command).decode("utf-8")

def is_variable_in_environment(variable):
    return check_key_in_dictionary(variable, os.environ)

def set_environment_variable(key, variable):
    if key and variable and key != "" and variable != "":
        os.environ[key] = variable

def get_environment_variable(variable):
    if check_key_in_dictionary(variable, os.environ):
        return os.environ[variable]

def check_key_in_dictionary(key, dictionary):
    return (key in dictionary) and dictionary[key] and dictionary[key] != ""

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

def create_tar_gz(files_to_archive, destination_tar_path):
    with tarfile.open(destination_tar_path, "w:gz") as tar:
        for file_path in files_to_archive:
            tar.add(file_path, arcname=os.path.basename(file_path))
    return destination_tar_path
        
def extract_tar_gz(tar_path, destination_path):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=destination_path)
    logging.info("Successfully extracted '%s' in path '%s'" % (tar_path, destination_path))
    
def set_instance_properties(event, context):
    global lambda_instance
    lambda_instance = Lambda(event, context)    

#####################################################################################################################

def lambda_handler(event, context):
    logger.debug("Received event: " + json.dumps(event))
    set_instance_properties(event, context)
    supervisor = Supervisor()
    try:
        supervisor.parse_input()
        supervisor.prepare_udocker()
        supervisor.execute_udocker()                                      
        supervisor.parse_output()
    except Exception:
        logger.error("Exception launched:\n {0}".format(traceback.format_exc()))
        supervisor.body["exception"] = traceback.format_exc()
        supervisor.status_code = 500
    
    return supervisor.create_response()
