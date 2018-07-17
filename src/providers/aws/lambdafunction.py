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

from botocore.exceptions import ClientError
from multiprocessing.pool import ThreadPool
from src.providers.aws.botoclientfactory import GenericClient
from src.providers.aws.functioncode import FunctionPackageCreator
from src.providers.aws.s3 import S3
import base64
import json
import src.exceptions as excp
import src.http.request as request
import src.logger as logger
import src.providers.aws.response as response_parser
import src.utils as utils

MAX_CONCURRENT_INVOCATIONS = 1000
MB = 1024*1024
KB = 1024
MAX_POST_BODY_SIZE = MB*6
MAX_POST_BODY_SIZE_ASYNC = KB*95

class Lambda(GenericClient):
    
    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.call_type = aws_properties['call_type']
        self.properties = aws_properties['lambda']
        self.properties['environment'] = {'Variables' : {}}
        self.properties['zip_file_path'] = utils.join_paths(utils.get_temp_dir(), 'function.zip')
        self.properties['invocation_type'] = 'RequestResponse'
        self.properties['log_type'] = 'Tail'
        if 'name' in self.properties:
            self.properties['handler'] = "{0}.lambda_handler".format(self.properties['name'])
        if 'asynchronous' not in self.properties:
            self.properties['asynchronous'] = False         

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
                }    
    
    @excp.exception(logger)
    def create_function(self):
        self.set_environment_variables()
        self.set_function_code()           
        creation_args = self.get_creations_args()
        response = self.client.create_function(**creation_args)
        if response and 'FunctionArn' in response:
            self.properties["function_arn"] = response['FunctionArn']
        return response
        
    def set_environment_variables(self):
        # Add required variables
        self.set_required_environment_variables()
        # Add explicitly user defined variables
        if 'environment_variables' in self.properties:
            for env_var in self.properties['environment_variables']:
                parsed_env_var = env_var.split("=")
                # Add an specific prefix to be able to find the variables defined by the user
                key = 'CONT_VAR_' + parsed_env_var[0]
                self.add_lambda_environment_variable(key, parsed_env_var[1])
        
    def set_required_environment_variables(self):
        self.add_lambda_environment_variable('TIMEOUT_THRESHOLD', str(self.properties['timeout_threshold']))
        self.add_lambda_environment_variable('LOG_LEVEL', self.properties['log_level'])        
        self.add_lambda_environment_variable('IMAGE_ID', self.properties['image'])
        if 's3' in self.aws_properties:
            s3_props = self.aws_properties['s3']
            if 'input_bucket' in s3_props:
                self.add_lambda_environment_variable('INPUT_BUCKET', s3_props['input_bucket'])
            if 'output_bucket' in s3_props:
                self.add_lambda_environment_variable('OUTPUT_BUCKET', s3_props['output_bucket'])
            if 'output_folder' in s3_props:
                self.add_lambda_environment_variable('OUTPUT_FOLDER', s3_props['output_folder'])
        if 'api_gateway' in self.aws_properties:
            self.add_lambda_environment_variable('API_GATEWAY_ID', self.aws_properties['api_gateway']['id'])                           

    def add_lambda_environment_variable(self, key, value):
        if key and value:
            self.properties['environment']['Variables'][key] = value         
    
    @excp.exception(logger)
    def upload_function_code_to_s3(self):
        self.aws_properties['s3']['input_bucket'] = self.properties['DeploymentBucket']
        S3(self.aws_properties).upload_file(file_path=self.properties['ZipFilePath'], file_key=self.properties['FileKey'])
    
    def set_function_code(self):
        package_props = self.get_function_payload_props()
        # Zip all the files and folders needed
        FunctionPackageCreator(package_props).prepare_lambda_code()
        if 'DeploymentBucket' in package_props:
            self.upload_function_code_to_s3()
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
        
