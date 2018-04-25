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

from .boto import BotoClient
from .iam import IAM
from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ReadTimeout
from enum import Enum
from multiprocessing.pool import ThreadPool
from src.parser.cfgfile import ConfigFile
from src.providers.aws.response import OutputType
import json
import os
import src.http.invoke as invoke
import src.logger as logger
import src.providers.aws.client.codezip as codezip
import src.providers.aws.client.validators as validators
import src.providers.aws.response as response_parser
import src.utils as utils
import tempfile

MAX_CONCURRENT_INVOCATIONS = 1000

class CallType(Enum):
    INIT = "init"
    RUN = "run"
    LS = "ls"
    RM = "rm"
    LOG = "log"
    INVOKE = "invoke"    
    
def get_call_type(value):
    for call_type in CallType:
        if call_type.value == value:
            return call_type

class Lambda(object):
    
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
    
    @utils.lazy_property
    def client(self):
        client = LambdaClient()
        return client    
    
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

    def get_delete_all(self):
        return self.get_property("all")

    def get_output_type(self):
        return self.get_property("output") 
        
    def get_function_name(self):
        return self.get_property("name")
    
    def get_function_arn(self):
        return self.get_property("function_arn")
    
    def need_preheat(self):
        return self.get_property("preheat")
    
    def has_event_source(self):
        return utils.has_dict_prop_value(self.properties, 'event_source')    
    
    def get_event_source(self):
        return self.get_property("event_source")   
    
    def create_function(self):
        try:
            response = self.client.create_function(self.get_property("name"),
                                                   self.get_property("runtime"),
                                                   self.get_property("iam", "role"),
                                                   self.get_property("handler"),
                                                   self.get_property("code"),
                                                   self.get_property("environment"),
                                                   self.get_property("description"),
                                                   self.get_property("time"),
                                                   self.get_property("memory"),
                                                   self.get_property("tags"))
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
        name = 'scar-%s' % '-'.join(parsed_id_or_path)
        i = 1
        while self.find_function(name):
            name = 'scar-%s-%s' % ('-'.join(parsed_id_or_path), str(i))
            i += 1
        return name    
    
    def check_function_name(self, func_name=None):
        call_type = self.get_property("call_type")
        if func_name:
            function_name = func_name
        else:
            function_name= self.get_property("name")
        function_found = self.find_function(function_name)
        error_msg = None
        if function_found and (call_type == CallType.INIT):
            error_msg = "Function name '%s' already used." % function_name
        elif (not function_found) and ((call_type == CallType.RM) or 
                                       (call_type == CallType.RUN) or 
                                       (call_type == CallType.INVOKE)):
            error_msg = "Function '%s' doesn't exist." % function_name
        if error_msg:
            logger.error(error_msg)             
            utils.finish_failed_execution()             
    
    def link_function_and_event_source(self):
        self.client.add_invocation_permission_from_s3(self.get_function_name(), 
                                                                           self.get_event_source())                    
        
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
        response_parser.parse_invocation_response(response,
                                                  self.get_function_name(),
                                                  self.get_property("output"), 
                                                  self.is_asynchronous())

    def invoke_lambda_function(self):
        return self.client.invoke_function(self.get_function_name(),
                                           self.get_property("invocation_type"),
                                           self.get_property("log_type"),
                                           json.dumps(self.get_property("payload")))

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
        
    def set_function_code(self):
        dbucket = self.get_property("deployment_bucket")
        func_name = self.get_property("name")
        bucket_file_key = 'lambda/' + func_name + '.zip'
        # Zip all the files and folders needed
        codezip.create_code_zip(func_name,
                                self.get_property("environment", "Variables"),
                                script=self.get_property("script"),
                                extra_payload=self.get_property("extra_payload"),
                                image_id=self.get_property("image_id"),
                                image_file=self.get_property("image_file"),
                                deployment_bucket=dbucket,
                                file_key=bucket_file_key)
        
        if dbucket and dbucket != "":
            self.properties['code'] = { "S3Bucket": dbucket, "S3Key" : bucket_file_key }
        else:
            self.properties['code'] = { "ZipFile": utils.get_file_as_byte_array(self.get_property("zip_file_path"))}

    def has_image_file(self):
        return utils.has_dict_prop_value(self.properties, 'image_file')
    
    def has_api_defined(self):
        return utils.has_dict_prop_value(self.properties, 'api_gateway_name')    
    
    def has_deployment_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'deployment_bucket')
        
    def has_output_bucket(self):
        return utils.has_dict_prop_value(self.properties, 'output_bucket')
    
    def has_output_lambda(self):
        return utils.has_dict_prop_value(self.properties, 'output_lambda')
        
    def set_required_environment_variables(self):
        self.add_lambda_environment_variable('TIMEOUT_THRESHOLD', str(self.get_property("timeout_threshold")))
        self.add_lambda_environment_variable('RECURSIVE', str(self.get_property("recursive")))
        self.add_lambda_environment_variable('IMAGE_ID', self.get_property("image_id"))
        if self.has_output_lambda():
            self.add_lambda_environment_variable('OUTPUT_LAMBDA', self.get_property("output_lambda"))
        if self.has_output_bucket():
            self.add_lambda_environment_variable('OUTPUT_BUCKET', self.get_property("output_bucket"))            

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

    def update_function_attributes(self, args):
        memory = self.get_argument_value(args, 'memory')
        time = self.get_argument_value(args, 'time')
        env_vars = self.get_property('environment_variables')
        func_name = self.get_property("name")
        if memory:
            self.client.update_function_memory(func_name, memory)
        if time:
            self.client.update_function_timeout(func_name, time)
        if env_vars:
            self.client.update_function_env_variables(func_name, env_vars)        

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
        if ((call_type != CallType.LS) and (not self.get_delete_all())):
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
                self.update_function_attributes(args)
                if self.get_argument_value(args, 'script'):
                    parsed_script = utils.escape_string(self.get_property("script").read())
                    self.set_property('payload', { "script" : parsed_script })
                if self.get_argument_value(args, 'cont_args'):
                    parsed_cont_args = utils.escape_list(self.get_property("cont_args"))
                    self.set_property('payload', { "cmd_args" : parsed_cont_args })

    def get_all_functions(self, arn_list):
        function_info_list = []
        try:
            for function_arn in arn_list:
                function_info_list.append(self.client.get_function_info(function_arn))
        except ClientError as ce:
            print ("Error getting function info by arn: %s" % ce)
        return function_info_list
    
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

    def get_api_gateway_id(self, func_name=None):
        if func_name:
            function_name = func_name
        else:
            function_name = self.get_function_name()
        self.check_function_name(function_name)
        env_vars = self.client.get_function_environment_variables(function_name)
        if ('API_GATEWAY_ID' in env_vars['Variables']):
            return env_vars['Variables']['API_GATEWAY_ID']
        
    def invoke_function_http(self, func_name=None):
        if func_name:
            function_name = func_name
        else:
            function_name = self.get_function_name()
        api_id = self.get_api_gateway_id(function_name)

        if api_id is None or api_id == "":
            error_msg = "Error retrieving API ID for lambda function {0}".format(func_name)
            logger.error(error_msg)
            utils.finish_failed_execution()
        
        function_url = 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(api_id, self.get_property("region"))
        asynch=self.get_property("asynchronous")
        headers=None
        if asynch:
            headers = {'X-Amz-Invocation-Type': 'Event'}
        
        params = self.get_property("parameters")
        if params:
            params = json.loads(params)
        
        data = self.get_property("data-binary")
        if data:
            with open(data, 'rb') as f:
                data = f.read()
        
        response = invoke.invoke_function(function_url, 
                               method=self.get_property("request"), 
                               parameters=params, 
                               data=data, 
                               headers=headers )
        
        response_parser.parse_http_response(response, function_name, asynch)

