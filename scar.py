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

import argparse
import base64
import boto3
import botocore
import configparser
import logging
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ReadTimeout
from enum import Enum
from multiprocessing.pool import ThreadPool
from tabulate import tabulate

FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='scar.log', level=logging.INFO, format=FORMAT)
config_file_folder = os.path.expanduser("~") + "/.scar"
config_file_name = "scar.cfg"
config_file_path = config_file_folder + '/' + config_file_name

MAX_CONCURRENT_INVOCATIONS = 1000

class OutputType(Enum):
    VERBOSE = 1
    JSON = 2
    TABLE = 3
    PLAIN_TEXT = 4

class  AWSClient(object):
    
    def __init__(self):
        # Default values
        self.botocore_client_read_timeout = 360
        self.default_aws_region = "us-east-1"
    
    def create_function_name(self, image_id_or_path):
        parsed_id_or_path = image_id_or_path.replace('/', ',,,').replace(':', ',,,').replace('.', ',,,').split(',,,')
        name = 'scar-%s' % '-'.join(parsed_id_or_path)
        i = 1
        while self.find_function_name(name):
            name = 'scar-%s-%s' % ('-'.join(parsed_id_or_path), str(i))
            i += 1
        return name
    
    def check_memory(self, lambda_memory):
        """ Check if the memory introduced by the user is correct.
        If the memory is not specified in 64mb increments,
        transforms the request to the next available increment."""
        if (lambda_memory < 128) or (lambda_memory > 1536):
            raise Exception('Incorrect memory size specified\nPlease, set a value between 128 and 1536.')
        else:
            res = lambda_memory % 64
            if (res == 0):
                return lambda_memory
            else:
                return lambda_memory - res + 64
    
    def check_time(self, lambda_time):
        if (lambda_time <= 0) or (lambda_time > 300):
            raise Exception('Incorrect time specified\nPlease, set a value between 0 and 300.')
        return lambda_time
    
    def get_user_name_or_id(self):
        try:
            user = self.get_iam().get_user()['User']
            return user.get('UserName', user['UserId'])
        except ClientError as ce:
            # If the user doesn't have access rights to IAM
            return Utils().find_expression('(?<=user\/)(\S+)', str(ce))
    
    def get_access_key(self):
        session = boto3.Session()
        credentials = session.get_credentials()
        return credentials.access_key
    
    def get_boto3_client(self, client_name, region=None):
        if region is None:
            region = self.default_aws_region
        boto_config = botocore.config.Config(read_timeout=self.botocore_client_read_timeout)            
        return boto3.client(client_name, region_name=region, config=boto_config)
    
    def get_lambda(self, region=None):
        return self.get_boto3_client('lambda', region)
    
    def get_log(self, region=None):
        return self.get_boto3_client('logs', region)
    
    def get_iam(self, region=None):
        return self.get_boto3_client('iam', region)
    
    def get_resource_groups_tagging_api(self, region=None):
        return self.get_boto3_client('resourcegroupstaggingapi', region)
    
    def get_s3(self, region=None):
        return self.get_boto3_client('s3', region)
    
    def get_s3_file_list(self, bucket_name):
        file_list = []
        result = self.get_s3().list_objects_v2(Bucket=bucket_name, Prefix='input/')
        if 'Contents' in result:
            for content in result['Contents']:
                if content['Key'] and content['Key'] != "input/":
                    file_list.append(content['Key'])
        return file_list
    
    def get_log_events_by_group_name(self, log_group_name, next_token=None):
        try:
            if next_token: 
                return self.get_log().filter_log_events(
                    logGroupName=log_group_name, 
                    nextToken=next_token)
            else:
                return self.get_log().filter_log_events(
                    logGroupName=log_group_name)                
        except ClientError as ce:
            print("Error getting log events")
            logging.error("Error getting log events for log group '%s': %s" % (log_group_name, ce))
            Utils().finish_failed_execution()    
    
    def get_log_events_by_group_name_and_stream_name(self, log_group_name, log_stream_name):
        try:        
            return AWSClient().get_log().get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                startFromHead=True )
        except ClientError as ce:
            print("Error getting log events")
            logging.error("Error getting log events for log group '%s' and log stream name '%s': %s"
                           % (log_group_name, log_stream_name, ce))
            Utils().finish_failed_execution()     
    
    def find_function_name(self, function_name):
        try:
            paginator = self.get_lambda().get_paginator('list_functions')
            for functions in paginator.paginate():
                for lfunction in functions['Functions']:
                    if function_name == lfunction['FunctionName']:
                        return True
            return False
        except ClientError as ce:
            print("Error listing the lambda functions")
            logging.error("Error listing the lambda functions: %s" % ce)
            Utils().finish_failed_execution()
    
    def check_function_name_not_exists(self, function_name):
        if not self.find_function_name(function_name):
            print("Function '%s' doesn't exist." % function_name)
            logging.error("Function '%s' doesn't exist." % function_name)
            Utils().finish_failed_execution()
    
    def check_function_name_exists(self, function_name):
        if self.find_function_name(function_name):
            print("Function name '%s' already used." % function_name)
            logging.error ("Function name '%s' already used." % function_name)
            Utils().finish_failed_execution()
    
    def update_function_timeout(self, function_name, timeout):
        try:
            self.get_lambda().update_function_configuration(FunctionName=function_name,
                                                                   Timeout=self.check_time(timeout))
        except ClientError as ce:
            print("Error updating lambda function timeout")
            logging.error("Error updating lambda function timeout: %s" % ce)
    
    def update_function_memory(self, function_name, memory):
        try:
            self.get_lambda().update_function_configuration(FunctionName=function_name,
                                                                   MemorySize=memory)
        except ClientError as ce:
            print("Error updating lambda function memory")
            logging.error("Error updating lambda function memory: %s" % ce)
    
    def create_function(self, aws_lambda): 
        try:
            logging.info("Creating lambda function.")
            response = self.get_lambda().create_function(FunctionName=aws_lambda.name,
                                                     Runtime=aws_lambda.runtime,
                                                     Role=aws_lambda.role,
                                                     Handler=aws_lambda.handler,
                                                     Code=aws_lambda.code,
                                                     Environment=aws_lambda.environment,
                                                     Description=aws_lambda.description,
                                                     Timeout=aws_lambda.time,
                                                     MemorySize=aws_lambda.memory,
                                                     Tags=aws_lambda.tags)
            aws_lambda.function_arn = response['FunctionArn']
            return response
        except ClientError as ce:
            print("Error creating lambda function")
            logging.error("Error creating lambda function: %s" % ce)        
        
    def create_log_group(self, aws_lambda):
        try:
            logging.info("Creating cloudwatch log group.")
            return self.get_log().create_log_group(logGroupName=aws_lambda.log_group_name,
                                                   tags=aws_lambda.tags)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print("Using existent log group '%s'" % aws_lambda.log_group_name)
                logging.warning("Using existent log group '%s'" % aws_lambda.log_group_name)
                pass
            else:
                logging.error("Error creating log groups: %s" % ce)   
                Utils().finish_failed_execution() 
    
    def set_log_retention_policy(self, aws_lambda):
        try:
            logging.info("Setting log group policy.")
            self.get_log().put_retention_policy(logGroupName=aws_lambda.log_group_name,
                                           retentionInDays=aws_lambda.log_retention_policy_in_days)
        except ClientError as ce:
            print("Error setting log retention policy")
            logging.error("Error setting log retention policy: %s" % ce)    
    
    def get_function_environment_variables(self, function_name):
        return self.get_lambda().get_function(FunctionName=function_name)['Configuration']['Environment']
    
    def update_function_env_variables(self, function_name, env_vars):
        try:
            # Retrieve the global variables already defined
            lambda_env_variables = self.get_function_environment_variables(function_name)
            self.parse_environment_variables(lambda_env_variables, env_vars)
            self.get_lambda().update_function_configuration(FunctionName=function_name,
                                                                    Environment=lambda_env_variables)
        except ClientError as ce:
            print("Error updating the environment variables of the lambda function")
            logging.error("Error updating the environment variables of the lambda function: %s" % ce)
    
    def get_trigger_configuration(self, function_arn, folder_name):
        return { "LambdaFunctionArn": function_arn,
                 "Events": [ "s3:ObjectCreated:*" ],
                 "Filter": { 
                     "Key": { 
                         "FilterRules": [
                             { "Name": "prefix",
                               "Value": folder_name }
                         ]
                     }
                 }}
    
    def put_bucket_notification_configuration(self, bucket_name, notification):
        try:
            self.get_s3().put_bucket_notification_configuration(Bucket=bucket_name,
                                                                NotificationConfiguration=notification)
        except ClientError as ce:
            print("Error configuring S3 bucket")
            logging.error("Error configuring S3 bucket: %s" % ce)
        
    def create_trigger_from_bucket(self, bucket_name, function_arn):
        notification = { "LambdaFunctionConfigurations": [self.get_trigger_configuration(function_arn, "input/")] }
        self.put_bucket_notification_configuration(bucket_name, notification)
            
    def create_recursive_trigger_from_bucket(self, bucket_name, function_arn):
        notification = { "LambdaFunctionConfigurations": [
                            self.get_trigger_configuration(function_arn, "input/"),
                            self.get_trigger_configuration(function_arn, "recursive/")] }
        self.put_bucket_notification_configuration(bucket_name, notification)          
    
    def add_lambda_permissions(self, lambda_name, bucket_name):
        try:
            self.get_lambda().add_permission(FunctionName=lambda_name,
                                             StatementId=str(uuid.uuid4()),
                                             Action="lambda:InvokeFunction",
                                             Principal="s3.amazonaws.com",
                                             SourceArn='arn:aws:s3:::%s' % bucket_name
                                            )
        except ClientError as ce:
            print("Error setting lambda permissions")
            logging.error("Error setting lambda permissions: %s" % ce)
    
    def check_and_create_s3_bucket(self, bucket_name):
        try:
            buckets = self.get_s3().list_buckets()
            # Search for the bucket
            found_bucket = [bucket for bucket in buckets['Buckets'] if bucket['Name'] == bucket_name]
            if not found_bucket:
                # Create the bucket if not found
                self.create_s3_bucket(bucket_name)
            # Add folder structure
            self.add_s3_bucket_folder(bucket_name, "input/")
            self.add_s3_bucket_folder(bucket_name, "output/")
        except ClientError as ce:
            print("Error getting the S3 buckets list")
            logging.error("Error getting the S3 buckets list: %s" % ce)
    
    def create_s3_bucket(self, bucket_name):
        try:
            self.get_s3().create_bucket(ACL='private', Bucket=bucket_name)
        except ClientError as ce:
            print("Error creating the S3 bucket '%s'" % bucket_name)
            logging.error("Error creating the S3 bucket '%s': %s" % (bucket_name, ce))
    
    def add_s3_bucket_folder(self, bucket_name, folder_name):
        try:
            self.get_s3().put_object(Bucket=bucket_name, Key=folder_name)
        except ClientError as ce:
            print("Error creating the S3 bucket '%s' folder '%s'" % (bucket_name, folder_name))
            logging.error("Error creating the S3 bucket '%s' folder '%s': %s" % (bucket_name, folder_name, ce))
    
    def get_functions_arn_list(self):
        arn_list = []
        try:
            # Creation of a function filter by tags
            client = self.get_resource_groups_tagging_api()
            user_id = self.get_user_name_or_id()
            tag_filters = [ { 'Key': 'owner', 'Values': [ user_id ] },
                            { 'Key': 'createdby', 'Values': ['scar'] } ]
            response = client.get_resources(TagFilters=tag_filters,
                                            TagsPerPage=100, 
                                            ResourceTypeFilters=['lambda'])
    
            for function in response['ResourceTagMappingList']:
                arn_list.append(function['ResourceARN'])
    
            while ('PaginationToken' in response) and (response['PaginationToken']):
                response = client.get_resources(PaginationToken=response['PaginationToken'],
                                                TagFilters=tag_filters,
                                                TagsPerPage=100)
                for function in response['ResourceTagMappingList']:
                    arn_list.append(function['ResourceARN'])
        except ClientError as ce:
            print("Error getting function arn by tag")
            logging.error("Error getting function arn by tag: %s" % ce)
        return arn_list
    
    def get_function_info_by_arn(self, function_arn):
        try:
            return self.get_lambda().get_function(FunctionName=function_arn)
        except ClientError as ce:
            print("Error getting function info by arn")
            logging.error("Error getting function info by arn: %s" % ce)
    
    def get_all_functions(self):
        function_list = []
        # Get the filtered resources from AWS
        function_arn_list = self.get_functions_arn_list()
        try:
            for function_arn in function_arn_list:
                function_info = self.get_function_info_by_arn(function_arn)
                function_list.append(function_info)
        except ClientError as ce:
            print("Error getting all functions")
            logging.error("Error getting all functions: %s" % ce)
        return function_list
    
    def delete_lambda_function(self, function_name):
        try:
            # Delete the lambda function
            return self.get_lambda().delete_function(FunctionName=function_name)
        except ClientError as ce:
            print("Error deleting the lambda function")
            logging.error("Error deleting the lambda function: %s" % ce)
    
    def delete_cloudwatch_group(self, function_name):
        try:
            # Delete the cloudwatch log group
            log_group_name = '/aws/lambda/%s' % function_name
            return self.get_log().delete_log_group(logGroupName=log_group_name)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                print("Cannot delete log group '%s'. Group not found." % log_group_name)
                logging.warning("Cannot delete log group '%s'. Group not found." % log_group_name)
            else:
                print("Error deleting the cloudwatch log")
                logging.error("Error deleting the cloudwatch log: %s" % ce)

    def delete_all_resources(self, aws_lambda):
        lambda_functions = self.get_all_functions()
        for function in lambda_functions:
            self.delete_resources(function['Configuration']['FunctionName'], aws_lambda.output)
    
    def parse_delete_function_response(self, function_name, reponse, output_type):
        if output_type == OutputType.VERBOSE:
            logging.info('LambdaOutput', reponse)
        elif output_type == OutputType.JSON:            
            logging.info('LambdaOutput', { 'RequestId' : reponse['ResponseMetadata']['RequestId'],
                                         'HTTPStatusCode' : reponse['ResponseMetadata']['HTTPStatusCode'] })
        else:
            logging.info("Function '%s' successfully deleted." % function_name)
        print("Function '%s' successfully deleted." % function_name)                 
    
    def parse_delete_log_response(self, function_name, response, output_type):
        if response:
            log_group_name = '/aws/lambda/%s' % function_name
            if output_type == OutputType.VERBOSE:
                logging.info('CloudWatchOutput', response)
            elif output_type == OutputType.JSON:            
                logging.info('CloudWatchOutput', { 'RequestId' : response['ResponseMetadata']['RequestId'],
                                                                   'HTTPStatusCode' : response['ResponseMetadata']['HTTPStatusCode'] })
            else:
                logging.info("Log group '%s' successfully deleted." % log_group_name)
            print("Log group '%s' successfully deleted." % log_group_name)
    
    def delete_resources(self, function_name, output_type):
        self.check_function_name_not_exists(function_name)
        delete_function_response = self.delete_lambda_function(function_name)
        self.parse_delete_function_response(function_name, delete_function_response, output_type)
        delete_log_response = self.delete_cloudwatch_group(function_name)
        self.parse_delete_log_response(function_name, delete_log_response, output_type)
    
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
        
    def invoke_lambda_function(self, aws_lambda):
        response = {}
        try:
            response = self.get_lambda().invoke(FunctionName=aws_lambda.name,
                                                InvocationType=aws_lambda.invocation_type,
                                                LogType=aws_lambda.log_type,
                                                Payload=aws_lambda.payload)
        except ClientError as ce:
            print("Error invoking lambda function")
            logging.error("Error invoking lambda function: %s" % ce)
            Utils().finish_failed_execution()
    
        except ReadTimeout as rt:
            print("Timeout reading connection pool")
            logging.error("Timeout reading connection pool: %s" % rt)
            Utils().finish_failed_execution()
        return response    

