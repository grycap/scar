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
import socket
import uuid
import base64
import sys
from urllib.parse import unquote_plus

sys.path.append("..")
sys.path.append(".")
# Works in lambda environment
import src.utils as utils

logger = logging.getLogger()
if utils.is_variable_in_environment('LOG_LEVEL'):
    logger.setLevel(utils.get_environment_variable('LOG_LEVEL'))
else:
    logger.setLevel('INFO')
logger.info('SCAR: Loading lambda function')
lambda_instance = None

#######################################
#        S3 RELATED FUNCTIONS         #
#######################################
class S3():
    
    @utils.lazy_property
    def client(self):
        client = boto3.client('s3')
        return client
    
    def __init__(self):
        if utils.is_value_in_dict(lambda_instance.event, 'Records'):
            self.record = self.get_s3_record()
            self.input_bucket = self.record['bucket']['name']
            self.file_key = unquote_plus(self.record['object']['key'])
            self.file_name = os.path.basename(self.file_key).replace(' ', '')
            self.file_download_path = '{0}/{1}'.format(lambda_instance.input_folder, self.file_name) 
    def get_s3_record(self):
        if len(lambda_instance.event['Records']) > 1:
            logger.warning("Multiple records detected. Only processing the first one.")
            
        record = lambda_instance.event['Records'][0]
        if utils.is_value_in_dict(record, 's3'):
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
  
    def get_file_key(self, function_name=None, folder=None, file_name=None):
        if function_name:
            return "{0}/{1}/{2}/{3}".format(function_name, folder, lambda_instance.request_id, file_name)
        else:
            return "{0}/{1}/{2}".format(folder, lambda_instance.request_id, file_name)

    def upload_output(self, bucket_name, bucket_folder=None):
        output_files_path = utils.get_all_files_in_directory(lambda_instance.output_folder)
        logger.debug("UPLOADING FILES {0}".format(output_files_path))
        for file_path in output_files_path:
            file_name = file_path.replace("{0}/".format(lambda_instance.output_folder), "")
            if bucket_folder:
                file_key = self.get_file_key(folder=bucket_folder, file_name=file_name)
            else:
                file_key = self.get_file_key(function_name=lambda_instance.function_name, folder='output', file_name=file_name)
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
    
    def delete_file(self):
        self.client.delete_object(Bucket=self.input_bucket, Key=self.file_key)    

#######################################
#    API GATEWAY RELATED FUNCTIONS    #
#######################################

