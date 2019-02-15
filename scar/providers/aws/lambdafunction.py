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
from scar.providers.aws.functioncode import FunctionPackageCreator
from scar.providers.aws.lambdalayers import LambdaLayers
from scar.providers.aws.s3 import S3
import base64
import json
import scar.exceptions as excp
import scar.http.request as request
import scar.logger as logger
import scar.providers.aws.response as response_parser
import scar.utils as utils

MAX_CONCURRENT_INVOCATIONS = 1000
MB = 1024*1024
KB = 1024
MAX_POST_BODY_SIZE = MB*6
MAX_POST_BODY_SIZE_ASYNC = KB*95

class Lambda(GenericClient):
    
    @utils.lazy_property
    def layers(self):
        layers = LambdaLayers(self.client)
        return layers    
    
    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.properties = aws_properties['lambda']
        self.properties['environment'] = {'Variables' : {}}
        self.properties['zip_file_path'] = utils.join_paths(utils.get_tmp_dir(), 'function.zip')
        self.properties['invocation_type'] = 'RequestResponse'
        self.properties['log_type'] = 'Tail'
        if 'name' in self.properties:
            self.properties['handler'] = "{0}.lambda_handler".format(self.properties['name'])
        if 'asynchronous' not in self.properties:
            self.properties['asynchronous'] = False
        self.properties['layers'] = []

    def get_creations_args(self):
        return {'FunctionName' : self.properties['name'],
                'Runtime' : self.properties['runtime'],
                'Role' : self.aws_properties['iam']['role'],
                'Handler' :  self.properties['handler'],
                'Code' : self.properties['code'],
                'Environment' : self.properties['environment'],
                'Description': self.properties['description'],
                'Timeout': self.properties['time'],
                'MemorySize': self.properties['memory'],
                'Tags': self.aws_properties['tags'],
                'Layers': self.properties['layers'],
                }    
    
    @excp.exception(logger)
    def create_function(self):
        self.manage_layers()
        self.set_environment_variables()
        self.set_function_code()
        creation_args = self.get_creations_args()
        response = self.client.create_function(**creation_args)
        if response and 'FunctionArn' in response:
            self.properties["function_arn"] = response['FunctionArn']
        return response

    def manage_layers(self):
        if not self.layers.is_supervisor_layer_created():
            self.layers.create_supervisor_layer()
        elif 'update_layer' in self.properties:
            self.layers.update_layer_and_functions()
        else:
            logger.info("Using existent 'faas-supervisor' layer")
        self.properties['layers'] = self.layers.get_layers_arn()

    def set_environment_variables(self):
        # Add required variables
        self.set_required_environment_variables()
        # Add explicitly user defined variables
        if 'environment_variables' in self.properties:
            if type(self.properties['environment_variables']) is dict:
                for key, val in self.properties['environment_variables'].items():
                    # Add an specific prefix to be able to find the variables defined by the user
                    self.add_lambda_environment_variable('CONT_VAR_{0}'.format(key), val)                    
            else:
                for env_var in self.properties['environment_variables']:
                    key_val = env_var.split("=")
                    # Add an specific prefix to be able to find the variables defined by the user
                    self.add_lambda_environment_variable('CONT_VAR_{0}'.format(key_val[0]), key_val[1])
        
    def set_required_environment_variables(self):
        self.add_lambda_environment_variable('SUPERVISOR_TYPE', 'LAMBDA')
        self.add_lambda_environment_variable('UDOCKER_EXEC', "/opt/udocker/udocker.py")
        self.add_lambda_environment_variable('UDOCKER_DIR', "/tmp/shared/udocker")
        self.add_lambda_environment_variable('UDOCKER_LIB', "/opt/udocker/lib/")
        self.add_lambda_environment_variable('UDOCKER_BIN', "/opt/udocker/bin/")
        
        self.add_lambda_environment_variable('TIMEOUT_THRESHOLD', str(self.properties['timeout_threshold']))
        self.add_lambda_environment_variable('LOG_LEVEL', self.properties['log_level'])
        self.add_lambda_environment_variable('EXECUTION_MODE',  self.aws_properties['execution_mode'])
        if (self.aws_properties['execution_mode']=='lambda-batch' or self.aws_properties['execution_mode']=='batch'):
            self.add_lambda_environment_variable('BATCH_SUPERVISOR_IMG',  'alpegon/scar-batch-io:devel')
        
        self.add_lambda_environment_variable('EXECUTION_MODE',  self.aws_properties['execution_mode'])
        if utils.is_value_in_dict(self.properties, 'image'):     
            self.add_lambda_environment_variable('IMAGE_ID', self.properties['image'])
        self.add_s3_environment_vars()
        if 'api_gateway' in self.aws_properties:
            self.add_lambda_environment_variable('API_GATEWAY_ID', self.aws_properties['api_gateway']['id'])

    def add_s3_environment_vars(self):
        if utils.is_value_in_dict(self.aws_properties, 's3'):
            s3_props = self.aws_properties['s3']
            if utils.is_value_in_dict(s3_props, 'input_bucket'):
                self.add_lambda_environment_variable('INPUT_BUCKET', s3_props['input_bucket'])
            if utils.is_value_in_dict(s3_props, 'output_bucket'):
                self.add_lambda_environment_variable('OUTPUT_BUCKET', s3_props['output_bucket'])
            if utils.is_value_in_dict(s3_props, 'output_folder'):
                self.add_lambda_environment_variable('OUTPUT_FOLDER', s3_props['output_folder'])        
        

    def add_lambda_environment_variable(self, key, value):
        if key and value:
            self.properties['environment']['Variables'][key] = value         
    
    @excp.exception(logger)
    def set_function_code(self):
        package_props = self.get_function_payload_props()
        # Zip all the files and folders needed
        FunctionPackageCreator(package_props).prepare_lambda_code()
        if 'DeploymentBucket' in package_props:
            self.aws_properties['s3']['input_bucket'] = package_props['DeploymentBucket']
            S3(self.aws_properties).upload_file(file_path=package_props['ZipFilePath'], file_key=package_props['FileKey'])
            self.properties['code'] = {"S3Bucket": package_props['DeploymentBucket'],
                                       "S3Key" : package_props['FileKey'],}
        else:
            self.properties['code'] = {"ZipFile": utils.read_file(self.properties['zip_file_path'], mode="rb")}        
        
    def get_function_payload_props(self):
        package_args = {'FunctionName' : self.properties['name'],
                        'EnvironmentVariables' : self.properties['environment']['Variables'],
                        'ZipFilePath' : self.properties['zip_file_path'],
                        }
        if 'init_script' in self.properties:
            if 'config_path' in self.aws_properties:
                package_args['Script'] = utils.join_paths(self.aws_properties['config_path'], self.properties['init_script'])
            else:
                package_args['Script'] = self.properties['init_script']
        if 'extra_payload' in self.properties:
            package_args['ExtraPayload'] = self.properties['extra_payload']
        if 'image_id' in self.properties:
            package_args['ImageId'] = self.properties['image_id']
        if 'image_file' in self.properties:
            package_args['ImageFile'] = self.properties['image_file']
        if 's3' in self.aws_properties:
            if 'deployment_bucket' in self.aws_properties['s3']:
                package_args['DeploymentBucket'] = self.aws_properties['s3']['deployment_bucket']                        
            if 'DeploymentBucket' in package_args:
                package_args['FileKey'] = 'lambda/{0}.zip'.format(self.properties['name'])        
        return package_args
    
    def delete_function(self):
        return self.client.delete_function(self.properties['name'])
    
    def link_function_and_input_bucket(self):
        kwargs = {'FunctionName' : self.properties['name'],
                  'Principal' : "s3.amazonaws.com",
                  'SourceArn' : 'arn:aws:s3:::{0}'.format(self.aws_properties['s3']['input_bucket'])}
        self.client.add_invocation_permission(**kwargs)

    def preheat_function(self):
        logger.info("Preheating function")
        self.set_request_response_call_parameters()
        return self.launch_lambda_instance()

    def launch_async_event(self, s3_event):
        self.set_asynchronous_call_parameters()
        return self.launch_s3_event(s3_event)        
   
    def launch_request_response_event(self, s3_event):
        self.set_request_response_call_parameters()
        return self.launch_s3_event(s3_event)            
               
    def launch_s3_event(self, s3_event):
        self.properties['payload'] = s3_event
        logger.info("Sending event for file '{0}'".format(s3_event['Records'][0]['s3']['object']['key']))
        return self.launch_lambda_instance()

    def process_asynchronous_lambda_invocations(self, s3_event_list):
        if (len(s3_event_list) > MAX_CONCURRENT_INVOCATIONS):
            s3_file_chunk_list = utils.divide_list_in_chunks(s3_event_list, MAX_CONCURRENT_INVOCATIONS)
            for s3_file_chunk in s3_file_chunk_list:
                self.launch_concurrent_lambda_invocations(s3_file_chunk)
        else:
            self.launch_concurrent_lambda_invocations(s3_event_list)

    def launch_concurrent_lambda_invocations(self, s3_event_list):
        pool = ThreadPool(processes=len(s3_event_list))
        pool.map(lambda s3_event: self.launch_async_event(s3_event), s3_event_list)
        pool.close()

    def launch_lambda_instance(self):
        response = self.invoke_lambda_function()
        response_args = {'Response' : response,
                         'FunctionName' : self.properties['name'],
                         'OutputType' : self.aws_properties['output'],
                         'IsAsynchronous' : self.properties['asynchronous']}
        response_parser.parse_invocation_response(**response_args)

    def get_payload(self):
        # Default payload
        payload = {}
        if 'run_script' in self.properties:
            if 'config_path' in self.aws_properties:
                script_path = utils.join_paths(self.aws_properties['config_path'], self.properties['run_script'])
            else:
                script_path = self.properties['run_script']
            file_content = utils.read_file(script_path, 'rb')
            # We first code to base64 in bytes and then decode those bytes to allow the json lib to parse the data
            # https://stackoverflow.com/questions/37225035/serialize-in-json-a-base64-encoded-data#37239382
            payload = { "script" : utils.utf8_to_base64_string(file_content) }
         
        if 'c_args' in self.properties:
            payload = { "cmd_args" : json.dumps(self.properties['c_args']) }

        return json.dumps(payload)

    def invoke_lambda_function(self):
        invoke_args = {'FunctionName' : self.properties['name'],
                       'InvocationType' : self.properties['invocation_type'],
                       'LogType' : self.properties['log_type'],
                       'Payload' : self.get_payload() }  
        return self.client.invoke_function(**invoke_args)

    def set_asynchronous_call_parameters(self):
        self.properties['invocation_type'] = "Event"
        self.properties['log_type'] = "None"
        self.properties['asynchronous'] = "True"
        
    def set_request_response_call_parameters(self):
        self.properties['invocation_type'] = "RequestResponse"
        self.properties['log_type'] = "Tail"
        self.properties['asynchronous'] = "False"        
        
    def update_function_attributes(self):
        update_args = {'FunctionName' : self.properties['name'] }
        if "memory" in self.properties and self.properties['memory']:
            update_args['MemorySize'] = self.properties['memory']
        if "time" in self.properties and self.properties['time']:
            update_args['Timeout'] = self.properties['time']            
        # To update the environment variables we need to retrieve the 
        # variables defined in lambda and update them with the new values
        env_vars = self.properties['environment']
        if "environment_variables" in self.properties:
            for env_var in self.properties['environment_variables']:
                key_val = env_var.split("=")
                # Add an specific prefix to be able to find the variables defined by the user
                env_vars['Variables']['CONT_VAR_{0}'.format(key_val[0])] = key_val[1]
        if "timeout_threshold" in self.properties and self.properties['timeout_threshold']:
            env_vars['Variables']['TIMEOUT_THRESHOLD'] = str(self.properties['timeout_threshold'])
        if "log_level" in self.properties and self.properties['log_level']:
            env_vars['Variables']['LOG_LEVEL'] = self.properties['log_level']            
        defined_lambda_env_variables = self.get_function_environment_variables()
        defined_lambda_env_variables['Variables'].update(env_vars['Variables'])
        update_args['Environment'] = defined_lambda_env_variables
        
        self.client.update_function(**update_args)
        logger.info("Function updated successfully.")

    def get_function_environment_variables(self):
        return self.get_function_info()['Environment']

    def get_all_functions(self, arn_list):
        function_info_list = []
        try:
            for function_arn in arn_list:
                function_info_list.append(self.client.get_function_info(function_arn))
        except ClientError as ce:
            print ("Error getting function info by arn: %s" % ce)
        return function_info_list
    
    def get_function_info(self):
        return self.client.get_function_info(self.properties['name'])
    
    @excp.exception(logger)
    def find_function(self, function_name_or_arn=None):
        try:
            # If this call works the function exists
            if function_name_or_arn:
                name_arn = function_name_or_arn
            else:
                name_arn = self.properties['name']
            self.client.get_function_info(name_arn)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:   
                raise
                
    def add_invocation_permission_from_api_gateway(self):
        api_gateway_id = self.aws_properties['api_gateway']['id']
        aws_acc_id = self.aws_properties['account_id']
        aws_region = self.aws_properties['region']
        kwargs = {'FunctionName' : self.properties['name'],
                  'Principal' : 'apigateway.amazonaws.com',
                  'SourceArn' : 'arn:aws:execute-api:{0}:{1}:{2}/*'.format(aws_region, aws_acc_id, api_gateway_id),
                  }
        # Testing permission
        self.client.add_invocation_permission(**kwargs)
        # Invocation permission
        kwargs['SourceArn'] = 'arn:aws:execute-api:{0}:{1}:{2}/scar/ANY'.format(aws_region, aws_acc_id, api_gateway_id)
        self.client.add_invocation_permission(**kwargs)

    def get_api_gateway_id(self):
        env_vars = self.get_function_environment_variables()
        if ('API_GATEWAY_ID' in env_vars['Variables']):
            return env_vars['Variables']['API_GATEWAY_ID']
        
    def get_api_gateway_url(self):
        api_id = self.get_api_gateway_id()
        if not api_id:
            raise excp.ApiEndpointNotFoundError(self.properties['name'])
        return 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(api_id, self.aws_properties["region"])
        
    def get_http_invocation_headers(self):
        if self.is_asynchronous():
            return {'X-Amz-Invocation-Type':'Event'}
        
    def parse_http_parameters(self, parameters):
        if type(parameters) is dict:
            return parameters
        return json.loads(parameters)

    def get_encoded_binary_data(self, data_path):
        if data_path:
            self.check_file_size(data_path)
            with open(data_path, 'rb') as f:
                data = f.read()
            return base64.b64encode(data)
        
    def invoke_http_endpoint(self):
        invoke_args = {'headers' : self.get_http_invocation_headers()}
        if 'api_gateway' in self.aws_properties:
            api_props = self.aws_properties['api_gateway']
            if 'data_binary' in api_props and api_props['data_binary']:
                invoke_args['data'] = self.get_encoded_binary_data(api_props['data_binary'])
            if 'parameters' in api_props and api_props['parameters']:
                invoke_args['params'] = self.parse_http_parameters(api_props['parameters'])
            if 'json_data' in api_props and api_props['json_data']:
                invoke_args['data'] = self.parse_http_parameters(api_props['json_data'])
                invoke_args['headers'] = {'Content-Type': 'application/json'}
        return request.invoke_http_endpoint(self.get_api_gateway_url(), **invoke_args)
        
    @excp.exception(logger)        
    def check_file_size(self, file_path):
        file_size = utils.get_file_size(file_path)
        if file_size > MAX_POST_BODY_SIZE:
            filesize = '{0:.2f}MB'.format(file_size/MB)
            maxsize = '{0:.2f}MB'.format(MAX_POST_BODY_SIZE_ASYNC/MB)            
            raise excp.InvocationPayloadError(file_size= filesize, max_size=maxsize)
        elif self.is_asynchronous() and file_size > MAX_POST_BODY_SIZE_ASYNC:
            filesize = '{0:.2f}KB'.format(file_size/KB)
            maxsize = '{0:.2f}KB'.format(MAX_POST_BODY_SIZE_ASYNC/KB)
            raise excp.InvocationPayloadError(file_size=filesize, max_size=maxsize)
    
    def is_asynchronous(self):
        return "asynchronous" in self.properties and self.properties['asynchronous']