class AWSLambda(object):

    def __init__(self):
        # Parameters needed to create the function in AWS
        self.asynchronous_call = False
        self.code = None
        self.container_arguments = None
        self.delete_all = False
        self.description = "Automatically generated lambda function"    
        self.environment = { 'Variables' : {} }
        self.event = { "Records" : [
                    { "eventSource" : "aws:s3",
                      "s3" : {
                          "bucket" : {
                              "name" : ""},
                          "object" : {
                              "key" : "" }
                        }
                    }
                ]}
        self.event_source = None
        self.extra_payload = None
        self.function_arn = None
        self.handler = None
        self.image_id = None
        self.invocation_type = "RequestResponse"
        self.log_group_name = None
        self.log_retention_policy_in_days = 30
        self.log_stream_name = None
        self.log_type = "Tail"
        self.memory = 512
        self.name = None
        self.output = OutputType.PLAIN_TEXT
        self.payload = "{}"
        self.recursive = False        
        self.region = 'us-east-1'
        self.request_id = None
        self.role = None
        self.runtime = "python3.6"
        self.scar_call = None
        self.script = None
        self.tags = {}
        self.time = 300
        self.timeout_threshold = 10
        self.udocker_dir = "/tmp/home/.udocker"
        self.udocker_tarball = "/var/task/udocker-1.1.0-RC2.tar.gz"
        self.zip_file_path = os.path.join(tempfile.gettempdir(), 'function.zip')

    def set_log_stream_name(self, stream_name):
        self.log_stream_name = stream_name
        
    def set_request_id(self, request_id):
        self.request_id = request_id
        
    def is_asynchronous(self):
        return self.asynchronous_call

    def has_event_source(self):
        return self.event_source is not None
    
    def delete_all(self):
        return self.delete_all
        
    def has_verbose_output(self):
        return self.verbose_output
    
    def has_json_output(self):
        return self.json_output
        
    def set_payload(self, payload):
        self.payload = json.dumps(payload)
        
    def set_cont_args(self, container_arguments):
        self.container_arguments = container_arguments

    def set_async(self, asynchronous_call):
        if asynchronous_call:
            self.set_asynchronous_call_parameters()
        else:
            self.set_request_response_call_parameters()

    def set_func(self, scar_call):
        self.scar_call = scar_call.__name__

    def set_asynchronous_call_parameters(self):
        self.asynchronous_call = True
        self.invocation_type = "Event"
        self.log_type = "None"

    def set_request_response_call_parameters(self):
        self.asynchronous_call = False
        self.invocation_type = "RequestResponse"
        self.log_type = "Tail"

    def set_name(self, name):
        if not Utils().is_valid_name(name):
            print("'%s' is an invalid lambda function name." % name)
            logging.error("'%s' is an invalid lambda function name." % name)
            Utils().finish_failed_execution()            
        self.name = name        
    
    def set_image_id(self, image_id):
        self.image_id = image_id
        if not hasattr(self, 'name') or self.name == "":
            self.set_name(AWSClient().create_function_name(image_id))
    
    def set_memory(self, memory):
        self.memory = AWSClient().check_memory(memory)        

    def set_time(self, time):
        self.time = AWSClient().check_time(time)
        
    def set_timeout_threshold(self, timeout_threshold):
        self.timeout_threshold = timeout_threshold
        
    def set_json(self, json):
        if json:
            self.output = OutputType.JSON
        
    def set_verbose(self, verbose):
        if verbose:
            self.output = OutputType.VERBOSE
        
    def set_script(self, script):
        self.script = script
        
    def set_event_source(self, event_source):
        self.event_source = event_source
        self.event['Records'][0]['s3']['bucket']['name'] = event_source
        
    def set_event_source_file_name(self, file_name):
        self.event['Records'][0]['s3']['object']['key'] = file_name        
        
    def set_lambda_role(self, lambda_role):
        self.lambda_role = lambda_role
        
    def set_recursive(self, recursive):
        self.recursive = recursive
        
    def set_preheat(self, preheat):
        self.preheat = preheat
        
    def set_extra_payload(self, extra_payload):
        self.extra_payload = extra_payload

    def set_code(self):
        self.code = {"ZipFile": self.create_zip_file()}
        
    def set_evironment_variable(self, key, value):
        self.environment['Variables'][key] = value
               
    def set_required_environment_variables(self):
        self.set_evironment_variable('UDOCKER_DIR', self.udocker_dir)
        self.set_evironment_variable('UDOCKER_TARBALL', self.udocker_tarball)
        self.set_evironment_variable('TIMEOUT_THRESHOLD', str(self.timeout_threshold))
        self.set_evironment_variable('RECURSIVE', str(self.recursive))
        self.set_evironment_variable('IMAGE_ID', self.image_id)        

    def set_environment_variables(self, variables):
        for env_var in variables:
            parsed_env_var = env_var.split("=")
            # Add an specific prefix to be able to find the variables defined by the user
            key = 'CONT_VAR_' + parsed_env_var[0]
            self.set_evironment_variable(key, parsed_env_var[1])

    def set_tags(self):
        self.tags['createdby'] = 'scar'
        self.tags['owner'] = AWSClient().get_user_name_or_id()

    def set_all(self, value):
        self.delete_all = value
          
    def validate_lambda_configuration(self):
        if not self.role or self.role == "":
            logging.error("Please, specify first a lambda role in the '%s/%s' file." % (config_file_folder, config_file_name))
            Utils().finish_failed_execution()

    def get_argument_value(self, args, attr):
        if attr in args.__dict__.keys():
            return args.__dict__[attr]

    def update_function_attributes(self, args):
        if self.get_argument_value(args, 'memory'):
            AWSClient().update_function_memory(self.name, self.memory)
        if self.get_argument_value(args, 'time'):
            AWSClient().update_function_timeout(self.name, self.time)
        if self.get_argument_value(args, 'env'):
            AWSClient().update_function_env_variables(self.name, self.environment)        

    def check_function_name(self):
        if self.name:
            if self.scar_call == 'init':
                AWSClient().check_function_name_exists(self.name)
            elif (self.scar_call == 'rm') or (self.scar_call == 'run'):
                AWSClient().check_function_name_not_exists(self.name)

    def set_attributes(self, args):
        # First set command line attributes
        for attr in args.__dict__.keys():
            value = self.get_argument_value(args, attr)
            try:
                if value is not None:
                    method_name = 'set_' + attr
                    method = getattr(self, method_name)
                    method(value)
            except Exception as ex:
                logging.error(ex)
        
        self.check_function_name()
        self.set_required_environment_variables()
        if self.name:
            self.handler = self.name + ".lambda_handler"
            self.log_group_name = '/aws/lambda/' + self.name
        if self.scar_call == 'init':
            self.set_tags()
            self.set_code()
        elif self.scar_call == 'run':
            self.update_function_attributes(args)
            if self.get_argument_value(args, 'script'):
                self.set_payload(self.create_payload("script", self.get_escaped_script()))
            if self.get_argument_value(args, 'cont_args'):
                self.set_payload(self.create_payload("cmd_args", self.get_parsed_cont_args()))             

    def create_payload(self, key, value):
        return { key : value }

    def get_escaped_script(self):
        return Utils().escape_string(self.script.read())

    def get_parsed_cont_args(self):
        return Utils().escape_list(self.container_arguments)

    def get_default_json_config(self):
        return { 'lambda_description' : self.description,
                 'lambda_memory' : self.memory,
                 'lambda_time' : self.time,
                 'lambda_region' : self.region,
                 'lambda_role' : '',
                 'lambda_timeout_threshold' : self.timeout_threshold }

    def check_config_file(self):
        config_parser = configparser.ConfigParser()
        # Check if the config file exists
        if os.path.isfile(config_file_path):
            config_parser.read(config_file_path)
            self.parse_config_file_values(config_parser)
        else:
            # Create scar config dir
            os.makedirs(config_file_folder, exist_ok=True)
            self.create_default_config_file(config_parser, config_file_path)
        self.validate_lambda_configuration()
    
    def create_default_config_file(self, config_parser, config_file_path):
        config_parser['scar'] = self.get_default_json_config()
        with open(config_file_path, "w") as config_file:
            config_parser.write(config_file)
        logging.warning("Config file '%s' created.\nPlease, set first a valid lambda role to be used." % config_file_path)
        Utils().finish_successful_execution()
    
    def parse_config_file_values(self, config_parser):
        scar_config = config_parser['scar']
        self.role = scar_config.get('lambda_role', self.role)
        self.region = scar_config.get('lambda_region', self.region)
        self.memory = scar_config.getint('lambda_memory', self.memory)
        self.time = scar_config.getint('lambda_time', self.time)
        self.description = scar_config.get('lambda_description', self.description)
        self.timeout_threshold = scar_config.getint('lambda_timeout_threshold', self.timeout_threshold)
        
    def get_scar_abs_path(self):
        return os.path.dirname(os.path.abspath(__file__))
        
    def create_zip_file(self):
        scar_dir = self.get_scar_abs_path()
        # Set generic lambda function name
        function_name = self.name + '.py'
        # Copy file to avoid messing with the repo files
        # We have to rename the file because the function name affects the handler name
        shutil.copy(scar_dir + '/lambda/scarsupervisor.py', function_name)
        # Zip the function file
        with zipfile.ZipFile(self.zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # AWSLambda function code
            zf.write(function_name)
            os.remove(function_name)
            # Udocker script code
            zf.write(scar_dir + '/lambda/udocker', 'udocker')
            # Udocker libs
            zf.write(scar_dir + '/lambda/udocker-1.1.0-RC2.tar.gz', 'udocker-1.1.0-RC2.tar.gz')
    
            if self.script:
                zf.write(self.script, 'init_script.sh')
                self.set_evironment_variable('INIT_SCRIPT_PATH', "/var/task/init_script.sh")
                
        if self.extra_payload:
            self.zip_folder(self.zip_file_path, self.extra_payload)
            self.set_evironment_variable('EXTRA_PAYLOAD', "/var/task/extra/")
    
        # Return the zip as an array of bytes
        with open(self.zip_file_path, 'rb') as f:
            return f.read()
    
    def zip_folder(self, zipPath, target_dir):            
        with zipfile.ZipFile(zipPath, 'a', zipfile.ZIP_DEFLATED) as zf:
            rootlen = len(target_dir) + 1
            for base, _, files in os.walk(target_dir):
                for file in files:
                    fn = os.path.join(base, file)
                    zf.write(fn, 'extra/' + fn[rootlen:])
                  
class CommandParser(object):
    
    def __init__(self, scar):
        self.scar = scar
        self.parser = argparse.ArgumentParser(prog="scar",
                                         description="Deploy containers in serverless architectures",
                                         epilog="Run 'scar COMMAND --help' for more information on a command.")
        self.subparsers = self.parser.add_subparsers(title='Commands')    
        self.create_init_parser()
        self.create_run_parser()
        self.create_rm_parser()
        self.create_ls_parser()
        self.create_log_parser()
    
    def create_init_parser(self):
        parser_init = self.subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.scar.init)
        # Set the positional arguments
        parser_init.add_argument("image_id", help="Container image id (i.e. centos:7)")
        # Set the optional arguments
        parser_init.add_argument("-d", "--description", help="Lambda function description.")
        parser_init.add_argument("-e", "--environment_variables", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_init.add_argument("-tt", "--timeout_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_init.add_argument("-s", "--script", help="Path to the input file passed to the function")
        parser_init.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
        parser_init.add_argument("-lr", "--lambda_role", help="Lambda role used in the management of the functions")
        parser_init.add_argument("-r", "--recursive", help="Launch a recursive lambda function", action="store_true")
        parser_init.add_argument("-p", "--preheat", help="Preheats the function running it once and downloading the necessary container", action="store_true")
        parser_init.add_argument("-ep", "--extra_payload", help="Folder containing files that are going to be added to the payload of the lambda function")
    
    
    def create_run_parser(self):
        parser_run = self.subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=self.scar.run)
        parser_run.add_argument("name", help="Lambda function name")
        parser_run.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_run.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_run.add_argument("-e", "--environment_variables", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_run.add_argument("-a", "--async", help="Tell Scar to wait or not for the lambda function return", action="store_true")
        parser_run.add_argument("-s", "--script", nargs='?', type=argparse.FileType('r'), help="Path to the input file passed to the function")
        parser_run.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_run.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_run.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
        parser_run.add_argument('cont_args', nargs=argparse.REMAINDER, help="Arguments passed to the container.")        
    
            
    def create_rm_parser(self):
        parser_rm = self.subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=self.scar.rm)
        group = parser_rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Delete all lambda functions", action="store_true")
        parser_rm.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_rm.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")  
    
                    
    def create_ls_parser(self):
        parser_ls = self.subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=self.scar.ls)
        parser_ls.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_ls.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
    
            
    def create_log_parser(self):
        parser_log = self.subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=self.scar.log)
        parser_log.add_argument("name", help="Lambda function name")
        parser_log.add_argument("-ls", "--log_stream_name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request_id", help="Return the output for the request id specified.")        
    
    def parse_arguments(self):
        try:
            """Command parsing and selection"""
            return self.parser.parse_args()        
        except AttributeError as ae:
            logging.error("Error parsing arguments: %s" % ae)
            print("Incorrect arguments: use scar -h to see the options available")
            Utils().finish_failed_execution()         
        