#     def create_function_name(self, image_id_or_path):
#         parsed_id_or_path = image_id_or_path.replace('/', ',,,').replace(':', ',,,').replace('.', ',,,').split(',,,')
#         name = "scar-{0}".format('-'.join(parsed_id_or_path))
#         i = 1
#         while self.find_function(name):
#             name = "scar-{0}-{1}".format('-'.join(parsed_id_or_path), str(i))
#             i += 1
#         return name    
#     
#     @excp.exception(logger)
#     def check_function_name(self, func_name=None):
#         call_type = self.get_property("call_type")
#         if func_name:
#             function_name = func_name
#         else:
#             function_name = self.get_property("name")
#         function_found = self.find_function(function_name)
#         error_msg = None
#         if function_found and (call_type == CallType.INIT):
#             error_msg = "Function name '{0}' already used.".format(function_name)
#             raise excp.FunctionCreationError(function_name=function_name, error_msg=error_msg)
#         elif (not function_found) and ((call_type == CallType.RM) or 
#                                        (call_type == CallType.RUN) or 
#                                        (call_type == CallType.INVOKE)):
#             error_msg = "Function '{0}' doesn't exist.".format(function_name)
#             raise excp.FunctionNotFoundError(function_name=function_name, error_msg=error_msg)
#         if error_msg:
#             logger.error(error_msg)             
    
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
            file_content = utils.read_file(self.properties['run_script'], 'rb')
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

    def is_asynchronous(self):
        return self.get_property('asynchronous')
 
    def set_asynchronous_call_parameters(self):
        self.properties['invocation_type'] = "Event"
        self.properties['log_type'] = "None"
        self.properties['asynchronous'] = "True"
        
    def set_request_response_call_parameters(self):
        self.properties['invocation_type'] = "RequestResponse"
        self.properties['log_type'] = "Tail"
        self.properties['asynchronous'] = "False"        
        
    def get_argument_value(self, args, attr):
        if attr in args.__dict__.keys():
            return args.__dict__[attr]

    def update_function_attributes(self):
        update_args = {'FunctionName' : self.get_property("name") }
        self.set_property_if_has_value(update_args, 'MemorySize', "memory")
        self.set_property_if_has_value(update_args, 'Timeout', "time")
        # To update the environment variables we need to retrieve the 
        # variables defined in lambda and update them with the new values
        env_vars = self.get_property("environment")
        if self.get_property('timeout_threshold'):
            env_vars['Variables']['TIMEOUT_THRESHOLD'] = str(self.get_property('timeout_threshold'))
        if self.get_property('log_level'):
            env_vars['Variables']['LOG_LEVEL'] = self.get_property('log_level')            
        defined_lambda_env_variables = self.client.get_function_environment_variables(self.get_property("name"))
        defined_lambda_env_variables['Variables'].update(env_vars['Variables'])
        update_args['Environment'] = defined_lambda_env_variables
        
        self.client.update_function(**update_args)

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
        env_vars = self.client.get_function_environment_variables(self.properties['name'])
        if ('API_GATEWAY_ID' in env_vars['Variables']):
            return env_vars['Variables']['API_GATEWAY_ID']
        
    def get_api_gateway_url(self):
        api_id = self.get_api_gateway_id()
        if not api_id:
            raise excp.ApiEndpointNotFoundError(self.properties['name'])
        return 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(api_id, self.aws_properties["region"])        
        
    def get_http_invocation_headers(self):
        if "asynchronous" in self.aws_properties and self.aws_properties['asynchronous']:
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
                invoke_args['parameters'] = self.parse_http_parameters(api_props['parameters'])
        return request.invoke_http_endpoint(self.get_api_gateway_url(), **invoke_args)
        
    @excp.exception(logger)        
    def check_file_size(self, file_path):
        file_size = utils.get_file_size(file_path)
        if file_size > MAX_POST_BODY_SIZE:
            filesize = '{0:.2f}MB'.format(file_size/MB)
            maxsize = '{0:.2f}MB'.format(MAX_POST_BODY_SIZE_ASYNC/MB)            
            raise excp.InvocationPayloadError(file_size= filesize, max_size=maxsize)
        elif "asynchronous" in self.aws_properties and self.aws_properties['asynchronous'] and file_size > MAX_POST_BODY_SIZE_ASYNC:
            filesize = '{0:.2f}KB'.format(file_size/KB)
            maxsize = '{0:.2f}KB'.format(MAX_POST_BODY_SIZE_ASYNC/KB)
            raise excp.InvocationPayloadError(file_size=filesize, max_size=maxsize)
            
