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

from .clients.cloudwatchlogs import CloudWatchLogsClient
from .clients.lambdac import LambdaClient
from .clients.s3 import S3Client
from .responseparser import ResponseParser
from botocore.exceptions import ClientError
from multiprocessing.pool import ThreadPool
import logging
import utils.functionutils as utils

MAX_CONCURRENT_INVOCATIONS = 1000

def lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.'''
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

class AWSManager(object):

    def __init__(self, aws_lambda):
        self.aws_lambda = aws_lambda

    @lazy_property
    def lambda_client(self):
        lambda_client = LambdaClient()
        return lambda_client    
    
    @lazy_property
    def cloudwatch_logs_client(self):
        cloudwatch_logs_client = CloudWatchLogsClient()
        return cloudwatch_logs_client
    
    @lazy_property
    def s3_client(self):
        s3_client = S3Client()
        return s3_client      
    
    @lazy_property
    def response_parser(self):
        response_parser = ResponseParser()
        return response_parser  

    def launch_async_event(self, aws_lambda, s3_file):
        aws_lambda.set_asynchronous_call_parameters()
        return self.launch_s3_event(aws_lambda, s3_file)        
   
    def launch_request_response_event(self, aws_lambda, s3_file):
        aws_lambda.set_request_response_call_parameters()
        return self.launch_s3_event(aws_lambda, s3_file)            

    def preheat_function(self, aws_lambda):
        aws_lambda.set_request_response_call_parameters()
        return self.invoke_lambda_function(aws_lambda)
                
    def launch_s3_event(self, aws_lambda, s3_file):
        aws_lambda.set_event_source_file_name(s3_file)
        aws_lambda.set_payload(aws_lambda.event)
        logging.info("Sending event for file '%s'" % s3_file)
        self.invoke_lambda_function(aws_lambda)
        
    def process_event_source_calls(self):
        s3_file_list = self.s3_client.get_s3_file_list(self.aws_lambda.event_source)
        logging.info("Files found: '%s'" % s3_file_list)
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_file = s3_file_list.pop(0)
            response = self.lambda_client.launch_request_response_event(self.aws_lambda, s3_file)
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
            lambda s3_file: self.parse_invocation_response(self.lambda_client.launch_async_event(s3_file, self.aws_lambda)),
            s3_file_list
        )
        pool.close()
    
    def launch_lambda_instance(self):
        response = self.lambda_client.invoke_lambda_function(self.aws_lambda)
        self.parse_invocation_response(response)   
        
    def add_event_source(self):
        bucket_name = self.aws_lambda.event_source
        try:
            self.s3_client.check_and_create_s3_bucket(bucket_name)
            self.lambda_client.add_lambda_permissions(self.aws_lambda.name, bucket_name)
            self.s3_client.create_trigger_from_bucket(bucket_name, self.aws_lambda.function_arn)
            if self.aws_lambda.recursive:
                self.s3_client.add_s3_bucket_folder(bucket_name, "recursive/")
                self.s3_client.create_recursive_trigger_from_bucket(bucket_name, self.aws_lambda.function_arn)
        except ClientError as ce:
            print ("Error creating the event source: %s" % ce)                        

    def create_lambda_function(self):
        # lambda_validator.validate_function_creation_values(self.aws_lambda)
        try:
            lambda_response = self.lambda_client.create_function(self.aws_lambda)
            self.response_parser.parse_lambda_function_creation_response(lambda_response,
                                                                         self.aws_lambda.name,
                                                                         self.lambda_client.get_access_key(), 
                                                                         self.aws_lambda.output)
        except ClientError as ce:
            logging.error("Error initializing lambda function: %s" % ce)
            utils.finish_failed_execution()
        finally:
            # Remove the files created in the operation
            utils.delete_file(self.aws_lambda.zip_file_path)

    def create_log_group(self):
        # lambda_validator.validate_log_creation_values(self.aws_lambda)
        cw_response = self.cloudwatch_logs_client.create_log_group(self.aws_lambda)
        self.response_parser.parse_log_group_creation_response(cw_response,
                                                               self.aws_lambda.log_group_name,
                                                               self.aws_lambda.output)
        # Set retention policy into the log group
        self.cloudwatch_logs_client.set_log_retention_policy(self.aws_lambda)

    def delete_all_resources(self, output_type):
        lambda_functions = self.lambda_client.get_all_functions()
        for function in lambda_functions:
            self.delete_resources(function['Configuration']['FunctionName'], output_type)
        
    def delete_resources(self, function_name, output_type):
        self.lambda_client.check_function_name_not_exists(function_name)
        # Delete lambda function
        delete_function_response = self.lambda_client.delete_lambda_function(function_name)
        self.response_parser.parse_delete_function_response(function_name, delete_function_response, output_type)
        # Delete associated log
        delete_log_response = self.cloudwatch_logs_client.delete_log_group(function_name)
        self.response_parser.parse_delete_log_response(function_name, delete_log_response, output_type)

