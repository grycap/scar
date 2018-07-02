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

from src.providers.aws.iam import IAM
from botocore.exceptions import ClientError
from enum import Enum
from multiprocessing.pool import ThreadPool
from src.parser.cfgfile import ConfigFile
from src.providers.aws.response import OutputType
import json
import os
import src.http.invoke as invoke
import src.logger as logger
import src.providers.aws.payload as codezip
import src.providers.aws.validators as validators
import src.providers.aws.response as response_parser
import src.utils as utils
import tempfile
import base64
from src.providers.aws.clientfactory import GenericClient

MAX_CONCURRENT_INVOCATIONS = 1000
MAX_POST_BODY_SIZE = 1024*1024*6
MAX_POST_BODY_SIZE_ASYNC = 1024*95

class CallType(Enum):
    INIT = "init"
    RUN = "run"
    UPDATE = "update"    
    LS = "ls"
    RM = "rm"
    LOG = "log"
    INVOKE = "invoke"
    PUT = "put"
    GET = "get"           

def get_call_type(value):
    for call_type in CallType:
        if call_type.value == value:
            return call_type

class Lambda(GenericClient):
    
    properties = {
        "runtime" : "python3.6",
        "invocation_type" : "RequestResponse",
        "log_type" : "Tail",
        "output" : OutputType.PLAIN_TEXT,
        "payload" : {},
        "tags" : {},
        "environment" : { 'Variables' : {} },
        "environment_variables" : {},
        "name_regex" : "(arn:(aws[a-zA-Z-]*)?:lambda:)?([a-z]{2}(-gov)?-[a-z]+-\d{1}:)?(\d{12}:)?(function:)?([a-zA-Z0-9-_]+)(:(\$LATEST|[a-zA-Z0-9-_]+))?",
        "s3_event" : { "Records" : [ 
                        {"eventSource" : "aws:s3",
                         "s3" : {"bucket" : { "name" : "" },
                                 "object" : { "key" : ""  } }
                        }]},
        "zip_file_path" : os.path.join(tempfile.gettempdir(), 'function.zip')
    }    

    def __init__(self):
        self.set_config_file_properties()
        validators.validate_iam_role(self.properties["iam"])    

    def set_config_file_properties(self):
        config_file_props = ConfigFile().get_aws_props()
        self.properties = utils.merge_dicts(self.properties, config_file_props['lambda'])
        self.properties['iam'] = config_file_props['iam']
        self.properties['cloudwatch'] = config_file_props['cloudwatch']

    def get_property(self, value, nested_value=None):
        if value in self.properties:
            if nested_value and nested_value in self.properties[value]:
                return self.properties[value][nested_value]
            else:
                return self.properties[value]
        
    def set_property(self, key, value):
        self.properties[key] = value

    def delete_all(self):
        return self.get_property("all")

    def get_output_type(self):
        return self.get_property("output") 
        
    def get_function_name(self):
        return self.get_property("name")
    
    def get_function_arn(self):
        return self.get_property("function_arn")
    
    def need_preheat(self):
        return self.get_property("preheat")
    
    def get_input_bucket(self):
        return self.get_property("input_bucket")      
    
    def get_output_bucket(self):
        return self.get_property("output_bucket")    
    
    def get_creations_args(self):
        return {'FunctionName' : self.get_property("name"),
                'Runtime' : self.get_property("runtime"),
                'Role' : self.get_property("iam", "role"),
                'Handler' : self.get_property("handler"),
                'Code' : self.get_property("code"),
                'Environment' : self.get_property("environment"),
                'Description':self.get_property("description"),
                'Timeout': self.get_property("time"),
                'MemorySize':self.get_property("memory"),
                'Tags':self.get_property("tags") }
    
    def create_function(self):
        try:
            response = self.client.create_function(**self.get_creations_args())
            if response and 'FunctionArn' in response:
                self.properties["function_arn"] = response['FunctionArn']
            response_parser.parse_lambda_function_creation_response(response,
                                                                    self.get_function_name(),
                                                                    self.client.get_access_key(),
                                                                    self.get_output_type())
        except ClientError as ce:
            error_msg = "Error initializing lambda function."
            logger.error(error_msg, error_msg + ": %s" % ce)
            utils.finish_failed_execution()
        finally:
            # Remove the files created in the operation
            utils.delete_file(self.properties["zip_file_path"])
        
    def delete_function(self, func_name=None):
        if func_name:
            function_name = func_name
        else:
            function_name = self.get_function_name()
        self.check_function_name(function_name)
        # Delete lambda function
        response = self.client.delete_function(function_name)
        response_parser.parse_delete_function_response(response,
                                                       function_name,
                                                       self.get_output_type())        
        
    def create_function_name(self, image_id_or_path):
        parsed_id_or_path = image_id_or_path.replace('/', ',,,').replace(':', ',,,').replace('.', ',,,').split(',,,')
        name = "scar-{0}".format('-'.join(parsed_id_or_path))
        i = 1
        while self.find_function(name):
            name = "scar-{0}-{1}".format('-'.join(parsed_id_or_path), str(i))
            i += 1
        return name    
    
    def check_function_name(self, func_name=None):
        call_type = self.get_property("call_type")
        if func_name:
            function_name = func_name
        else:
            function_name = self.get_property("name")
        function_found = self.find_function(function_name)
        error_msg = None
        if function_found and (call_type == CallType.INIT):
            error_msg = "Function name '{0}' already used.".format(function_name)
        elif (not function_found) and ((call_type == CallType.RM) or 
                                       (call_type == CallType.RUN) or 
                                       (call_type == CallType.INVOKE)):
            error_msg = "Function '{0}' doesn't exist.".format(function_name)
        if error_msg:
            logger.error(error_msg)             
            utils.finish_failed_execution()             
    
    def link_function_and_input_bucket(self):
        self.add_invocation_permission_from_s3(self.get_function_name(), 
                                               self.get_input_bucket())
        
    def add_invocation_permission_from_s3(self, function_name, bucket_name):
            self.client.add_invocation_permission(function_name, 
                                                  "s3.amazonaws.com",
                                                  'arn:aws:s3:::{0}'.format(bucket_name))                            
        
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
        self.set_property('payload', self.get_property("s3_event"))
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
        
    def set_api_gateway_id(self, api_id, acc_id):
        self.set_property('api_gateway_id', api_id)
        self.set_property('aws_acc_id', acc_id)
        self.add_lambda_environment_variable('API_GATEWAY_ID', api_id)

    def set_request_response_call_parameters(self):
        self.set_property('invocation_type', "RequestResponse")
        self.set_property('log_type', "Tail")        

    def set_s3_event_source(self, file_name):
        self.properties['s3_event']['Records'][0]['s3']['bucket']['name'] = self.get_property('event_source')
        self.properties['s3_event']['Records'][0]['s3']['object']['key'] = file_name
        
    def set_property_if_has_value(self, dictio, key, prop):
        prop_val =  self.get_property(prop)
        if prop_val and prop_val != "":
            dictio[key] = prop_val        
        
    def get_function_code_args(self):
        package_args = {'FunctionName' : self.get_property("name"),
                        'EnvironmentVariables' : self.get_property("environment", "Variables")}
        self.set_property_if_has_value(package_args, 'Script', "init_script")
        self.set_property_if_has_value(package_args, 'ExtraPayload', "extra_payload")
        self.set_property_if_has_value(package_args, 'ImageId', "image_id")
        self.set_property_if_has_value(package_args, 'ImageFile', "image_file")
        self.set_property_if_has_value(package_args, 'DeploymentBucket', "deployment_bucket")
        if 'DeploymentBucket' in package_args:
            package_args['FileKey'] = 'lambda/' + self.get_property("name") + '.zip'        
        return package_args
        
    def set_function_code(self):
        package_args = self.get_function_code_args()
        # Zip all the files and folders needed
        codezip.prepare_lambda_payload(**package_args)
        
        if 'DeploymentBucket' in package_args:
            self.properties['code'] = { "S3Bucket": package_args['DeploymentBucket'], "S3Key" : package_args['FileKey'] }
        else:
            self.properties['code'] = { "ZipFile": utils.read_file(self.get_property("zip_file_path"), mode="rb")}

    def has_image_file(self):
        return utils.has_dict_prop_value(self.properties, 'image_file')
    
    def has_api_defined(self):
        return utils.has_dict_prop_value(self.properties, 'api_gateway_name')    
    
    def has_deployment_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'deployment_bucket')
 
    def has_input_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'input_bucket')
    
    def has_output_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'output_bucket')
    
    def has_output_folder(self):
        return utils.has_dict_prop_value(self.properties, 'output_folder')

    def set_required_environment_variables(self):
        self.add_lambda_environment_variable('TIMEOUT_THRESHOLD', str(self.get_property("timeout_threshold")))
        self.add_lambda_environment_variable('IMAGE_ID', self.get_property("image_id"))
        if self.has_input_bucket():
            self.add_lambda_environment_variable('INPUT_BUCKET', self.get_property("input_bucket"))
        if self.has_output_bucket():
            self.add_lambda_environment_variable('OUTPUT_BUCKET', self.get_property("output_bucket"))
        if self.has_output_folder():
            self.add_lambda_environment_variable('OUTPUT_FOLDER', self.get_property("output_folder"))                   

    def add_lambda_environment_variable(self, key, value):
        if (key is not None or key != "") and (value is not None):
            self.get_property("environment", "Variables")[key] = value        

    def set_environment_variables(self):
        if isinstance(self.get_property("environment_variables"), list):
            for env_var in self.get_property("environment_variables"):
                parsed_env_var = env_var.split("=")
                # Add an specific prefix to be able to find the variables defined by the user
                key = 'CONT_VAR_' + parsed_env_var[0]
                self.add_lambda_environment_variable(key, parsed_env_var[1])
        if (self.get_property("call_type") == CallType.INIT):
            self.set_required_environment_variables()

    def set_tags(self):
        self.properties["tags"]['createdby'] = 'scar'
        self.properties["tags"]['owner'] = IAM().get_user_name_or_id()

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
        defined_lambda_env_variables = self.client.get_function_environment_variables(self.get_property("name"))
        defined_lambda_env_variables['Variables'].update(env_vars['Variables'])
        update_args['Environment'] = defined_lambda_env_variables
        
        validators.validate(**update_args)
        self.client.update_function(**update_args)

    def set_call_type(self, call_type):
        self.set_property("call_type", get_call_type(call_type))
        return self.properties["call_type"]

    def set_output_type(self):
        if self.get_property("json"):
            self.set_property("output", OutputType.JSON)    
        elif self.get_property("verbose"):
            self.set_property("output", OutputType.VERBOSE)

    def set_properties(self, args):
        # Set the command line parsed properties
        self.properties = utils.merge_dicts(self.properties, vars(args))
        call_type = self.set_call_type(args.func.__name__)
        self.set_output_type()
        if ((call_type != CallType.LS) and 
            (not self.delete_all()) and
            (call_type != CallType.PUT) and
            (call_type != CallType.GET)):
            if (call_type == CallType.INIT):
                if (not self.get_property("name")) or (self.get_property("name") == ""):
                    func_name = "function"
                    if self.get_property("image_id") != "":
                        func_name = self.get_property("image_id")
                    elif self.get_property("image_file") != "":
                        func_name = self.get_property("image_file").split('.')[0]
                    self.properties["name"] = self.create_function_name(func_name)
                self.set_tags()
            
            self.check_function_name()
            function_name = self.get_property("name")
            validators.validate_function_name(function_name, self.get_property("name_regex"))
                
            self.set_environment_variables()
            self.properties["handler"] = function_name + ".lambda_handler"
            self.properties["log_group_name"] = '/aws/lambda/' + function_name
            
            if (call_type == CallType.INIT):   
                self.set_function_code()           
                
            if (call_type == CallType.RUN):
                if self.get_argument_value(args, 'run_script'):
                    file_content = utils.read_file(self.get_property("run_script"), 'rb')
                    # We first code to base64 in bytes and then decode those bytes to allow json to work
                    # https://stackoverflow.com/questions/37225035/serialize-in-json-a-base64-encoded-data#37239382
                    parsed_script = utils.utf8_to_base64_string(file_content)
                    self.set_property('payload', { "script" : parsed_script })
                
                if self.get_argument_value(args, 'c_args'):
                    parsed_cont_args = json.dumps(self.get_property("c_args"))
                    self.set_property('payload', { "cmd_args" : parsed_cont_args })

    def get_all_functions(self, arn_list):
        function_info_list = []
        try:
            for function_arn in arn_list:
                function_info_list.append(self.client.get_function_info(function_arn))
        except ClientError as ce:
            print ("Error getting function info by arn: %s" % ce)
        return function_info_list
    
    def get_function_info(self, function_name_or_arn):
        try:
            # If this call works the function exists
            return self.client.get_function_info(function_name_or_arn)
        except ClientError as ce:
            error_msg = "Error while looking for the lambda function"
            logger.error(error_msg, error_msg + ": %s" % ce)
            utils.finish_failed_execution()    
    
    def find_function(self, function_name_or_arn):
        validators.validate_function_name(function_name_or_arn, self.get_property("name_regex"))
        try:
            # If this call works the function exists
            self.client.get_function_info(function_name_or_arn)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:   
                error_msg = "Error while looking for the lambda function"
                logger.error(error_msg, error_msg + ": %s" % ce)
                utils.finish_failed_execution()
                
    def add_invocation_permission_from_api_gateway(self):
        api_gateway_id = self.get_property('api_gateway_id')
        aws_acc_id = self.get_property('aws_acc_id')
        # Testing permission
        self.client.add_invocation_permission(self.get_property("name"),
                                              'apigateway.amazonaws.com',
                                              'arn:aws:execute-api:us-east-1:{0}:{1}/*'.format(aws_acc_id, api_gateway_id))
        # Invocation permission
        self.client.add_invocation_permission(self.get_property("name"),
                                              'apigateway.amazonaws.com',
                                              'arn:aws:execute-api:us-east-1:{0}:{1}/scar/ANY'.format(aws_acc_id, api_gateway_id))                              

    def get_api_gateway_id(self, function_name):
        self.check_function_name(function_name)
        env_vars = self.client.get_function_environment_variables(function_name)
        if ('API_GATEWAY_ID' in env_vars['Variables']):
            return env_vars['Variables']['API_GATEWAY_ID']
        
    def get_api_gateway_url(self, function_name):
        api_id = self.get_api_gateway_id(function_name)
        if api_id is None or api_id == "":
            error_msg = "Error retrieving API ID for lambda function {0}".format(function_name)
            logger.error(error_msg)
            utils.finish_failed_execution()
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
            utils.finish_failed_execution()   
