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
from scar.providers.aws.validators import AWSValidator
import base64
import json
import scar.exceptions as excp
import scar.http.request as request
import scar.logger as logger
import scar.providers.aws.response as response_parser
import scar.utils as utils

MAX_CONCURRENT_INVOCATIONS = 1000

class Lambda(GenericClient):
    
    asynchronous_call_parameters = {"invocation_type" : "Event", "log_type" : "None", "asynchronous" : "True"}
    request_response_call_parameters = {"invocation_type" : "RequestResponse", "log_type" : "Tail", "asynchronous" : "False"}    
    
    @utils.lazy_property
    def layers(self):
        layers = LambdaLayers(self.client)
        return layers    
    
    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.properties = aws_properties['lambda']
        self._set_property("environment", {'Variables' : {}})
        self._set_property("zip_file_path", utils.join_paths(utils.get_tmp_dir(), 'function.zip'))
        if self._has_property("name"):
            self._set_property("handler", "{0}.lambda_handler".format(self._get_property("name")))
        self._set_property("invocation_type", "RequestResponse")
        self._set_property("log_type", "Tail")
        if not self._has_property("asynchronous"):
            self._set_property("asynchronous", False)
        self._set_property("layers", [])

    def _has_property(self, prop):
        return utils.is_value_in_dict(prop, self.properties)
        
    def _get_property(self, prop):
        return self.properties[prop]
    
    def _set_property(self, prop, val):
        self.properties[prop] = val
        
    def is_asynchronous(self):
        return self._has_property("asynchronous")        

    def get_creations_args(self):
        return {'FunctionName' : self._get_property("name"),
                'Runtime' : self._get_property("runtime"),
                'Role' : self.aws_properties['iam']['role'],
                'Handler' :  self._get_property("handler"),
                'Code' : self._get_property("code"),
                'Environment' : self._get_property("environment"),
                'Description': self._get_property("description"),
                'Timeout': self._get_property("time"),
                'MemorySize': self._get_property("memory"),
                'Tags': self.aws_properties['tags'],
                'Layers': self._get_property("layers"),
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
        else:
            logger.info("Using existent 'faas-supervisor' layer")
        self.properties['layers'] = self.layers.get_layers_arn()

    def set_environment_variables(self):
        # Add required variables
        self.set_required_environment_variables()
        # Add explicitly user defined variables
        if self._has_property("environment_variables"):
            env_vars = self._get_property("environment_variables")
            if type(env_vars) is dict:
                for key, val in env_vars.items():
                    # Add an specific prefix to be able to find the variables defined by the user
                    self.add_lambda_environment_variable('CONT_VAR_{0}'.format(key), val)                    
            else:
                for env_var in env_vars:
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
        if utils.is_value_in_dict('image', self.properties):     
            self.add_lambda_environment_variable('IMAGE_ID', self.properties['image'])
        self.add_s3_environment_vars()
        if 'api_gateway' in self.aws_properties:
            self.add_lambda_environment_variable('API_GATEWAY_ID', self.aws_properties['api_gateway']['id'])

    def add_s3_environment_vars(self):
        if utils.is_value_in_dict('s3', self.aws_properties):
            s3_props = self.aws_properties['s3']
            if utils.is_value_in_dict('input_bucket', s3_props):
                self.add_lambda_environment_variable('INPUT_BUCKET', s3_props['input_bucket'])
            if utils.is_value_in_dict('output_bucket', s3_props):
                self.add_lambda_environment_variable('OUTPUT_BUCKET', s3_props['output_bucket'])
            if utils.is_value_in_dict('output_folder', s3_props):
                self.add_lambda_environment_variable('OUTPUT_FOLDER', s3_props['output_folder'])        
        

    def add_lambda_environment_variable(self, key, value):
        if key and value:
            self.properties['environment']['Variables'][key] = value
    
    @excp.exception(logger)
    def set_function_code(self):
        package_props = self.get_function_payload_props()
        # Zip all the files and folders needed
        FunctionPackageCreator(package_props).prepare_lambda_code()
        self._set_property("code", {"ZipFile": utils.read_file(self.properties['zip_file_path'], mode="rb")})
        if 'DeploymentBucket' in package_props:
            self.aws_properties['s3']['input_bucket'] = package_props['DeploymentBucket']
            S3(self.aws_properties).upload_file(file_path=package_props['ZipFilePath'], file_key=package_props['FileKey'])
            self._set_property("code", {"S3Bucket": package_props['DeploymentBucket'], "S3Key" : package_props['FileKey']})
        
    def _set_init_script_property(self, package_args):
        if self._has_property("init_script"):
            package_args['Script'] = self._get_property("init_script")
            if 'config_path' in self.aws_properties:
                package_args['Script'] = utils.join_paths(self.aws_properties['config_path'], self._get_property("init_script"))
    
    def _set_extra_payload_property(self, package_args):
        if self._has_property("extra_payload"):
            package_args['ExtraPayload'] = self._get_property("extra_payload")
               
    def _set_image_id_property(self, package_args):
        if self._has_property("image_id"):
            package_args['ImageId'] = self._get_property("image_id")
                    
    def _set_image_file_property(self, package_args):
        if self._has_property("image_file"):
            package_args['ImageFile'] = self._get_property("image_file")
    
    def _set_s3_properties(self, package_args):
        if 's3' in self.aws_properties:
            if 'deployment_bucket' in self.aws_properties['s3']:
                package_args['DeploymentBucket'] = self.aws_properties['s3']['deployment_bucket']                        
            if 'DeploymentBucket' in package_args:
                package_args['FileKey'] = 'lambda/{0}.zip'.format(self.properties['name'])        
        
    def get_function_payload_props(self):
        package_args = {'FunctionName' : self._get_property("name"),
                        'EnvironmentVariables' : self._get_property("environment")['Variables'],
                        'ZipFilePath' : self._get_property("zip_file_path")}
        self._set_init_script_property(package_args)
        self._set_extra_payload_property(package_args)
        self._set_image_id_property(package_args)
        self._set_image_file_property(package_args)
        self._set_s3_properties(package_args)
        return package_args
    
    def delete_function(self):
        return self.client.delete_function(self._get_property("name"))
    
    def link_function_and_input_bucket(self):
        kwargs = {'FunctionName' : self._get_property("name"),
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
        self._set_property("payload", s3_event)
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
                         'FunctionName' : self._get_property("name"),
                         'OutputType' : self.aws_properties['output'],
                         'IsAsynchronous' : self._get_property("asynchronous")}
        response_parser.parse_invocation_response(**response_args)

    def get_payload(self):
        # Default payload
        payload = {}
        if self._has_property("run_script"):
            script_path = self._get_property("run_script")
            if 'config_path' in self.aws_properties:
                script_path = utils.join_paths(self.aws_properties['config_path'], self._get_property("run_script")) 
            # We first code to base64 in bytes and then decode those bytes to allow the json lib to parse the data
            # https://stackoverflow.com/questions/37225035/serialize-in-json-a-base64-encoded-data#37239382
            payload = { "script" : utils.utf8_to_base64_string(utils.read_file(script_path, 'rb')) }
         
        if self._has_property("c_args"):
            payload = { "cmd_args" : json.dumps(self._get_property("c_args")) }

        return json.dumps(payload)

    def invoke_lambda_function(self):
        invoke_args = {'FunctionName' :  self._get_property('name'),
                       'InvocationType' :  self._get_property('invocation_type'),
                       'LogType' :  self._get_property('log_type'),
                       'Payload' : self.get_payload() }  
        return self.client.invoke_function(**invoke_args)

    def set_asynchronous_call_parameters(self):
        self.properties.update(self.asynchronous_call_parameters)
        
    def set_request_response_call_parameters(self):
        self.properties.update(self.request_response_call_parameters)

    def _update_environment_variables(self, function_info, update_args):
        # To update the environment variables we need to retrieve the 
        # variables defined in lambda and update them with the new values
        env_vars = self._get_property("environment")
        if self._has_property("environment_variables"):
            for env_var in self._get_property("environment_variables"):
                key_val = env_var.split("=")
                # Add an specific prefix to be able to find the variables defined by the user
                env_vars['Variables']['CONT_VAR_{0}'.format(key_val[0])] = key_val[1]
        if self._has_property("timeout_threshold"):
            env_vars['Variables']['TIMEOUT_THRESHOLD'] = str(self._get_property('timeout_threshold'))
        if self._has_property("log_level"):
            env_vars['Variables']['LOG_LEVEL'] = self._get_property('log_level')
        function_info['Environment']['Variables'].update(env_vars['Variables'])
        update_args['Environment'] = function_info['Environment']        
        
    def _update_supervisor_layer(self, function_info, update_args):
        if self._has_property("supervisor_layer"):
            # Set supervisor layer Arn
            function_layers = [self.layers.get_latest_supervisor_layer_arn()]
            # Add the rest of layers (if exist)
            if 'Layers' in function_info:
                function_layers.extend([layer for layer in function_info['Layers'] if self.layers.layer_name not in layer['Arn']])
            update_args['Layers'] = function_layers        
        
    def update_function_attributes(self, function_info=None):
        if not function_info:
            function_info = self.get_function_info()
        update_args = {'FunctionName' : function_info['FunctionName'] }
        if self._has_property("memory"):
            update_args['MemorySize'] = self._get_property('memory')
        if self._has_property("time"):
            update_args['Timeout'] = self._get_property('time')
        self._update_environment_variables(function_info, update_args)
        self._update_supervisor_layer(function_info, update_args)
        self.client.update_function(**update_args)
        logger.info("Function '{}' updated successfully.".format(function_info['FunctionName']))

    def get_function_environment_variables(self):
        return self.get_function_info()['Environment']

    def get_all_functions(self, arn_list):
        try:
            return [self.client.get_function_info(function_arn) for function_arn in arn_list]
        except ClientError as ce:
            print ("Error getting function info by arn: %s" % ce)
    
    def get_function_info(self):
        return self.client.get_function_info(self._get_property('name'))
    
    @excp.exception(logger)
    def find_function(self, function_name_or_arn=None):
        try:
            # If this call works the function exists
            name_arn = function_name_or_arn if function_name_or_arn else self._get_property('name')
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
        kwargs = {'FunctionName' : self._get_property('name'),
                  'Principal' : 'apigateway.amazonaws.com',
                  'SourceArn' : 'arn:aws:execute-api:{0}:{1}:{2}/*'.format(aws_region, aws_acc_id, api_gateway_id)}
        # Add Testing permission
        self.client.add_invocation_permission(**kwargs)
        # Add Invocation permission
        kwargs['SourceArn'] = 'arn:aws:execute-api:{0}:{1}:{2}/scar/ANY'.format(aws_region, aws_acc_id, api_gateway_id)
        self.client.add_invocation_permission(**kwargs)

    def get_api_gateway_id(self):
        env_vars = self.get_function_environment_variables()
        return env_vars['Variables']['API_GATEWAY_ID'] if utils.is_value_in_dict('API_GATEWAY_ID', env_vars['Variables']) else ''
        
    def get_api_gateway_url(self):
        api_id = self.get_api_gateway_id()
        if not api_id:
            raise excp.ApiEndpointNotFoundError(self._get_property('name'))
        return 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(api_id, self.aws_properties["region"])
        
    def parse_http_parameters(self, parameters):
        return parameters if type(parameters) is dict else json.loads(parameters)

    @excp.exception(logger)
    def get_b64encoded_binary_data(self, data_path):
        if data_path:
            AWSValidator.validate_payload_size(data_path, self.is_asynchronous())
            with open(data_path, 'rb') as data_file:
                return base64.b64encode(data_file.read())
        
    def call_http_endpoint(self):
        invoke_args = {'headers' : {'X-Amz-Invocation-Type':'Event'} if self.is_asynchronous() else {}}
        if 'api_gateway' in self.aws_properties:
            api_props = self.aws_properties['api_gateway']
            if utils.is_value_in_dict('data_binary', api_props):
                invoke_args['data'] = self.get_b64encoded_binary_data(api_props['data_binary'])
            if utils.is_value_in_dict('parameters', api_props):
                invoke_args['params'] = self.parse_http_parameters(api_props['parameters'])
            if utils.is_value_in_dict('json_data', api_props):
                invoke_args['data'] = self.parse_http_parameters(api_props['json_data'])
                invoke_args['headers'] = {'Content-Type': 'application/json'}
        return request.call_http_endpoint(self.get_api_gateway_url(), **invoke_args)
