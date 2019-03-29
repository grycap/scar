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

from botocore.exceptions import ClientError
from multiprocessing.pool import ThreadPool
from scar.providers.aws.botoclientfactory import GenericClient
from scar.providers.aws.functioncode import FunctionPackager
from scar.providers.aws.lambdalayers import LambdaLayers
from scar.providers.aws.s3 import S3
from scar.providers.aws.validators import AWSValidator
import base64
import json
import random
import scar.exceptions as excp
import scar.http.request as request
import scar.logger as logger
import scar.providers.aws.response as response_parser
import scar.utils as utils

MAX_CONCURRENT_INVOCATIONS = 500

class Lambda(GenericClient):
    
    @utils.lazy_property
    def layers(self):
        layers = LambdaLayers(self.client)
        return layers
    
    @utils.lazy_property
    def s3(self):
        s3 = S3(self.aws)
        return s3    
    
    def __init__(self, aws_properties):
        super().__init__(aws_properties)
        self._initialize_properties()

    def _initialize_properties(self):
        self.aws._lambda.environment = {'Variables' : {}}
        self.aws._lambda.zip_file_path = utils.join_paths(utils.get_tmp_dir(), 'function.zip')
        self.aws._lambda.invocation_type = "RequestResponse"
        self.aws._lambda.log_type = "Tail"
        self.aws._lambda.layers = []
        if hasattr(self.aws._lambda, "name"):
            self.aws._lambda.handler = "{0}.lambda_handler".format(self.aws._lambda.name)
        if not hasattr(self.aws._lambda, "asynchronous"):
            self.aws._lambda.asynchronous = False
        self._set_default_call_parameters()

    def is_asynchronous(self):
        return self.aws._lambda.asynchronous

    def _set_default_call_parameters(self):
        self.asynchronous_call_parameters = {"invocation_type" : "Event",
                                             "log_type" : "None",
                                             "asynchronous" : "True"}
        self.request_response_call_parameters = {"invocation_type" : "RequestResponse",
                                                 "log_type" : "Tail",
                                                 "asynchronous" : "False"}               

    def _get_creations_args(self):
        return {'FunctionName' : self.aws._lambda.name,
                'Runtime' : self.aws._lambda.runtime,
                'Role' : self.aws.iam.role,
                'Handler' :  self.aws._lambda.handler,
                'Code' : self.aws._lambda.code,
                'Environment' : self.aws._lambda.environment,
                'Description': self.aws._lambda.description,
                'Timeout':  self.aws._lambda.time,
                'MemorySize': self.aws._lambda.memory,
                'Tags': self.aws.tags,
                'Layers': self.aws._lambda.layers }    
    
    @excp.exception(logger)
    def create_function(self):
        self._manage_supervisor_layer()
        self._set_environment_variables()
        self._set_function_code()
        creation_args = self._get_creations_args()
        response = self.client.create_function(**creation_args)
        if response and utils.is_value_in_dict("FunctionArn", response):
            self.aws._lambda.arn = response['FunctionArn']
        return response

    def _manage_supervisor_layer(self):
        if not self.layers.is_supervisor_layer_created():
            self.layers.create_supervisor_layer()
        else:
            logger.info("Using existent 'faas-supervisor' layer")
        self.aws._lambda.layers = self.layers.get_layers_arn()

    def _add_lambda_environment_variable(self, key, value):
        if key and value:
            self.aws._lambda.environment['Variables'][key] = value

    def _set_environment_variables(self):
        # Add required variables
        self._set_required_environment_variables()
        # Add explicitly user defined variables
        if hasattr(self.aws._lambda, "environment_variables"):
            if type(self.aws._lambda.environment_variables) is dict:
                for key, val in self.aws._lambda.environment_variables.items():
                    # Add an specific prefix to be able to find the variables defined by the user
                    self._add_lambda_environment_variable('CONT_VAR_{0}'.format(key), val)                    
            else:
                for env_var in self.aws._lambda.environment_variables:
                    key_val = env_var.split("=")
                    # Add an specific prefix to be able to find the variables defined by the user
                    self._add_lambda_environment_variable('CONT_VAR_{0}'.format(key_val[0]), key_val[1])
        
    def _set_required_environment_variables(self):
        self._add_lambda_environment_variable('SUPERVISOR_TYPE', 'LAMBDA')
        self._add_lambda_environment_variable('TIMEOUT_THRESHOLD', str(self.aws._lambda.timeout_threshold))
        self._add_lambda_environment_variable('LOG_LEVEL', self.aws._lambda.log_level)
        self._add_udocker_variables()
        self._add_execution_mode()
        self._add_s3_environment_vars()
        if hasattr(self.aws._lambda, "image"):
            self._add_lambda_environment_variable('IMAGE_ID', self.aws._lambda.image)
        if hasattr(self.aws, "api_gateway"):
            self._add_lambda_environment_variable('API_GATEWAY_ID', self.aws.api_gateway.id)        

    def _add_udocker_variables(self):
        self._add_lambda_environment_variable('UDOCKER_EXEC', "/opt/udocker/udocker.py")
        self._add_lambda_environment_variable('UDOCKER_DIR', "/tmp/shared/udocker")
        self._add_lambda_environment_variable('UDOCKER_LIB', "/opt/udocker/lib/")
        self._add_lambda_environment_variable('UDOCKER_BIN', "/opt/udocker/bin/")

    def _add_execution_mode(self):
        self._add_lambda_environment_variable('EXECUTION_MODE',  self.aws.execution_mode)
        if (self.aws.execution_mode == 'lambda-batch' or self.aws.execution_mode == 'batch'):
            self._add_lambda_environment_variable('BATCH_SUPERVISOR_IMG',  self.aws.batch.supervisor_image)        

    def _add_s3_environment_vars(self):
        if hasattr(self.aws, "s3"):
            provider_id = random.randint(1,1000001)
            
            if hasattr(self.aws.s3, "input_bucket"):
                self._add_lambda_environment_variable('STORAGE_PATH_INPUT_{}'.format(provider_id), self.aws.s3.storage_path_input)
            
            if hasattr(self.aws.s3, "output_bucket"):
                self._add_lambda_environment_variable('STORAGE_PATH_OUTPUT_{}'.format(provider_id), self.aws.s3.storage_path_output)
            else:
                self._add_lambda_environment_variable('STORAGE_PATH_OUTPUT_{}'.format(provider_id), self.aws.s3.storage_path_input)
            self._add_lambda_environment_variable('STORAGE_AUTH_S3_{}_USER'.format(provider_id), "scar")
        
    @excp.exception(logger)
    def _set_function_code(self):
        # Zip all the files and folders needed
        FunctionPackager(self.aws).create_zip()
        if hasattr(self.aws, "s3") and hasattr(self.aws.s3, 'deployment_bucket'):
            self._upload_to_S3()
            self.aws._lambda.code = {"S3Bucket": self.aws.s3.deployment_bucket, "S3Key" : self.aws.s3.file_key}
        else:
            self.aws._lambda.code = {"ZipFile": utils.read_file(self.aws._lambda.zip_file_path, mode="rb")}
        
    def _upload_to_S3(self):
        self.aws.s3.input_bucket = self.aws.s3.deployment_bucket
        self.aws.s3.file_key = 'lambda/{0}.zip'.format(self.aws._lambda.name)
        self.s3.upload_file(file_path=self.aws._lambda.zip_file_path, file_key=self.aws.s3.file_key)
        
    def delete_function(self):
        return self.client.delete_function(self.aws._lambda.name)
    
    def link_function_and_input_bucket(self):
        kwargs = {'FunctionName' : self.aws._lambda.name,
                  'Principal' : "s3.amazonaws.com",
                  'SourceArn' : 'arn:aws:s3:::{0}'.format(self.aws.s3.input_bucket)}
        self.client.add_invocation_permission(**kwargs)

    def preheat_function(self):
        logger.info("Preheating function")
        self._set_request_response_call_parameters()
        return self.launch_lambda_instance()

    def _launch_async_event(self, s3_event):
        self.set_asynchronous_call_parameters()
        return self._launch_s3_event(s3_event)        
   
    def launch_request_response_event(self, s3_event):
        self._set_request_response_call_parameters()
        return self._launch_s3_event(s3_event)            
               
    def _launch_s3_event(self, s3_event):
        self.aws._lambda.payload = s3_event
        logger.info("Sending event for file '{0}'".format(s3_event['Records'][0]['s3']['object']['key']))
        return self.launch_lambda_instance()

    def process_asynchronous_lambda_invocations(self, s3_event_list):
        if (len(s3_event_list) > MAX_CONCURRENT_INVOCATIONS):
            s3_file_chunk_list = utils.divide_list_in_chunks(s3_event_list, MAX_CONCURRENT_INVOCATIONS)
            for s3_file_chunk in s3_file_chunk_list:
                self._launch_concurrent_lambda_invocations(s3_file_chunk)
        else:
            self._launch_concurrent_lambda_invocations(s3_event_list)

    def _launch_concurrent_lambda_invocations(self, s3_event_list):
        pool = ThreadPool(processes=len(s3_event_list))
        pool.map(lambda s3_event: self._launch_async_event(s3_event), s3_event_list)
        pool.close()

    def launch_lambda_instance(self):
        response = self._invoke_lambda_function()
        response_args = {'Response' : response,
                         'FunctionName' : self.aws._lambda.name,
                         'OutputType' : self.aws.output,
                         'IsAsynchronous' : self.aws._lambda.asynchronous}
        response_parser.parse_invocation_response(**response_args)

    def _get_invocation_payload(self):
        # Default payload empty
        payload = {}
        # Check for defined run script
        if hasattr(self.aws._lambda, "run_script"):
            script_path = self.aws._lambda.run_script
            if hasattr(self.aws, "config_path"):
                script_path = utils.join_paths(self.aws.config_path, script_path) 
            # We first code to base64 in bytes and then decode those bytes to allow the json lib to parse the data
            # https://stackoverflow.com/questions/37225035/serialize-in-json-a-base64-encoded-data#37239382
            payload = { "script" : utils.utf8_to_base64_string(utils.read_file(script_path, 'rb')) }
        # Check for defined commands
        # This overrides any other function payload
        if hasattr(self.aws._lambda, "c_args"):
            payload = { "cmd_args" : json.dumps(self.aws._lambda.c_args) }
        return json.dumps(payload)

    def _invoke_lambda_function(self):
        invoke_args = {'FunctionName' :  self.aws._lambda.name,
                       'InvocationType' :  self.aws._lambda.invocation_type,
                       'LogType' :  self.aws._lambda.log_type,
                       'Payload' : self._get_invocation_payload() }  
        return self.client.invoke_function(**invoke_args)

    def set_asynchronous_call_parameters(self):
        self.aws._lambda.update_properties(self.asynchronous_call_parameters)
        
    def _set_request_response_call_parameters(self):
        self.aws._lambda.update_properties(self.request_response_call_parameters)

    def _update_environment_variables(self, function_info, update_args):
        # To update the environment variables we need to retrieve the 
        # variables defined in lambda and update them with the new values
        env_vars = self.aws._lambda.environment
        if hasattr(self.aws._lambda, "environment_variables"):
            for env_var in self.aws._lambda.environment_variables:
                key_val = env_var.split("=")
                # Add an specific prefix to be able to find the variables defined by the user
                env_vars['Variables']['CONT_VAR_{0}'.format(key_val[0])] = key_val[1]
        if hasattr(self.aws._lambda, "timeout_threshold"):
            env_vars['Variables']['TIMEOUT_THRESHOLD'] = str(self.aws._lambda.timeout_threshold)
        if hasattr(self.aws._lambda, "log_level"):
            env_vars['Variables']['LOG_LEVEL'] = self.aws._lambda.log_level
        function_info['Environment']['Variables'].update(env_vars['Variables'])
        update_args['Environment'] = function_info['Environment']        
        
    def _update_supervisor_layer(self, function_info, update_args):
        if hasattr(self.aws._lambda, "supervisor_layer"):
            # Set supervisor layer Arn
            function_layers = [self.layers.get_latest_supervisor_layer_arn()]
            # Add the rest of layers (if exist)
            if 'Layers' in function_info:
                function_layers.extend([layer for layer in function_info['Layers'] if self.layers.layer_name not in layer['Arn']])
            update_args['Layers'] = function_layers        
        
    def update_function_configuration(self, function_info=None):
        if not function_info:
            function_info = self.get_function_info()
        update_args = {'FunctionName' : function_info['FunctionName'] }
