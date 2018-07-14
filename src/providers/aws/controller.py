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

from src.providers.aws.lambdafunction import Lambda
from src.providers.aws.cloudwatchlogs import CloudWatchLogs
from src.providers.aws.apigateway import APIGateway
from src.providers.aws.s3 import S3
from src.providers.aws.iam import IAM
from src.providers.aws.resourcegroups import ResourceGroups
from botocore.exceptions import ClientError
from src.cmdtemplate import Commands
from src.providers.aws.validators import AWSValidator

import src.logger as logger
import src.providers.aws.response as response_parser
import src.utils as utils
import os
import src.exceptions as excp

class AWS(Commands):

    properties = {}

    @utils.lazy_property
    def _lambda(self):
        '''It's called _lambda because 'lambda'
        it's a restricted word in python'''
        _lambda = Lambda(self.properties)
        return _lambda
    
    @utils.lazy_property
    def cloudwatch_logs(self):
        cloudwatch_logs = CloudWatchLogs(self.properties)
        return cloudwatch_logs
    
    @utils.lazy_property
    def api_gateway(self):
        api_gateway = APIGateway(self.properties)
        return api_gateway    
    
    @utils.lazy_property
    def s3(self):
        s3 = S3(self.properties)
        return s3      
    
    @utils.lazy_property
    def resource_groups(self):
        resource_groups = ResourceGroups(self.properties)
        return resource_groups
    
    @utils.lazy_property
    def iam(self):
        iam = IAM(self.properties)
        return iam    
       
    @excp.exception(logger)
    def init(self):
        if self._lambda.has_api_defined():
            api_id, aws_acc_id = self.api_gateway.create_api_gateway()
            self._lambda.set_api_gateway_id(api_id, aws_acc_id)        
        
        # Call the aws services
        self._lambda.create_function()
        self.cloudwatch_logs.create_log_group()
        
        if self._lambda.has_input_bucket():
            self.create_input_source()
            
        if self._lambda.has_output_bucket():
            self.s3.create_bucket(self._lambda.get_output_bucket())            
       
        if self._lambda.has_api_defined():
            self._lambda.add_invocation_permission_from_api_gateway() 
            
        # If preheat is activated, the function is launched at the init step
        if self._lambda.need_preheat():    
            self._lambda.preheat_function()
    
    def invoke(self):
        function_name = self._lambda.get_function_name()
        response = self._lambda.invoke_function_http(function_name)
        response_parser.parse_http_response(response, 
                                            function_name, 
                                            self._lambda.get_property("asynchronous"))
    
    def run(self):
        if self._lambda.has_input_bucket():
            self.process_input_bucket_calls()
        else:
            if self._lambda.is_asynchronous():
                self._lambda.set_asynchronous_call_parameters()
            self._lambda.launch_lambda_instance()
            
    def update(self):
        self._lambda.update_function_attributes()
    
    @excp.exception(logger)
    def ls(self):
        if 's3' in self.properties:
            file_list = self.s3.get_bucket_files()
            for file_info in file_list:
                print(file_info)
        else:
            lambda_functions = self.get_all_functions()
            response_parser.parse_ls_response(lambda_functions, 
                                              self.properties['output'])
    
    def rm(self):
        if self._lambda.delete_all():
            self.delete_all_resources(self.get_all_functions())
        else:
            self.delete_resources(self._lambda.get_function_name())
    
    def log(self):
        aws_log = self.cloudwatch_logs.get_aws_log()
        print(aws_log)
        
    def put(self):
        bucket_name = self._lambda.get_property("bucket")
        bucket_folder = self._lambda.get_property("bucket_folder")
        path_to_upload = self._lambda.get_property("path")
        self.upload_to_s3(bucket_name, bucket_folder, path_to_upload)
        
    def get(self):
        bucket_name = self._lambda.get_property("bucket")
        file_prefix = self._lambda.get_property("bucket_folder")
        output_path = self._lambda.get_property("path")
        self.s3.download_bucket_files(bucket_name, file_prefix, output_path)

    @AWSValidator.validate()
    def parse_arguments(self, **kwargs):
        self.properties = kwargs['aws']
        self.add_aws_properties()

        import pprint
        pprint.pprint(self.properties)
        print('----------------------------------------------------------------------------')
    
    def add_aws_properties(self):
        self.add_tags()
        self.add_output()
        
    def add_tags(self):
        self.properties["tags"] = {}
        self.properties["tags"]['createdby'] = 'scar'
        self.properties["tags"]['owner'] = self.iam.get_user_name_or_id()
                
    def add_output(self):
        self.properties["output"] =  response_parser.OutputType.PLAIN_TEXT
        if 'json' in self.properties and self.properties['json']:
            self.properties["output"] = response_parser.OutputType.JSON
        # Override json ouput if both of them are defined
        if 'verbose' in self.properties and self.properties['verbose']:
            self.properties["output"] = response_parser.OutputType.VERBOSE
        
    def get_all_functions(self):
        functions_arn_list = self.get_functions_arn_list()
        return self._lambda.get_all_functions(functions_arn_list)        

    def get_functions_arn_list(self):
        user_id = self.iam.get_user_name_or_id()
        return self.resource_groups.get_lambda_functions_arn_list(user_id)
        
    def process_input_bucket_calls(self):
        s3_file_list = self.s3.get_processed_bucket_file_list()
        logger.info("Files found: '%s'" % s3_file_list)
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_file = s3_file_list.pop(0)
            self._lambda.launch_request_response_event(s3_file)
        # If the list has more elements, invoke functions asynchronously    
        if s3_file_list:
            self._lambda.process_asynchronous_lambda_invocations(s3_file_list)      

    def upload_to_s3(self, bucket_name, bucket_folder, path_to_upload):
        self.s3.create_bucket(bucket_name)
        if(os.path.isdir(path_to_upload)):
            files = utils.get_all_files_in_directory(path_to_upload)
        else:
            files = [path_to_upload]
        for file in files:
            self.upload_file_to_s3(bucket_name, bucket_folder, file)            

    def upload_file_to_s3(self, bucket_name, bucket_folder, file_path):
        file_data = utils.read_file(file_path, 'rb')
        file_name = os.path.basename(file_path)
        file_key = "{0}".format(file_name)
        if bucket_folder and bucket_folder != "" and bucket_folder.endswith("/"):
            file_key = "{0}{1}".format(bucket_folder, file_name)
        else:
            file_key = "{0}/{1}".format(bucket_folder, file_name)
        logger.info("Uploading file '{0}' to bucket '{1}' with key '{2}'".format(file_path, bucket_name, file_key))
        self.s3.upload_file(bucket_name, file_key, file_data)
     
    def create_input_source(self):
        try:
            self.s3.create_input_bucket()
            self._lambda.link_function_and_input_bucket()
            self.s3.set_input_bucket_notification()
        except ClientError as ce:
            error_msg = "Error creating the event source"
            logger.error(error_msg, error_msg + ": %s" % ce)

    def delete_all_resources(self, lambda_functions):
        for function in lambda_functions:
            self.delete_resources(function['FunctionName'])
        
    def delete_resources(self, function_name):
        # Delete associated api
        api_id = self._lambda.get_api_gateway_id(function_name)
        output_type = self._lambda.get_output_type()
        if api_id:
            self.api_gateway.delete_api_gateway(api_id, output_type)
        # Delete associated log
        self.cloudwatch_logs.delete_log_group(function_name)
        # Delete associated notifications
        func_info = self._lambda.get_function_info(function_name)
        function_arn = func_info['FunctionArn']
        variables = func_info['Environment']['Variables']
        if 'INPUT_BUCKET' in variables:
            bucket_name = variables['INPUT_BUCKET']
            self.s3.delete_bucket_notification(bucket_name, function_arn)        
        # Delete function
        self._lambda.delete_function(function_name)

        
