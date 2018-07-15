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
import json
import src.http.invoke as invoke
import src.logger as logger
from src.providers.aws.payload import FunctionPackageCreator
import src.providers.aws.response as response_parser
import src.utils as utils
import base64
from src.providers.aws.botoclientfactory import GenericClient
import src.exceptions as excp

MAX_CONCURRENT_INVOCATIONS = 1000
MAX_POST_BODY_SIZE = 1024*1024*6
MAX_POST_BODY_SIZE_ASYNC = 1024*95

class Lambda(GenericClient):
    
    s3_event = { "Records" : [ {"eventSource" : "aws:s3",
                 "s3" : {"bucket" : { "name" : "" },
                         "object" : { "key" : ""  } }
                }]}

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

#     def extra_thingies(self):
#         if ((call_type != CallType.LS) and (not self.delete_all()) and
#             (call_type != CallType.PUT) and (call_type != CallType.GET)):
#             if (call_type == CallType.INIT):
#                 if (not self.get_property("name")) or (self.get_property("name") == ""):
#                     func_name = "function"
#                     if self.get_property("image_id") != "":
#                         func_name = self.get_property("image_id")
#                     elif self.get_property("image_file") != "":
#                         func_name = self.get_property("image_file").split('.')[0]
#                     self.properties["name"] = self.create_function_name(func_name)
#             
#             self.check_function_name()
#             function_name = self.get_property("name")
#                 
#             self.set_environment_variables()
#             self.properties["handler"] = function_name + ".lambda_handler"
#             
#             if (call_type == CallType.INIT):   
#                 self.set_function_code()           
#                 
#             if (call_type == CallType.RUN):
#                 if self.get_argument_value(args, 'run_script'):
#                     file_content = utils.read_file(self.get_property("run_script"), 'rb')
#                     # We first code to base64 in bytes and then decode those bytes to allow json to work
#                     # https://stackoverflow.com/questions/37225035/serialize-in-json-a-base64-encoded-data#37239382
#                     parsed_script = utils.utf8_to_base64_string(file_content)
#                     self.set_property('payload', { "script" : parsed_script })
#                 
#                 if self.get_argument_value(args, 'c_args'):
#                     parsed_cont_args = json.dumps(self.get_property("c_args"))
#                     self.set_property('payload', { "cmd_args" : parsed_cont_args })        
    
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
        self.add_lambda_environment_variable('IMAGE_ID', self.properties['image_id'])
        if 's3' in self.aws_properties:
            s3_props = self.aws_properties['s3']
            if 'input_bucket' in s3_props:
                self.add_lambda_environment_variable('INPUT_BUCKET', s3_props['input_bucket'])
            if 'output_bucket' in s3_props:
                self.add_lambda_environment_variable('OUTPUT_BUCKET', s3_props['output_bucket'])
            if 'output_folder' in s3_props:
                self.add_lambda_environment_variable('OUTPUT_FOLDER', s3_props['output_folder'])                   

    def add_lambda_environment_variable(self, key, value):
        if key and value:
            self.properties['environment']['Variables'][key] = value         
        
    def set_function_code(self):
        package_props = self.get_function_payload_props()
        # Zip all the files and folders needed
        FunctionPackageCreator(package_props).prepare_lambda_payload()
        if 'DeploymentBucket' in package_props:
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

    def launch_async_event(self, s3_file):
        self.set_asynchronous_call_parameters()
        return self.launch_s3_event(s3_file)        
   
    def launch_request_response_event(self, s3_file):
        self.set_request_response_call_parameters()
        return self.launch_s3_event(s3_file)            
               
    def launch_s3_event(self, s3_file):
        self.set_s3_event_source(s3_file)
        self.set_property('payload', self.s3_event)
        logger.info("Sending event for file '%s'" % s3_file)
        return self.launch_lambda_instance()

    def process_asynchronous_lambda_invocations(self, s3_file_list):
        if (len(s3_file_list) > MAX_CONCURRENT_INVOCATIONS):
            s3_file_chunk_list = utils.divide_list_in_chunks(s3_file_list, MAX_CONCURRENT_INVOCATIONS)
            for s3_file_chunk in s3_file_chunk_list:
                self.launch_concurrent_lambda_invocations(s3_file_chunk)
        else:
            self.launch_concurrent_lambda_invocations(s3_file_list)

    def launch_concurrent_lambda_invocations(self, s3_file_list):
        pool = ThreadPool(processes=len(s3_file_list))
        pool.map(
            lambda s3_file: self.launch_async_event(s3_file), s3_file_list
        )
        pool.close()

    def launch_lambda_instance(self):
        response = self.invoke_lambda_function()
        response_args = {'Response' : response,
                         'FunctionName' : self.get_function_name(),
                         'OutputType' : self.get_property("output"),
                         'IsAsynchronous' : self.is_asynchronous()}
        response_parser.parse_invocation_response(**response_args)

    def invoke_lambda_function(self):
        invoke_args = {'FunctionName' : self.get_function_name(),
                       'InvocationType' : self.get_property("invocation_type"),
                       'LogType' : self.get_property("log_type"),
                       'Payload' : json.dumps(self.get_property("payload"))}    
        return self.client.invoke_function(**invoke_args)

    def is_asynchronous(self):
        return self.get_property('asynchronous')
 
    def set_asynchronous_call_parameters(self):
        self.set_property('invocation_type', "Event")
        self.set_property('log_type', 'None')
        self.set_property('asynchronous', 'True')
        
    def set_api_gateway_id(self, api_id):
        self.add_lambda_environment_variable('API_GATEWAY_ID', api_id)

    def set_request_response_call_parameters(self):
        self.set_property('invocation_type', "RequestResponse")
        self.set_property('log_type', "Tail")    
        self.set_property('asynchronous', 'False')    

    def set_s3_event_source(self, file_name):
        self.s3_event['Records'][0]['s3']['bucket']['name'] = self.get_property('input_bucket')
        self.s3_event['Records'][0]['s3']['object']['key'] = file_name
        
    def has_image_file(self):
        return utils.has_dict_prop_value(self.properties, 'image_file')
    
    def has_deployment_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'deployment_bucket')
 
    def has_input_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'input_bucket')
    
    def has_output_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'output_bucket')
    
    def has_output_folder(self):
        return utils.has_dict_prop_value(self.properties, 'output_folder')

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
        api_gateway_id = self.get_property('api_gateway_id')
        aws_acc_id = self.get_property('aws_acc_id')
        kwargs = {'FunctionName' : self.get_function_name(),
                  'Principal' : 'apigateway.amazonaws.com',
                  'SourceArn' : 'arn:aws:execute-api:us-east-1:{0}:{1}/*'.format(aws_acc_id, api_gateway_id)}
        # Testing permission
        self.client.add_invocation_permission(**kwargs)
        # Invocation permission
        kwargs['SourceArn'] = 'arn:aws:execute-api:us-east-1:{0}:{1}/scar/ANY'.format(aws_acc_id, api_gateway_id)
        self.client.add_invocation_permission(**kwargs)                              

    def get_api_gateway_id(self):
        env_vars = self.client.get_function_environment_variables(self.properties['name'])
        if ('API_GATEWAY_ID' in env_vars['Variables']):
            return env_vars['Variables']['API_GATEWAY_ID']
        
    def get_api_gateway_url(self, function_name):
        api_id = self.get_api_gateway_id(function_name)
        if api_id is None or api_id == "":
            error_msg = "Error retrieving API ID for lambda function {0}".format(function_name)
            logger.error(error_msg)
        return 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(api_id, self.get_property("region"))        
        
    def get_http_invocation_headers(self):
        asynch = self.get_property("asynchronous")
        if asynch:
            return {'X-Amz-Invocation-Type':'Event'}  
        
    def get_encoded_binary_data(self):
        data = self.get_property("data_binary")
        if data:
            self.check_file_size(data)                
            with open(data, 'rb') as f:
                data = f.read()
            return base64.b64encode(data)        
        
    def get_http_parameters(self):
        params = self.get_property("parameters")
        if params:
            if type(params) is dict:
                return params
            return json.loads(params)
        
    def invoke_function_http(self, function_name):
        function_url = self.get_api_gateway_url(function_name)
        headers = self.get_http_invocation_headers()
        params = self.get_http_parameters()
        data = self.get_encoded_binary_data()

        return invoke.invoke_function(function_url,
                               parameters=params,
                               data=data,
                               headers=headers)
        
    def check_file_size(self, file_path):
        asynch = self.get_property("asynchronous")
        file_size = utils.get_file_size(file_path)
        error_msg = None
        if file_size > MAX_POST_BODY_SIZE:
            error_msg = "Invalid request: Payload size {0:.2f} MB greater than 6 MB".format((file_size/(1024*1024)))
        elif asynch and file_size > MAX_POST_BODY_SIZE_ASYNC:
            error_msg = "Invalid request: Payload size {0:.2f} KB greater than 128 KB".format((file_size/(1024)))
        if error_msg:
            error_msg += "\nCheck AWS Lambda invocation limits in : https://docs.aws.amazon.com/lambda/latest/dg/limits.html"
            logger.error(error_msg)