class HTTP():

    def is_post_request_with_body(self):
        return lambda_instance.event['httpMethod'] == 'POST' and lambda_instance.event['body'] is not None

    def is_post_request_with_body_json(self):
        return lambda_instance.event['httpMethod'] == 'POST' and lambda_instance.event['headers']['Content-Type'].strip() == 'application/json'

    def save_post_body_json(self):
        body = lambda_instance.event['body']
        file_path = "/tmp/{0}/api_event.json".format(lambda_instance.request_id)
        logger.info("Received JSON from POST request and saved it in path '{0}'".format(file_path))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  
        with open(file_path, 'w') as event_file:
            event_file.write(body)
        return file_path

    def save_post_body_file(self):
        body = base64.b64decode(lambda_instance.event['body'])
        body_file_name = uuid.uuid4().hex
        file_path = "/tmp/{0}/{1}".format(lambda_instance.request_id, body_file_name)
        logger.info("Received file from POST request and saved it in path '{0}'".format(file_path))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  
        with open(file_path, 'wb') as data:
            data.write(body)
        return file_path

    def save_post_body(self):
        if self.is_post_request_with_body_json():
            return self.save_post_body_json()
        elif self.is_post_request_with_body:
            return self.save_post_body_file()

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

    @utils.lazy_property
    def output_bucket(self):
        output_bucket = utils.get_environment_variable('OUTPUT_BUCKET')
        return output_bucket
    
    @utils.lazy_property
    def output_bucket_folder(self):
        output_folder = utils.get_environment_variable('OUTPUT_FOLDER')
        return output_folder
    
    @utils.lazy_property
    def input_bucket(self):
        input_bucket = utils.get_environment_variable('INPUT_BUCKET')
        return input_bucket
    
    def has_output_bucket(self):
        return utils.is_variable_in_environment('OUTPUT_BUCKET')

    def has_output_bucket_folder(self):
        return utils.is_variable_in_environment('OUTPUT_FOLDER')
    
    def has_input_bucket(self):
        return utils.is_variable_in_environment('INPUT_BUCKET')

    def get_invocation_remaining_seconds(self):
        return int(self.context.get_remaining_time_in_millis() / 1000) - int(utils.get_environment_variable('TIMEOUT_THRESHOLD'))            
        
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
        
        if utils.is_variable_in_environment("IMAGE_ID"):
            self.container_image_id = utils.get_environment_variable("IMAGE_ID")
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
        cmd_out = utils.execute_command_and_return_output(self.cmd_get_images)
        return self.container_image_id in cmd_out              

    def create_image(self):
        if self.is_container_image_downloaded():
            logger.info("Container image '{0}' already available".format(self.container_image_id))
        else:                     
            if utils.is_variable_in_environment("IMAGE_FILE"):
                self.load_local_container_image()
            else:
                self.download_container_image()        

    def load_local_container_image(self):
        logger.info("Loading container image '{0}'".format(self.container_image_id))
        utils.execute_command(self.cmd_load_image)
        
    def download_container_image(self):
        logger.info("Pulling container '{0}' from Docker Hub".format(self.container_image_id))
        utils.execute_command(self.cmd_download_image)

    def is_container_available(self):
        cmd_out = utils.execute_command_and_return_output(self.cmd_list_containers)
        return self.container_name in cmd_out      

    def create_container(self):
        if self.is_container_available():
            logger.info("Container already available")
        else:
            logger.info("Creating container based on image '{0}'.".format(self.container_image_id))
            utils.execute_command(self.cmd_create_container)
        utils.execute_command(self.cmd_set_execution_mode)

    def create_command(self):
        self.add_container_volumes()
        self.add_container_environment_variables()
        # Container running script
        if utils.is_value_in_dict(lambda_instance.event, 'script'): 
            self.add_script_as_entrypoint()
        # Container with args
        elif utils.is_value_in_dict(lambda_instance.event,'cmd_args'):
            self.add_args()
        # Script to be executed every time (if defined)
        elif utils.is_variable_in_environment('INIT_SCRIPT_PATH'):
            self.add_init_script()
        # Only container
        else:
            self.cmd_container_execution += [self.container_name]
    
    def add_container_volumes(self):
        self.cmd_container_execution += ["-v", lambda_instance.temporal_folder]
        self.cmd_container_execution += ["-v", "/dev", "-v", "/proc", "-v", "/etc/hosts", "--nosysdirs"]
        if utils.is_variable_in_environment('EXTRA_PAYLOAD'):
            self.cmd_container_execution += ["-v", lambda_instance.permanent_folder]

    def add_container_environment_variable(self, key, value):
        self.cmd_container_execution += self.parse_container_environment_variable(key, value)
            
    def add_container_environment_variables(self):
        self.cmd_container_execution += self.parse_container_environment_variable("REQUEST_ID", lambda_instance.request_id)
        self.cmd_container_execution += self.parse_container_environment_variable("INSTANCE_IP", 
                                                                                  socket.gethostbyname(socket.gethostname()))        
        self.cmd_container_execution += self.get_user_defined_variables()
        self.cmd_container_execution += self.get_decrypted_variables()
        self.cmd_container_execution += self.get_iam_credentials()
        self.cmd_container_execution += self.get_input_file()
        self.cmd_container_execution += self.get_output_dir()
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
                                                                       utils.get_environment_variable(key))
        return user_vars

    def get_decrypted_variables(self):
        decrypted_vars = []
        session = boto3.session.Session()
        client = session.client('kms')
        for key in os.environ.keys():
            if re.match("CONT_VAR_KMS_ENC_.*", key):
                secret  = utils.get_environment_variable(key)
                decrypt = client.decrypt(CiphertextBlob=bytes(base64.b64decode(secret)))["Plaintext"]
                decrypted_vars += self.parse_container_environment_variable(key.replace("CONT_VAR_KMS_ENC", "KMS_DEC"),
                                                                            decrypt.decode("utf-8"))
        return decrypted_vars

    def get_iam_credentials(self):
        creds = []
        iam_creds = {'CONT_VAR_AWS_ACCESS_KEY_ID':'AWS_ACCESS_KEY_ID',
                     'CONT_VAR_AWS_SECRET_ACCESS_KEY':'AWS_SECRET_ACCESS_KEY',
                     'CONT_VAR_AWS_SESSION_TOKEN':'AWS_SESSION_TOKEN'}
        # Add IAM credentials
        for key,value in iam_creds.items():
            if not utils.is_variable_in_environment(key):
                creds += self.parse_container_environment_variable(value, 
                                                                   utils.get_environment_variable(value))
        return creds
    
    def get_input_file(self):
        file = []
        if self.scar_input_file and self.scar_input_file != "":
            file += self.parse_container_environment_variable("SCAR_INPUT_FILE", self.scar_input_file)
        return file

    def get_output_dir(self):
        return self.parse_container_environment_variable("SCAR_OUTPUT_DIR", 
                                                         "/tmp/{0}/output".format(lambda_instance.request_id))
            
    def get_extra_payload_path(self):
        ppath = []
        if utils.is_variable_in_environment('EXTRA_PAYLOAD'):
            ppath += self.parse_container_environment_variable("EXTRA_PAYLOAD", 
                                                               utils.get_environment_variable("EXTRA_PAYLOAD"))
        return ppath
          
    def get_lambda_output_variable(self):
        out_lambda = []
        if utils.is_variable_in_environment('OUTPUT_LAMBDA'):
            utils.set_environment_variable("OUTPUT_LAMBDA_FILE", "/tmp/{0}/lambda_output".format(lambda_instance.request_id))
            out_lambda += self.parse_container_environment_variable("OUTPUT_LAMBDA_FILE", 
                                                                    utils.get_environment_variable("EXTRA_PAYLOAD"))
        return out_lambda      
            
    def add_script_as_entrypoint(self):
        script_path = "{0}/script.sh".format(lambda_instance.temporal_folder)
        script_content = utils.base64_to_utf8_string(lambda_instance.event['script'])
        utils.create_file_with_content(script_path, script_content)
        self.cmd_container_execution += ["--entrypoint={0} {1}".format(self.script_exec, script_path), self.container_name]

    def add_args(self):
        self.cmd_container_execution += [self.container_name]
        self.cmd_container_execution += json.loads(lambda_instance.event['cmd_args'])
    
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
                logger.info("Stopping process '{0}'".format(process))
                utils.kill_process(process)
                logger.warning("Container timeout")
                raise
        
        if os.path.isfile(self.container_output_file):
            return utils.read_file(self.container_output_file)
        
#####################################################################################################################

class Supervisor():
    
    scar_input_file = None
    response = {}
    status_code = 200
    body = {}
    
    @utils.lazy_property
    def s3(self):
        s3 = S3()
        return s3
    
    @utils.lazy_property
    def http(self):
        http = HTTP()
        return http
    
    @utils.lazy_property
    def udocker(self):
        udocker = Udocker(self.scar_input_file)
        return udocker
    
    def __init__(self):
        self.create_temporal_folders()
        self.create_event_file()

    def is_s3_event(self):
        if utils.is_value_in_dict(lambda_instance.event, 'Records'):
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
            logger.info("CONTAINER OUTPUT:\n " + udocker_output)
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
        utils.create_folder(lambda_instance.temporal_folder)
        utils.create_folder(lambda_instance.input_folder)
        utils.create_folder(lambda_instance.output_folder)
    
    def create_event_file(self):
        utils.create_file_with_content("{0}/event.json".format(lambda_instance.temporal_folder), json.dumps(lambda_instance.event))        
        
#####################################################################################################################
def set_instance_properties(event, context):
    global lambda_instance
    lambda_instance = Lambda(event, context)

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