class LambdaClient(BotoClient):
    '''A low-level client representing aws LambdaClient.
    https://boto3.readthedocs.io/en/latest/reference/services/lambda.htmll'''    
    
    def __init__(self, region=None):
        super().__init__('lambda', region)
    
    def update_function_timeout(self, function_name, timeout):
        try:
            self.get_client().update_function_configuration(FunctionName=function_name,
                                                            Timeout=validators.validate_time(timeout))
        except ClientError as ce:
            error_msg = "Error updating lambda function timeout"
            logger.error(error_msg, error_msg + ": %s" % ce)
            utils.finish_failed_execution()
    
    def update_function_memory(self, function_name, memory):
        try:
            self.get_client().update_function_configuration(FunctionName=function_name,
                                                            MemorySize=validators.validate_memory(memory))
        except ClientError as ce:
            error_msg = "Error updating lambda function memory"
            logger.error(error_msg, error_msg + ": %s" % ce)
            utils.finish_failed_execution()     
            
    def create_function(self, function_name, runtime, role, 
                        handler, code, environment,
                        description, timeout, memory_size, tags): 
        try:
            logger.info("Creating lambda function.")
            response = self.get_client().create_function(FunctionName=function_name,
                                                         Runtime=runtime,
                                                         Role=role,
                                                         Handler=handler,
                                                         Code=code,
                                                         Environment=environment,
                                                         Description=description,
                                                         Timeout=timeout,
                                                         MemorySize=memory_size,
                                                         Tags=tags)
            return response
        except ClientError as ce:
            error_msg = "Error creating lambda function"
            logger.error(error_msg, error_msg + ": %s" % ce)
            raise ce            

    def get_function_info(self, function_name_or_arn):
        ''' You can specify a function name or you can specify
         the Amazon Resource Name (ARN) of the function.
         Returns the configuration information of the Lambda function.
         http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.get_function_configuration '''
        try:
            return self.get_client().get_function_configuration(FunctionName=function_name_or_arn)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                raise ce
            else:            
                error_msg = "Error getting function data"
                logger.error(error_msg, error_msg + ": %s" % ce)
     
        
    def get_function_environment_variables(self, function_name):
        return self.get_client().get_function(FunctionName=function_name)['Configuration']['Environment']
    
    def update_function_env_variables(self, function_name, env_vars):
        try:
            # Retrieve the global variables already defined
            lambda_env_variables = self.get_function_environment_variables(function_name)
            lambda_env_variables['Variables'].update(env_vars)
            self.get_client().update_function_configuration(FunctionName=function_name,
                                                            Environment=lambda_env_variables)
        except ClientError as ce:
            error_msg = "Error updating the environment variables of the lambda function"
            logger.error(error_msg, error_msg + ": %s" % ce)
    
    def add_invocation_permission_from_s3(self, function_name, bucket_name):
            self.add_invocation_permission(function_name, "s3.amazonaws.com", 'arn:aws:s3:::%s' % bucket_name)
    
    def list_functions(self):
        ''' Returns a list of your Lambda functions. '''
        functions = []
        try:
            result = self.get_client().list_functions();
            if "Functions" in result:
                functions.extend(result['Functions'])
            while utils.has_dict_prop_value(result, "NextMarker"):
                result = self.get_client().list_functions(Marker=result['NextMarker']);
                if "Functions" in result:
                    functions.extend(result['Functions'])            
            return functions
        except ClientError as ce:
            error_msg = "Error listing Lambda functions"
            logger.error(error_msg, error_msg + ": %s" % ce)                         
            
    def delete_function(self, function_name):
        try:
            # Delete the lambda function
            return self.get_client().delete_function(FunctionName=function_name)
        except ClientError as ce:
            error_msg = "Error deleting the lambda function"
            logger.error(error_msg, error_msg + ": %s" % ce)            
    
    def invoke_function(self, function_name, invocation_type, log_type, payload):
        response = {}
        try:
            response = self.get_client().invoke(FunctionName=function_name,
                                                InvocationType=invocation_type,
                                                LogType=log_type,
                                                Payload=payload)
        except ClientError as ce:
            error_msg = "Error invoking lambda function"
            logger.error(error_msg, error_msg + ": %s" % ce)
            utils.finish_failed_execution()
    
        except ReadTimeout as rt:
            error_msg = "Timeout reading connection pool"
            logger.error(error_msg, error_msg + ": %s" % rt)            
            utils.finish_failed_execution()
        return response
    
    def add_invocation_permission(self, function_name, principal, source_arn):
        try:
            self.get_client().add_permission(FunctionName=function_name,
                                             StatementId=utils.get_random_uuid4_str(),
                                             Action="lambda:InvokeFunction",
                                             Principal=principal,
                                             SourceArn=source_arn )
        except ClientError as ce:
            error_msg = "Error setting lambda permissions"
            logger.error(error_msg, error_msg + ": %s" % ce)                                     
        