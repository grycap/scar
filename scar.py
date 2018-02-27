#! /usr/bin/python

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

from aws.clients.awslambda import Lambda as LambdaClient
from aws.clients.cloudwatchlogs import CloudWatchLogs as CloudWatchLogsClient
from aws.clients.s3 import S3 as S3Client
from aws.lambdafunction import AWSLambda
from botocore.exceptions import ClientError
from multiprocessing.pool import ThreadPool
from tabulate import tabulate
from utils.commandparser import CommandParser
import json
import logging
import utils.functionutils as utils
import utils.outputtype as outputType

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='scar.log', level=logging.INFO, format=FORMAT)
MAX_CONCURRENT_INVOCATIONS = 1000
                  
class Scar(object):
    
    def __init__(self, aws_lambda):
        self.aws_lambda = aws_lambda
     
    def parse_lambda_function_creation_response(self, lambda_response):
        if self.aws_lambda.output == outputType.VERBOSE:
            logging.info('LambdaOutput', lambda_response)
        elif self.aws_lambda.output == outputType.JSON:
            logging.info('LambdaOutput', {'AccessKey' : LambdaClient().get_access_key(),
                                                   'FunctionArn' : lambda_response['FunctionArn'],
                                                   'Timeout' : lambda_response['Timeout'],
                                                   'MemorySize' : lambda_response['MemorySize'],
                                                   'FunctionName' : lambda_response['FunctionName']})
        else:
            print("Function '%s' successfully created." % self.aws_lambda.name)
            logging.info("Function '%s' successfully created." % self.aws_lambda.name)
    
    def parse_log_group_creation_response(self, cw_response):
        if self.aws_lambda.output == outputType.VERBOSE:
            logging.info('CloudWatchOuput', cw_response)
        if self.aws_lambda.output == outputType.JSON:
            logging.info('CloudWatchOutput', {'RequestId' : cw_response['ResponseMetadata']['RequestId'],
                                                                'HTTPStatusCode' : cw_response['ResponseMetadata']['HTTPStatusCode']})
        else:
            print("Log group '%s' successfully created." % self.aws_lambda.log_group_name)
            logging.info("Log group '%s' successfully created." % self.aws_lambda.log_group_name)
    
    def create_function(self):
        # lambda_validator.validate_function_creation_values(self.aws_lambda)
        try:
            lambda_response = LambdaClient().create_function(self.aws_lambda)
            self.parse_lambda_function_creation_response(lambda_response)
        except ClientError as ce:
            logging.error("Error initializing lambda function: %s" % ce)
            utils.finish_failed_execution()
        finally:
            # Remove the zip created in the operation
            utils.delete_file(self.aws_lambda.zip_file_path)
    
    def create_cloudwatch_log_group(self):
        # lambda_validator.validate_log_creation_values(self.aws_lambda)
        cw_response = CloudWatchLogsClient().create_cloudwatch_log_group(self.aws_lambda)
        self.parse_log_group_creation_response(cw_response)
        # Set retention policy into the log group
        CloudWatchLogsClient().set_cloudwatch_log_retention_policy(self.aws_lambda)
        
    def add_event_source(self):
        bucket_name = self.aws_lambda.event_source
        try:
            s3_client = S3Client()
            s3_client.check_and_create_s3_bucket(bucket_name)
            LambdaClient().add_lambda_permissions(self.aws_lambda.name, bucket_name)
            s3_client.create_trigger_from_bucket(bucket_name, self.aws_lambda.function_arn)
            if self.aws_lambda.recursive:
                s3_client.add_s3_bucket_folder(bucket_name, "recursive/")
                s3_client.create_recursive_trigger_from_bucket(bucket_name, self.aws_lambda.function_arn)
        except ClientError as ce:
            print ("Error creating the event source: %s" % ce)        
    
    def parse_aws_logs(self, logs, request_id):
        if (logs is None) or (request_id is None):
            return None
        full_msg = ""
        logging = False
        lines = logs.split('\n')
        for line in lines:
            if line.startswith('REPORT') and request_id in line:
                full_msg += line + '\n'
                return full_msg
            if logging:
                full_msg += line + '\n'
            if line.startswith('START') and request_id in line:
                full_msg += line + '\n'
                logging = True
    
    def preheat_function(self):
        response = LambdaClient().preheat_function(self.aws_lambda)
        self.parse_invocation_response(response)
    
    def launch_lambda_instance(self):
        response = LambdaClient().invoke_lambda_function(self.aws_lambda)
        self.parse_invocation_response(response)
    
    def parse_invocation_response(self, response):
        # Decode and parse the payload
        response = utils.parse_payload(response)
        if "FunctionError" in response:
            if "Task timed out" in response['Payload']:
                # Find the timeout time
                message = utils.find_expression('(Task timed out .* seconds)', str(response['Payload']))
                # Modify the error message
                message = message.replace("Task", "Function '%s'" % self.aws_lambda.name)
                if (self.aws_lambda.output == outputType.VERBOSE) or (self.aws_lambda.output == outputType.JSON):
                    logging.error({"Error" : json.dumps(message)})
                else:
                    logging.error("Error: %s" % message)
            else:
                print("Error in function response")
                logging.error("Error in function response: %s" % response['Payload'])
            utils.finish_failed_execution()
    
        if self.aws_lambda.is_asynchronous():
            if (self.aws_lambda.output == outputType.VERBOSE):
                logging.info('LambdaOutput', response)
            elif (self.aws_lambda.output == outputType.JSON):
                logging.info('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                             'RequestId' : response['ResponseMetadata']['RequestId']})
            else:
                logging.info("Function '%s' launched correctly" % self.aws_lambda.name)
                print("Function '%s' launched correctly" % self.aws_lambda.name)
        else:
            # Transform the base64 encoded results to something legible
            response = utils.parse_base64_response_values(response)
            # Extract log_group_name and log_stream_name from the payload
            response = utils.parse_log_ids(response)
            if (self.aws_lambda.output == outputType.VERBOSE):
                logging.info('LambdaOutput', response)
            elif (self.aws_lambda.output == outputType.JSON):
                logging.info('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                             'Payload' : response['Payload'],
                                             'LogGroupName' : response['LogGroupName'],
                                             'LogStreamName' : response['LogStreamName'],
                                             'RequestId' : response['ResponseMetadata']['RequestId']})
            else:
                logging.info('SCAR: Request Id: %s' % response['ResponseMetadata']['RequestId'])
                logging.info(response['Payload'])
                print('Request Id: %s' % response['ResponseMetadata']['RequestId'])
                print(response['Payload'])
            
    def process_event_source_calls(self):
        s3_file_list = S3Client().get_s3_file_list(self.aws_lambda.event_source)
        logging.info("Files found: '%s'" % s3_file_list)
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_file = s3_file_list.pop(0)
            response = LambdaClient().launch_request_response_event(self.aws_lambda, s3_file)
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
            lambda s3_file: self.parse_invocation_response(LambdaClient().launch_async_event(s3_file, self.aws_lambda)),
            s3_file_list
        )
        pool.close()    
    
    def parse_lambda_info_json_result(self, function_info):
        name = function_info['Configuration'].get('FunctionName', "-")
        memory = function_info['Configuration'].get('MemorySize', "-")
        timeout = function_info['Configuration'].get('Timeout', "-")
        image_id = function_info['Configuration']['Environment']['Variables'].get('IMAGE_ID', "-")
        return {'Name' : name,
                'Memory' : memory,
                'Timeout' : timeout,
                'Image_id': image_id}
    
    def get_table(self, functions_info):
        headers = ['NAME', 'MEMORY', 'TIME', 'IMAGE_ID']
        table = []
        for function in functions_info:
            table.append([function['Name'],
                          function['Memory'],
                          function['Timeout'],
                          function['Image_id']])
        return tabulate(table, headers)
    
    def parse_ls_response(self, lambda_function_info_list):
        # Create the data structure
        if self.aws_lambda.output == outputType.VERBOSE:
            functions_full_info = []
            [functions_full_info.append(function_info) for function_info in lambda_function_info_list]
            print('LambdaOutput', functions_full_info)
        else:
            functions_parsed_info = []
            for function_info in lambda_function_info_list:
                lambda_info_parsed = self.parse_lambda_info_json_result(function_info)
                functions_parsed_info.append(lambda_info_parsed)
            if self.aws_lambda.output == outputType.JSON:
                print('Functions', functions_parsed_info)
            else:
                print(self.get_table(functions_parsed_info))
    
    def init(self):
        # Call the aws services
        self.create_function()
        self.create_cloudwatch_log_group()
        if self.aws_lambda.event_source:
            self.add_event_source()
        # If preheat is activated, the function is launched at the init step
        if self.aws_lambda.preheat:    
            self.preheat_function()
    
    def run(self):
        if self.aws_lambda.has_event_source():
            self.process_event_source_calls()               
        else:
            self.launch_lambda_instance()
    
    def ls(self):
        # Get the filtered resources from aws
        lambda_function_info_list = LambdaClient().get_all_functions()
        self.parse_ls_response(lambda_function_info_list)
    
    def rm(self):
        if self.aws_lambda.delete_all:
            LambdaClient().delete_all_resources(self.aws_lambda)
        else:
            LambdaClient().delete_resources(self.aws_lambda.name, self.aws_lambda.output)
    
    def log(self):
        try:
            log_client = CloudWatchLogsClient()
            full_msg = ""
            if self.aws_lambda.log_stream_name:
                response = log_client.get_cloudwatch_log_events_by_group_name_and_stream_name(
                    self.aws_lambda.log_group_name,
                    self.aws_lambda.log_stream_name)
                for event in response['events']:
                    full_msg += event['message']
            else:
                response = log_client.get_cloudwatch_log_events_by_group_name(self.aws_lambda.log_group_name)
                data = []
    
                for event in response['events']:
                    data.append((event['message'], event['timestamp']))
    
                while(('nextToken' in response) and response['nextToken']):
                    response = log_client.get_cloudwatch_log_events_by_group_name(self.aws_lambda.log_group_name, response['nextToken'])
                    for event in response['events']:
                        data.append((event['message'], event['timestamp']))
    
                sorted_data = sorted(data, key=lambda time: time[1])
                for sdata in sorted_data:
                    full_msg += sdata[0]
    
            response['completeMessage'] = full_msg
            if self.aws_lambda.request_id:
                print (self.parse_aws_logs(full_msg, self.aws_lambda.request_id))
            else:
                print (full_msg)
    
        except ClientError as ce:
            print(ce)


if __name__ == "__main__":
    logging.info('----------------------------------------------------')
    logging.info('SCAR execution started')
    aws_lambda = AWSLambda()
    aws_lambda.check_config_file()
    scar = Scar(aws_lambda)
    args = CommandParser(scar).parse_arguments()
    aws_lambda.set_attributes(args)
    args.func()
    logging.info('SCAR execution finished')
    logging.info('----------------------------------------------------')   
    