class Utils(object):
    
    def is_valid_name(self, function_name):
        if function_name:
            aws_name_regex = "(arn:(aws[a-zA-Z-]*)?:lambda:)?([a-z]{2}(-gov)?-[a-z]+-\d{1}:)?(\d{12}:)?(function:)?([a-zA-Z0-9-_]+)(:(\$LATEST|[a-zA-Z0-9-_]+))?"           
            pattern = re.compile(aws_name_regex)
            func_name = pattern.match(function_name)
            return func_name and (func_name.group() == function_name)
        return False    
    
    def finish_failed_execution(self):
        logging.info('SCAR execution finished with errors')
        logging.info('----------------------------------------------------')
        sys.exit(1)

    
    def finish_successful_execution(self):
        logging.info('SCAR execution finished')
        logging.info('----------------------------------------------------')
        sys.exit(0)
    
    
    def find_expression(self, rgx_pattern, string_to_search):
        '''Returns the first group that matches the rgx_pattern in the string_to_search'''
        pattern = re.compile(rgx_pattern)
        match = pattern.search(string_to_search)
        if match :
            return match.group()
    
    
    def base64_to_utf8(self, value):
        return base64.b64decode(value).decode('utf8')
    
    
    def escape_list(self, values):
        result = []
        for value in values:
            result.append(self.escape_string(value))
        return str(result).replace("'", "\"")
    
    
    def escape_string(self, value):
        value = value.replace("\\", "\\/").replace('\n', '\\n')
        value = value.replace('"', '\\"').replace("\/", "\\/")
        value = value.replace("\b", "\\b").replace("\f", "\\f")
        return value.replace("\r", "\\r").replace("\t", "\\t")
    
    
    def parse_payload(self, value):
        value['Payload'] = value['Payload'].read().decode("utf-8")[1:-1].replace('\\n', '\n')
        return value
    
    
    def parse_base64_response_values(self, value):
        value['LogResult'] = self.base64_to_utf8(value['LogResult'])
        value['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'] = self.base64_to_utf8(value['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'])
        return value
    
    
    def parse_log_ids(self, value):
        parsed_output = value['Payload'].split('\n')
        value['LogGroupName'] = parsed_output[1][22:]
        value['LogStreamName'] = parsed_output[2][23:]
        return value
    
    
    def print_json(self, value):
        print(json.dumps(value))
    
        
    def divide_list_in_chunks(self, elements, chunk_size):
        """Yield successive n-sized chunks from th elements list."""
        if len(elements) == 0:
            yield []
        for i in range(0, len(elements), chunk_size):
            yield elements[i:i + chunk_size]    

