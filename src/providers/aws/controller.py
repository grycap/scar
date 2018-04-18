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

from .client.lambdafunction import Lambda
from .client.cloudwatchlogs import CloudWatchLogs
from .client.apigateway import APIGateway
from .client.s3 import S3
from .client.iam import IAM
from .client.resourcegroups import ResourceGroups
from botocore.exceptions import ClientError
from src.cmdtemplate import Commands

import src.logger as logger
import src.providers.aws.response as response_parser
import src.utils as utils

class AWS(Commands):

    @utils.lazy_property
    def _lambda(self):
        '''It's called _lambda because 'lambda'
        it's a restricted word in python'''
        _lambda = Lambda()
        return _lambda  
    
    @utils.lazy_property
    def cloudwatch_logs(self):
        cloudwatch_logs = CloudWatchLogs(self._lambda)
        return cloudwatch_logs
    
    @utils.lazy_property
    def api_gateway(self):
        api_gateway = APIGateway(self._lambda)
        return api_gateway    
    
    @utils.lazy_property
    def s3(self):
        s3 = S3(self._lambda)
        return s3      
    
    @utils.lazy_property
    def resource_groups(self):
        resource_groups = ResourceGroups()
        return resource_groups
    
    @utils.lazy_property
    def iam(self):
        iam = IAM()
        return iam    
       
    def init(self):
        
        if self._lambda.has_api_defined():
            api_id, aws_acc_id = self.api_gateway.create_api_gateway()
            self._lambda.set_api_gateway_id(api_id, aws_acc_id)        
        
        # Call the aws services
        self._lambda.create_function()
        self.cloudwatch_logs.create_log_group()
        
        if self._lambda.has_event_source():
            self.create_event_source()
       
        if self._lambda.has_api_defined():
            self._lambda.add_invocation_permission_from_api_gateway() 
            
        # If preheat is activated, the function is launched at the init step
        if self._lambda.need_preheat():    
            self._lambda.preheat_function()
    
    def run(self):
        if self._lambda.has_event_source():
            self.process_event_source_calls()               
        else:
            if self._lambda.is_asynchronous():
                self._lambda.set_asynchronous_call_parameters()
            self._lambda.launch_lambda_instance()
    
    def ls(self):
        lambda_functions = self.get_all_functions()
        response_parser.parse_ls_response(lambda_functions, 
                                          self._lambda.get_output_type())
    
    def rm(self):
        if self._lambda.get_delete_all():
            self.delete_all_resources(self.get_all_functions())
        else:
            self.delete_resources()
    
    def log(self):
        aws_log = self.cloudwatch_logs.get_aws_log()
        print(aws_log)

    def parse_command_arguments(self, args):
        self._lambda.set_properties(args)

    def get_all_functions(self):
        functions_arn_list = self.get_functions_arn_list()
        return self._lambda.get_all_functions(functions_arn_list)        

    def get_functions_arn_list(self):
        user_id = self.iam.get_user_name_or_id()
        return self.resource_groups.get_lambda_functions_arn_list(user_id)
        
    def process_event_source_calls(self):
        s3_file_list = self.s3.get_processed_bucket_file_list()
        logger.info("Files found: '%s'" % s3_file_list)
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_file = s3_file_list.pop(0)
            self._lambda.launch_request_response_event(s3_file)
        # If the list has more elements, invoke functions asynchronously    
        if s3_file_list:
            self._lambda.process_asynchronous_lambda_invocations(s3_file_list)      
     
    def create_event_source(self):
        try:
            self.s3.create_event_source()
            self._lambda.link_function_and_event_source()
            self.s3.set_event_source_notification()
        except ClientError as ce:
            error_msg = "Error creating the event source"
            logger.error(error_msg, error_msg + ": %s" % ce)

    def delete_all_resources(self, lambda_functions):
        for function in lambda_functions:
            self.delete_resources(function['FunctionName'])
        
    def delete_resources(self, function_name=None):
        # Delete associated api
        api_id = self._lambda.get_api_gateway_id(function_name)
        output_type = self._lambda.get_output_type()
        if api_id:
            self.api_gateway.delete_api_gateway(api_id, output_type)
        # Delete associated log
        self.cloudwatch_logs.delete_log_group(function_name)
        # Delete function
        self._lambda.delete_function(function_name)

        
