# SCAR - Serverless Container-aware ARchitectures
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


from .clients.lambdac import LambdaClient
from .clients.iam import IAMClient

import utils.functionutils as utils
import utils.outputtype as outputType
from utils.config import Config

import json
import logging
import os
import shutil
import tempfile
import zipfile

MAX_PAYLOAD_SIZE = 50 * 1024 * 1024
MAX_S3_PAYLOAD_SIZE = 250 * 1024 * 1024

default_invocation_type = "RequestResponse"
default_log_type = "Tail"
default_output = outputType.PLAIN_TEXT
default_payload = "{}"
default_tags = {}
default_udocker_dir = "/tmp/home/.udocker"
default_udocker_tarball = "/var/task/udocker-1.1.0-RC2.tar.gz"
default_zip_file_path = os.path.join(tempfile.gettempdir(), 'function.zip')
default_recursive_behavior = False 
default_asynchronous_behavior = False
s3_event_template = { "Records" : [ 
                        { "eventSource" : "aws:s3",
                          "s3" : { "bucket" : { "name" : "" },
                                   "object" : { "key" : ""  } }
                        }
                    ]}
lambda_environment_template = { 'Variables' : {} }

class AWSLambda(object):

    def __init__(self):
        self.initialize_properties()
        self.set_config_file_properties()
        self.validate_lambda_configuration()

    def set_config_file_properties(self):
        config = Config()
        self.role = config.get_iam_role()
        self.name = config.get_lambda_name()
        self.region = config.get_lambda_region()
        self.memory = config.get_lambda_memory()
        self.time = config.get_lambda_execution_time()
        self.description = config.get_lambda_description()
        self.timeout_threshold = config.get_lambda_timeout_threshold()
        self.runtime = config.get_lambda_runtime()
        self.log_retention_policy_in_days = config.get_cloudwatch_log_retention_policy_in_days()

    def validate_lambda_configuration(self):
        if not self.role or self.role == "":
            logging.error("Please, specify a valid iam role in the configuration file (usually located in ~/.scar/scar_aws.cfg).")
            print("Please, specify a valid iam role in the configuration file (usually located in ~/.scar/scar_aws.cfg).")
            utils.finish_failed_execution()

    def initialize_properties(self):
        # Parameters needed to create the function in aws
        self.role = None
        self.region = None
        self.memory = None
        self.time = None               
        self.description = None
        self.timeout_threshold = None        
        self.code = None
        self.container_arguments = None
        self.event_source = None
        self.extra_payload = None
        self.function_arn = None
        self.handler = None
        self.image_id = None
        self.image_file = None
        self.log_group_name = None
        self.log_retention_policy_in_days = None
        self.log_stream_name = None
        self.name = None
        self.request_id = None
        self.runtime = None
        self.scar_call = None
        self.script = None
        self.deployment_bucket = None   
        self.delete_all = False
        self.environment = lambda_environment_template
        self.event = s3_event_template              
        self.log_type = default_log_type     
        self.asynchronous_call = default_asynchronous_behavior        
        self.invocation_type = default_invocation_type        
        self.output = default_output
        self.payload = default_payload
        self.recursive = default_recursive_behavior        
        self.tags = default_tags
        self.udocker_dir = default_udocker_dir
        self.udocker_tarball = default_udocker_tarball
        self.zip_file_path = default_zip_file_path

    def set_log_stream_name(self, stream_name):
        self.log_stream_name = stream_name
        
    def set_request_id(self, request_id):
        self.request_id = request_id
        
    def is_asynchronous(self):
        return self.asynchronous_call

    def has_event_source(self):
        return (self.event_source is not None)
    
    def delete_all(self):
        return self.delete_all
        
    def has_verbose_output(self):
        return self.verbose_output
    
    def has_json_output(self):
        return self.json_output

    def set_deployment_bucket(self, deployment_bucket):
        self.deployment_bucket = deployment_bucket
        
    def set_payload(self, payload):
        self.payload = json.dumps(payload)
        
    def set_cont_args(self, container_arguments):
        self.container_arguments = container_arguments

    def set_async(self, asynchronous_call):
        if asynchronous_call:
            self.set_asynchronous_call_parameters()
        else:
            self.set_request_response_call_parameters()

    def set_func(self, scar_call):
        self.scar_call = scar_call.__name__

    def set_asynchronous_call_parameters(self):
        self.asynchronous_call = True
        self.invocation_type = "Event"
        self.log_type = "None"

    def set_request_response_call_parameters(self):
        self.asynchronous_call = False
        self.invocation_type = "RequestResponse"
        self.log_type = "Tail"

    def set_name(self, name):
        if not utils.is_valid_aws_name(name):
            print("'%s' is an invalid lambda function name." % name)
            logging.error("'%s' is an invalid lambda function name." % name)
            utils.finish_failed_execution()            
        self.name = name        
    
    def set_image_id(self, image_id):
        self.image_id = image_id
        if not hasattr(self, 'name') or self.name == "":
            self.set_name(LambdaClient().create_function_name(image_id))
    
    def set_image_file(self, image_file):
        self.image_file = image_file
    
    def set_memory(self, memory):
        self.memory = self.check_memory(memory)
        
    def check_memory(self, lambda_memory):
        """ Check if the memory introduced by the user is correct.
        If the memory is not specified in 64mb increments,
        transforms the request to the next available increment."""
        if (lambda_memory < 128) or (lambda_memory > 1536):
            raise Exception('Incorrect memory size specified\nPlease, set a value between 128 and 1536.')
        else:
            res = lambda_memory % 64
            if (res == 0):
                return lambda_memory
            else:
                return lambda_memory - res + 64

    def set_time(self, time):
        self.time = self.check_time(time)
        
    def check_time(self, lambda_time):
        if (lambda_time <= 0) or (lambda_time > 300):
            raise Exception('Incorrect time specified\nPlease, set a value between 0 and 300.')
        return lambda_time          
        
    def set_timeout_threshold(self, timeout_threshold):
        self.timeout_threshold = timeout_threshold
        
    def set_json(self, json):
        if json:
            self.output = outputType.JSON
        
    def set_verbose(self, verbose):
        if verbose:
            self.output = outputType.VERBOSE
        
    def set_script(self, script):
        self.script = script
        
    def set_event_source(self, event_source):
        ''' Sets the S3 bucket name from where the events are going to be launched'''
        self.event_source = event_source
        self.event['Records'][0]['s3']['bucket']['name'] = event_source
        
    def set_event_source_file_name(self, file_name):
        self.event['Records'][0]['s3']['object']['key'] = file_name        
        
    def set_lambda_role(self, lambda_role):
        self.lambda_role = lambda_role
        
    def set_recursive(self, recursive):
        self.recursive = recursive
        
    def set_preheat(self, preheat):
        self.preheat = preheat
        
    def set_extra_payload(self, extra_payload):
        self.extra_payload = extra_payload

    def set_code(self):
        # Zip all the files and folders needed
        self.create_zip_file()
        self.code = {"ZipFile": utils.get_file_as_byte_array(self.zip_file_path)}
        
    def set_evironment_variable(self, key, value):
        self.environment['Variables'][key] = value
               
    def set_required_environment_variables(self):
        self.set_evironment_variable('UDOCKER_DIR', self.udocker_dir)
        self.set_evironment_variable('UDOCKER_TARBALL', self.udocker_tarball)
        self.set_evironment_variable('TIMEOUT_THRESHOLD', str(self.timeout_threshold))
        self.set_evironment_variable('RECURSIVE', str(self.recursive))
        self.set_evironment_variable('IMAGE_ID', self.image_id)        

    def set_environment_variables(self, variables):
        for env_var in variables:
            parsed_env_var = env_var.split("=")
            # Add an specific prefix to be able to find the variables defined by the user
            key = 'CONT_VAR_' + parsed_env_var[0]
            self.set_evironment_variable(key, parsed_env_var[1])

    def set_tags(self):
        self.tags['createdby'] = 'scar'
        self.tags['owner'] = IAMClient().get_user_name_or_id()

    def set_all(self, value):
        self.delete_all = value
          
    def get_argument_value(self, args, attr):
        if attr in args.__dict__.keys():
            return args.__dict__[attr]

    def update_function_attributes(self, args):
        if self.get_argument_value(args, 'memory'):
            LambdaClient().update_function_memory(self.name, self.memory)
        if self.get_argument_value(args, 'time'):
            LambdaClient().update_function_timeout(self.name, self.time)
        if self.get_argument_value(args, 'env'):
            LambdaClient().update_function_env_variables(self.name, self.environment)        

    def check_function_name(self):
        if self.name:
            if self.scar_call == 'init':
                LambdaClient().check_function_name_exists(self.name)
            elif (self.scar_call == 'rm') or (self.scar_call == 'run'):
                LambdaClient().check_function_name_not_exists(self.name)

    def set_attributes(self, args):
        # First set command line attributes
        for attr in args.__dict__.keys():
            value = self.get_argument_value(args, attr)
            try:
                if value is not None:
                    method_name = 'set_' + attr
                    method = getattr(self, method_name)
                    method(value)
            except Exception as ex:
                logging.error(ex)
        
        self.check_function_name()
        self.set_required_environment_variables()
        if self.name:
            self.handler = self.name + ".lambda_handler"
            self.log_group_name = '/aws/lambda/' + self.name
        if self.scar_call == 'init':
            self.set_tags()
            self.set_code()
        elif self.scar_call == 'run':
            self.update_function_attributes(args)
            if self.get_argument_value(args, 'script'):
                self.set_payload(self.create_payload("script", self.get_escaped_script()))
            if self.get_argument_value(args, 'cont_args'):
                self.set_payload(self.create_payload("cmd_args", self.get_parsed_cont_args()))             

    def create_payload(self, key, value):
        return { key : value }

    def get_escaped_script(self):
        return utils.escape_string(self.script.read())

    def get_parsed_cont_args(self):
        return utils.escape_list(self.container_arguments)

    def get_scar_abs_path(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    def create_zip_file(self):
        scar_dir = self.get_scar_abs_path()
        # Set lambda function name
        function_name = self.name + '.py'
        # Copy file to avoid messing with the repo files
        # We have to rename the file because the function name affects the handler name
        shutil.copy(scar_dir + '/lambda/scarsupervisor.py', function_name)
        # Zip the function file
        with zipfile.ZipFile(self.zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # AWSLambda function code
            zf.write(function_name)
            utils.delete_file(function_name)
            # Udocker script code
            zf.write(scar_dir + '/lambda/udocker', 'udocker')
            # Udocker libs
            zf.write(scar_dir + '/lambda/udocker-1.1.0-RC2.tar.gz', 'udocker-1.1.0-RC2.tar.gz')
    
            if self.script:
                zf.write(self.script, 'init_script.sh')
                self.set_evironment_variable('INIT_SCRIPT_PATH', "/var/task/init_script.sh")
                
        if self.extra_payload:
            utils.zip_folder(self.zip_file_path, self.extra_payload)
            self.set_evironment_variable('EXTRA_PAYLOAD', "/var/task/extra/")
    
        # Add docker image file
        if self.image_file and self.deployment_bucket:
            self.add_image_file()
        # Check if the payload size fits within the aws limits
        self.check_payload_size()

    def add_image_file(self):
        utils.add_file_to_zip(self.zip_file_path, self.image_file, self.name)

    def check_payload_size(self):
        if((not self.deployment_bucket) and (os.path.getsize(self.zip_file_path) > MAX_PAYLOAD_SIZE)):
            error_message = "Error: Payload size greater than 50MB.\nPlease specify an S3 bucket to deploy the function.\n"
            self.payload_size_error(error_message)
        
        if(os.path.getsize(self.zip_file_path) > MAX_S3_PAYLOAD_SIZE):            
            error_message = "Error: Payload size greater than 250MB.\nPlease reduce the payload size and try again.\n"
            self.payload_size_error(error_message)

    def payload_size_error(self, message):
        logging.error(message)
        print(message)
        utils.delete_file(self.zip_file_path)
        utils.finish_failed_execution()
    