class Scar(object):
    
    def __init__(self, aws_lambda):
        self.aws_lambda = aws_lambda
     
    def delete_function_code(self):
        # Remove the zip created in the operation
        os.remove(self.aws_lambda.zip_file_path)        
    
    def parse_lambda_function_creation_response(self, lambda_response):
        if self.aws_lambda.output == OutputType.VERBOSE:
            logging.info('LambdaOutput', lambda_response)
        elif self.aws_lambda.output == OutputType.JSON:
            logging.info('LambdaOutput', {'AccessKey' : AWSClient().get_access_key(),
                                                   'FunctionArn' : lambda_response['FunctionArn'],
                                                   'Timeout' : lambda_response['Timeout'],
                                                   'MemorySize' : lambda_response['MemorySize'],
                                                   'FunctionName' : lambda_response['FunctionName']})
        else:
            print("Function '%s' successfully created." % self.aws_lambda.name)
            logging.info("Function '%s' successfully created." % self.aws_lambda.name)
    
    def parse_log_group_creation_response(self, cw_response):
        if self.aws_lambda.output == OutputType.VERBOSE:
            logging.info('CloudWatchOuput', cw_response)
        if self.aws_lambda.output == OutputType.JSON:
            logging.info('CloudWatchOutput', {'RequestId' : cw_response['ResponseMetadata']['RequestId'],
                                                                'HTTPStatusCode' : cw_response['ResponseMetadata']['HTTPStatusCode']})
        else:
            print("Log group '%s' successfully created." % self.aws_lambda.log_group_name)
            logging.info("Log group '%s' successfully created." % self.aws_lambda.log_group_name)
    
    
    def create_function(self):
        # lambda_validator.validate_function_creation_values(self.aws_lambda)
        try:
            lambda_response = AWSClient().create_function(self.aws_lambda)
            self.parse_lambda_function_creation_response(lambda_response)
        except ClientError as ce:
            logging.error("Error initializing lambda function: %s" % ce)
            Utils().finish_failed_execution()
        finally:
            self.delete_function_code()
    
    
    def create_log_group(self):
        # lambda_validator.validate_log_creation_values(self.aws_lambda)
        cw_response = AWSClient().create_log_group(self.aws_lambda)
        self.parse_log_group_creation_response(cw_response)
        # Set retention policy into the log group
        AWSClient().set_log_retention_policy(self.aws_lambda)
    
        
    def add_event_source(self):
        bucket_name = self.aws_lambda.event_source
        try:
            AWSClient().check_and_create_s3_bucket(bucket_name)
            AWSClient().add_lambda_permissions(self.aws_lambda.name, bucket_name)
            AWSClient().create_trigger_from_bucket(bucket_name, self.aws_lambda.function_arn)
            if self.aws_lambda.recursive:
                AWSClient().add_s3_bucket_folder(bucket_name, "recursive/")
                AWSClient().create_recursive_trigger_from_bucket(bucket_name, self.aws_lambda.function_arn)
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
        response = AWSClient().preheat_function(self.aws_lambda)
        self.parse_invocation_response(response)
    
    
    def launch_lambda_instance(self):
        response = AWSClient().invoke_lambda_function(self.aws_lambda)
        self.parse_invocation_response(response)
    
    
    def parse_invocation_response(self, response):
        # Decode and parse the payload
        response = Utils().parse_payload(response)
        if "FunctionError" in response:
            if "Task timed out" in response['Payload']:
                # Find the timeout time
                message = Utils().find_expression('(Task timed out .* seconds)', str(response['Payload']))
                # Modify the error message
                message = message.replace("Task", "Function '%s'" % self.aws_lambda.name)
                if (self.aws_lambda.output == OutputType.VERBOSE) or (self.aws_lambda.output == OutputType.JSON):
                    logging.error({"Error" : json.dumps(message)})
                else:
                    logging.error("Error: %s" % message)
            else:
                print("Error in function response")
                logging.error("Error in function response: %s" % response['Payload'])
            Utils().finish_failed_execution()
    
        if self.aws_lambda.is_asynchronous():
            if (self.aws_lambda.output == OutputType.VERBOSE):
                logging.info('LambdaOutput', response)
            elif (self.aws_lambda.output == OutputType.JSON):
                logging.info('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                             'RequestId' : response['ResponseMetadata']['RequestId']})
            else:
                logging.info("Function '%s' launched correctly" % self.aws_lambda.name)
                print("Function '%s' launched correctly" % self.aws_lambda.name)
        else:
            # Transform the base64 encoded results to something legible
            response = Utils().parse_base64_response_values(response)
            # Extract log_group_name and log_stream_name from the payload
            response = Utils().parse_log_ids(response)
            if (self.aws_lambda.output == OutputType.VERBOSE):
                logging.info('LambdaOutput', response)
            elif (self.aws_lambda.output == OutputType.JSON):
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
        s3_file_list = AWSClient().get_s3_file_list(self.aws_lambda.event_source)
        logging.info("Files found: '%s'" % s3_file_list)
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_file = s3_file_list.pop(0)
            response = AWSClient().launch_request_response_event(self.aws_lambda, s3_file)
            self.parse_invocation_response(response)
        # If the list has more elements, invoke functions asynchronously    
        if s3_file_list:
            self.process_asynchronous_lambda_invocations(s3_file_list)      
    
     
    def process_asynchronous_lambda_invocations(self, s3_file_list):
        size = len(s3_file_list)
        if size > MAX_CONCURRENT_INVOCATIONS:
            s3_file_chunk_list = Utils().divide_list_in_chunks(s3_file_list, MAX_CONCURRENT_INVOCATIONS)
            for s3_file_chunk in s3_file_chunk_list:
                self.launch_concurrent_lambda_invocations(s3_file_chunk)
        else:
            self.launch_concurrent_lambda_invocations(s3_file_list)
    
    
    def launch_concurrent_lambda_invocations(self, s3_file_list):
        pool = ThreadPool(processes=len(s3_file_list))
        pool.map(
            lambda s3_file: self.parse_invocation_response(AWSClient().launch_async_event(s3_file, self.aws_lambda)),
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
        if self.aws_lambda.output == OutputType.VERBOSE:
            functions_full_info = []
            [functions_full_info.append(function_info) for function_info in lambda_function_info_list]
            print('LambdaOutput', functions_full_info)
        else:
            functions_parsed_info = []
            for function_info in lambda_function_info_list:
                lambda_info_parsed = self.parse_lambda_info_json_result(function_info)
                functions_parsed_info.append(lambda_info_parsed)
            if self.aws_lambda.output == OutputType.JSON:
                print('Functions', functions_parsed_info)
            else:
                print(self.get_table(functions_parsed_info))
    
    
    def init(self):
        # Call the AWS services
        self.create_function()
        self.create_log_group()
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
        # Get the filtered resources from AWS
        lambda_function_info_list = AWSClient().get_all_functions()
        self.parse_ls_response(lambda_function_info_list)
    
    
    def rm(self):
        if self.aws_lambda.delete_all:
            AWSClient().delete_all_resources(self.aws_lambda)
        else:
            AWSClient().delete_resources(self.aws_lambda.name, self.aws_lambda.output)
    
    
    def log(self):
        try:
            full_msg = ""
            if self.aws_lambda.log_stream_name:
                response = AWSClient().get_log_events_by_group_name_and_stream_name(
                    self.aws_lambda.log_group_name,
                    self.aws_lambda.log_stream_name )
                for event in response['events']:
                    full_msg += event['message']
            else:
                response = AWSClient().get_log_events_by_group_name(self.aws_lambda.log_group_name)
                data = []
    
                for event in response['events']:
                    data.append((event['message'], event['timestamp']))
    
                while(('nextToken' in response) and response['nextToken']):
                    response = AWSClient().get_log_events_by_group_name(self.aws_lambda.log_group_name, response['nextToken'])
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
    
