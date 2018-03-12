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
from .client.s3 import S3
from .client.iam import IAM
from .client.resourcegroups import ResourceGroups
from botocore.exceptions import ClientError
from multiprocessing.pool import ThreadPool
from src.cmdtemplate import Commands

import src.logger as logger
import src.providers.aws.response as response_parser
import src.utils as utils

MAX_CONCURRENT_INVOCATIONS = 1000

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
        # Call the aws services
        self._lambda.create_function()
        self.cloudwatch_logs.create_log_group()
        
        if self._lambda.has_event_source():
            self.create_event_source()
        # If preheat is activated, the function is launched at the init step
        if self._lambda.need_preheat():    
            self._lambda.preheat_function()
    
    def run(self):
        if self._lambda.has_event_source():
            self.process_event_source_calls()               
        else:
            self._lambda.launch_lambda_instance()
    
    def ls(self):
        lambda_functions = self.get_all_functions()
        response_parser.parse_ls_response(lambda_functions, 
                                          self._lambda.get_output_type())
    
    def rm(self):
        if self._lambda.get_delete_all():
            self.delete_all_resources(self.get_all_functions())
        else:
            self.delete_function_and_log()
    
    def log(self):
        aws_log = self.cloudwatch_logs.get_aws_log()
        print(aws_log)

    def parse_command_arguments(self, args):
        self._lambda.set_properties(args)

    def get_all_functions(self):
        functions_arn_list = self.get_functions_arn_list()
        return self._lambda.get_all_functions(functions_arn_list)        

    def launch_async_event(self, s3_file):
        self.aws_lambda.set_asynchronous_call_parameters()
        return self.launch_s3_event(s3_file)        
   
    def launch_request_response_event(self, s3_file):
        self.aws_lambda.set_request_response_call_parameters()
        return self.launch_s3_event(s3_file)            
               
    def launch_s3_event(self, s3_file):
        self.aws_lambda.set_event_source_file_name(s3_file)
        self.aws_lambda.set_payload(self.aws_lambda.event)
        logger.info("Sending event for file '%s'" % s3_file)
        return self._lambda.invoke_function(self.aws_lambda)
        
    def get_functions_arn_list(self):
        user_id = self.iam.get_user_name_or_id()
        return self.resource_groups.get_lambda_functions_arn_list(user_id)
        
    def process_event_source_calls(self):
        s3_file_list = self.s3().get_processed_bucket_file_list()
        logger.info("Files found: '%s'" % s3_file_list)
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_file = s3_file_list.pop(0)
            response = self._lambda.launch_request_response_event(self.aws_lambda, s3_file)
            self.parse_invocation_response(response)
        # If the list has more elements, invoke functions asynchronously    
        if s3_file_list:
            self.process_asynchronous_lambda_invocations(s3_file_list)      
     
    def process_asynchronous_lambda_invocations(self, s3_file_list):
        size = len(s3_file_list)
        if size > MAX_CONCURRENT_INVOCATIONS:
            s3_file_chunk_list = utils.divide_list_in_chunks(s3_file_list, MAX_CONCURRENT_INVOCATIONS)
            for s3_file_chunk in s3_file_chunk_list:
                self.launch_concurrent_lambda_invocations(s3_file_chunk)
        else:
            self.launch_concurrent_lambda_invocations(s3_file_list)
    
    def launch_concurrent_lambda_invocations(self, s3_file_list):
        pool = ThreadPool(processes=len(s3_file_list))
        pool.map(
            lambda s3_file: self.parse_invocation_response(self._lambda.launch_async_event(s3_file, self.aws_lambda)),
            s3_file_list
        )
        pool.close()
    
    def create_event_source(self):
        # To ease the readability
        bucket_name = self.get_event_source()
        function_arn = self._lambda.get_function_arn()
        try:
            self.s3.create_event_source(bucket_name)
            self._lambda.link_function_and_event_source()
            self.s3.set_event_source_notification(bucket_name, function_arn)
        except ClientError as ce:
            print ("Error creating the event source: %s" % ce)

    def delete_all_resources(self, lambda_functions):
        for function in lambda_functions:
            self.delete_function_and_log(function['FunctionName'])
        
    def delete_function_and_log(self, function_name=None):
        self._lambda.delete_function(function_name)
        # Delete associated log
        self.cloudwatch_logs.delete_log_group(function_name)
        