#         if hasattr(self.aws._lambda, "memory"):
#             update_args['MemorySize'] = self.aws._lambda.memory
#         else:
#             update_args['MemorySize'] = function_info['MemorySize']
#         if hasattr(self.aws._lambda, "time"):
#             update_args['Timeout'] = self.aws._lambda.time
#         else:
#             update_args['Timeout'] = function_info['Timeout']
        self._update_environment_variables(function_info, update_args)
        self._update_supervisor_layer(function_info, update_args)
        self.client.update_function_configuration(**update_args)
        logger.info("Function '{}' updated successfully.".format(function_info['FunctionName']))

    def _get_function_environment_variables(self):
        return self.get_function_info()['Environment']

    def get_all_functions(self, arn_list):
        try:
            return [self.client.get_function_info(function_arn) for function_arn in arn_list]
        except ClientError as ce:
            print ("Error getting function info by arn: {}".format(ce))
    
    def get_function_info(self):
        return self.client.get_function_info(self.aws._lambda.name)
    
    @excp.exception(logger)
    def find_function(self, function_name_or_arn=None):
        try:
            # If this call works the function exists
            name_arn = function_name_or_arn if function_name_or_arn else self.aws._lambda.name
            self.client.get_function_info(name_arn)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:   
                raise
    
    def add_invocation_permission_from_api_gateway(self):
        kwargs = {'FunctionName' : self.aws._lambda.name,
                  'Principal' : 'apigateway.amazonaws.com',
                  'SourceArn' : 'arn:aws:execute-api:{0}:{1}:{2}/*'.format(self.aws.region,
                                                                           self.aws.account_id,
                                                                           self.aws.api_gateway.id)}
        # Add Testing permission
        self.client.add_invocation_permission(**kwargs)
        # Add Invocation permission
        kwargs['SourceArn'] = 'arn:aws:execute-api:{0}:{1}:{2}/scar/ANY'.format(self.aws.region,
                                                                                self.aws.account_id,
                                                                                self.aws.api_gateway.id)
        self.client.add_invocation_permission(**kwargs)

    def get_api_gateway_id(self):
        env_vars = self._get_function_environment_variables()
        return env_vars['Variables']['API_GATEWAY_ID'] if utils.is_value_in_dict('API_GATEWAY_ID', env_vars['Variables']) else ''
        
    def _get_api_gateway_url(self):
        api_id = self.get_api_gateway_id()
        if not api_id:
            raise excp.ApiEndpointNotFoundError(self.aws._lambda.name)
        return 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(api_id, self.aws.region)
        
    def call_http_endpoint(self):
        invoke_args = {'headers' : {'X-Amz-Invocation-Type':'Event'} if self.is_asynchronous() else {}}
        if hasattr(self.aws, "api_gateway"):
            self._set_api_gateway_props(invoke_args)
        return request.call_http_endpoint(self._get_api_gateway_url(), **invoke_args)        
        
    def _set_api_gateway_props(self, invoke_args):
        if hasattr(self.aws.api_gateway, "data_binary"):
            invoke_args['data'] = self._get_b64encoded_binary_data(self.aws.api_gateway.data_binary)
            invoke_args['headers'] = {'Content-Type': 'application/octet-stream'}
        if hasattr(self.aws.api_gateway, "parameters"):
            invoke_args['params'] = self._parse_http_parameters(self.aws.api_gateway.parameters)
        if hasattr(self.aws.api_gateway, "json_data"):
            invoke_args['data'] = self._parse_http_parameters(self.aws.api_gateway.json_data)
            invoke_args['headers'] = {'Content-Type': 'application/json'}

    def _parse_http_parameters(self, parameters):
        return parameters if type(parameters) is dict else json.loads(parameters)

    @excp.exception(logger)
    def _get_b64encoded_binary_data(self, data_path):
        if data_path:
            AWSValidator.validate_http_payload_size(data_path, self.is_asynchronous())
            with open(data_path, 'rb') as data_file:
                return base64.b64encode(data_file.read())                      
    

