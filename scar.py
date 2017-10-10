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
import json
import os
import re
import shutil
import sys
import uuid
import zipfile
from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ReadTimeout
from multiprocessing.pool import ThreadPool
from tabulate import tabulate

class Scar(object):
    """Implements most of the command line interface.
    These methods correspond directly to the commands that can
    be invoked via the command line interface.
    """

    def init(self, args):
        # Set lambda name
        if not args.name:
            Config.lambda_name = StringUtils().create_image_based_name(args.image_id)
        else:
            Config.lambda_name = args.name
        # Validate function name
        if not StringUtils().validate_function_name(Config.lambda_name):
            if args.verbose or args.json:
                StringUtils().print_json({"Error" : "Function name '%s' is not valid." % Config.lambda_name})
            else:
                print ("Error: Function name '%s' is not valid." % Config.lambda_name)
            sys.exit(1)
        aws_client = self.get_aws_client()
        # Check if function exists
        aws_client.check_function_name_exists(Config.lambda_name, (True if args.verbose or args.json else False))
        # Set the rest of the parameters
        Config.lambda_handler = Config.lambda_name + ".lambda_handler"
        if args.script:
            Config.lambda_zip_file = {"ZipFile": self.create_zip_file(Config.lambda_name, args.script)}
            Config.lambda_env_variables['Variables']['INIT_SCRIPT_PATH'] = "/var/task/init_script.sh"
        else:
            Config.lambda_zip_file = {"ZipFile": self.create_zip_file(Config.lambda_name)}
        if args.memory:
            Config.lambda_memory = aws_client.check_memory(args.memory)
        if args.time:
            Config.lambda_time = aws_client.check_time(args.time)
        if args.description:
            Config.lambda_description = args.description
        if args.image_id:
            Config.lambda_env_variables['Variables']['IMAGE_ID'] = args.image_id
        if args.lambda_role:
            Config.lambda_role = args.lambda_role
        if args.time_threshold:
            Config.lambda_env_variables['Variables']['TIME_THRESHOLD'] = str(args.time_threshold)
        else:
            Config.lambda_env_variables['Variables']['TIME_THRESHOLD'] = str(Config.lambda_timeout_threshold)
        if args.recursive:        
            Config.lambda_env_variables['Variables']['RECURSIVE'] = str(True)            
        # Modify environment vars if necessary
        if args.env:
            StringUtils().parse_environment_variables(args.env)
        # Update lambda tags
        Config.lambda_tags['owner'] = aws_client.get_user_name_or_id()

        # Call the AWS service
        result = Result()
        function_arn = ""
        try:
            lambda_response = aws_client.get_lambda().create_function(FunctionName=Config.lambda_name,
                                                         Runtime=Config.lambda_runtime,
                                                         Role=Config.lambda_role,
                                                         Handler=Config.lambda_handler,
                                                         Code=Config.lambda_zip_file,
                                                         Environment=Config.lambda_env_variables,
                                                         Description=Config.lambda_description,
                                                         Timeout=Config.lambda_time,
                                                         MemorySize=Config.lambda_memory,
                                                         Tags=Config.lambda_tags)
            # Parse results
            function_arn = lambda_response['FunctionArn']
            result.append_to_verbose('LambdaOutput', lambda_response)
            result.append_to_json('LambdaOutput', {'AccessKey' : aws_client.get_access_key(),
                                                   'FunctionArn' : lambda_response['FunctionArn'],
                                                   'Timeout' : lambda_response['Timeout'],
                                                   'MemorySize' : lambda_response['MemorySize'],
                                                   'FunctionName' : lambda_response['FunctionName']})
            result.append_to_plain_text("Function '%s' successfully created." % Config.lambda_name)

        except ClientError as ce:
            print ("Error initializing lambda function: %s" % ce)
            sys.exit(1)
        finally:
            # Remove the zip created in the operation
            os.remove(Config.zif_file_path)

        # Create log group
        log_group_name = '/aws/lambda/' + Config.lambda_name
        try:
            cw_response = aws_client.get_log().create_log_group(
                logGroupName=log_group_name,
                tags={ 'owner' : aws_client.get_user_name_or_id(),
                       'createdby' : 'scar' }
            )
            # Parse results
            result.append_to_verbose('CloudWatchOuput', cw_response)
            result.append_to_json('CloudWatchOutput', {'RequestId' : cw_response['ResponseMetadata']['RequestId'],
                                                       'HTTPStatusCode' : cw_response['ResponseMetadata']['HTTPStatusCode']})
            result.append_to_plain_text("Log group '/aws/lambda/%s' successfully created." % Config.lambda_name)

        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                result.add_warning_message("Using existent log group '%s'" % log_group_name)
            else:
                print ("Error creating log groups: %s" % ce)
        # Set retention policy into the log group
        try:
            aws_client.get_log().put_retention_policy(logGroupName=log_group_name,
                                                        retentionInDays=30)
        except ClientError as ce:
            print ("Error setting log retention policy: %s" % ce)

        # Add even source to lambda function
        if args.event_source:
            try:
                aws_client.check_and_create_s3_bucket(args.event_source)
                aws_client.add_lambda_permissions(args.event_source)
                aws_client.create_trigger_from_bucket(args.event_source, function_arn)
            except ClientError as ce:
                print ("Error creating the event source: %s" % ce)

        # Show results
        result.print_results(json=args.json, verbose=args.verbose)

    def ls(self, args):
        try:
            aws_client = self.get_aws_client()
            result = Result()
            # Get the filtered resources from AWS
            lambda_functions = aws_client.get_all_functions()
            # Create the data structure
            functions_parsed_info = []
            functions_full_info = []
            for lambda_function in lambda_functions:
                parsed_function = {'Name' : lambda_function['Configuration']['FunctionName'],
                            'Memory' : lambda_function['Configuration']['MemorySize'],
                            'Timeout' : lambda_function['Configuration']['Timeout'],
                            'Image_id': lambda_function['Configuration']['Environment']['Variables']['IMAGE_ID']}
                functions_full_info.append(lambda_function)
                functions_parsed_info.append(parsed_function)

            result.append_to_verbose('LambdaOutput', functions_full_info)
            result.append_to_json('Functions', functions_parsed_info)

            # Parse output
            if args.verbose:
                result.print_verbose_result()
            elif args.json:
                result.print_json_result()
            else:
                result.generate_table(functions_parsed_info)

        except ClientError as ce:
            print ("Error listing the resources: %s" % ce)


    def run(self, args):
        aws_client = self.get_aws_client()
        # Check if function not exists
        aws_client.check_function_name_not_exists(args.name, (True if args.verbose or args.json else False))
        # Set call parameters
        invocation_type = 'RequestResponse'
        log_type = 'Tail'
        if args.async:
            invocation_type = 'Event'
            log_type = 'None'
        # Modify memory if necessary
        if args.memory:
            aws_client.update_function_memory(args.name, args.memory)
        # Modify timeout if necessary
        if args.time:
            aws_client.update_function_timeout(args.name, args.time)
        # Modify environment vars if necessary
        if args.env:
            aws_client.update_function_env_variables(args.name, args.env)
            
        payload = {}
        # Parse the function script
        if args.script:
            payload = { "script" : StringUtils().escape_string(args.script.read()) }
        # Or parse the container arguments
        elif args.cont_args:
            payload = { "cmd_args" : StringUtils().escape_list(args.cont_args) }

        # Use the event source to launch the function
        if args.event_source:
            event = Config.lambda_event
            event['Records'][0]['s3']['bucket']['name'] = args.event_source
            s3_files = aws_client.get_s3_file_list(args.event_source)
            print("Files found: '%s'" % s3_files)

            if len(s3_files) >= 1:
                self.launch_request_response_event(s3_files[0], event, aws_client, args)

            if len(s3_files) > 1:
                s3_files = s3_files[1:]
                size = len(s3_files)

                chunk_size = 1000
                if size > chunk_size:
                    s3_file_chunks = self.chunks(s3_files, chunk_size)
                    for s3_file_chunk in s3_file_chunks:
                        pool = ThreadPool(processes=len(s3_file_chunk))
                        pool.map(
                            lambda s3_file: self.launch_async_event(s3_file, event, aws_client, args),
                            s3_file_chunk
                        )
                        pool.close()
                else:
                    pool = ThreadPool(processes=len(s3_files))
                    pool.map(
                        lambda s3_file: self.launch_async_event(s3_file, event, aws_client, args),
                        s3_files
                    )
                    pool.close()
        else:
            response = aws_client.invoke_function(args.name, invocation_type, log_type, json.dumps(payload))
            self.parse_run_response(response, args.name, args.async, args.json, args.verbose)

    def chunks(self, elements, chunk_size):
        """Yield successive n-sized chunks from list."""
        if len(elements) == 0:
            yield []
        for i in range(0, len(elements), chunk_size):
            yield elements[i:i + chunk_size]

    def launch_generic_event(self, s3_file, event, aws_client, args, async, invocation_type, log_type):
        event['Records'][0]['s3']['object']['key'] = s3_file
        payload = json.dumps(event)
        print("Sending event for file '%s'" % s3_file)
        response = aws_client.invoke_function(args.name, invocation_type, log_type, payload)
        self.parse_run_response(response, args.name, async, args.json, args.verbose)

    def launch_request_response_event(self, s3_file, event, aws_client, args):
        self.launch_generic_event(s3_file, event, aws_client, args, False, 'RequestResponse', 'Tail')

    def launch_async_event(self, s3_file, event, aws_client, args):
        self.launch_generic_event(s3_file, event, aws_client, args, True, 'Event', 'None')

    def parse_run_response(self, response, function_name, async, json, verbose):
        # Decode and parse the payload
        response = StringUtils().parse_payload(response)
        if "FunctionError" in response:
            if "Task timed out" in response['Payload']:
                # Find the timeout time
                message = StringUtils().find_expression('(Task timed out .* seconds)', str(response['Payload']))
                # Modify the error message
                message = message.replace("Task", "Function '%s'" % function_name)
                if verbose or json:
                    StringUtils().print_json({"Error" : message})
                else:
                    print ("Error: %s" % message)
            else:
                print ("Error in function response: %s" % response['Payload'])
            sys.exit(1)


        result = Result()
        if async:
            # Prepare the outputs
            result.append_to_verbose('LambdaOutput', response)
            result.append_to_json('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                                       'RequestId' : response['ResponseMetadata']['RequestId']})
            result.append_to_plain_text("Function '%s' launched correctly" % function_name)

        else:
            # Transform the base64 encoded results to something legible
            response = StringUtils().parse_base64_response_values(response)
            # Extract log_group_name and log_stream_name from the payload
            response = StringUtils().parse_log_ids(response)
            # Prepare the outputs
            result.append_to_verbose('LambdaOutput', response)
            result.append_to_json('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                                   'Payload' : response['Payload'],
                                                   'LogGroupName' : response['LogGroupName'],
                                                   'LogStreamName' : response['LogStreamName'],
                                                   'RequestId' : response['ResponseMetadata']['RequestId']})

            result.append_to_plain_text('SCAR: Request Id: %s' % response['ResponseMetadata']['RequestId'])
            result.append_to_plain_text(response['Payload'])

        # Show results
        result.print_results(json=json, verbose=verbose)

    def rm(self, args):
        aws_client = self.get_aws_client()
        if args.all:
            lambda_functions = aws_client.get_all_functions()
            for function in lambda_functions:
                aws_client.delete_resources(function['Configuration']['FunctionName'], args.json, args.verbose)
        else:
            aws_client.delete_resources(args.name, args.json, args.verbose)

    def create_zip_file(self, file_name, script_path=None):
        # Set generic lambda function name
        function_name = file_name + '.py'
        # Copy file to avoid messing with the repo files
        # We have to rename because the function name afects the handler name
        shutil.copy(Config.dir_path + '/lambda/scarsupervisor.py', function_name)
        # Zip the function file
        with zipfile.ZipFile(Config.zif_file_path, 'w') as zf:
            # Lambda function code
            zf.write(function_name)
            # Udocker script code
            zf.write(Config.dir_path + '/lambda/udocker', 'udocker')
            # Udocker libs
            zf.write(Config.dir_path + '/lambda/udocker-1.1.0-RC2.tar.gz', 'udocker-1.1.0-RC2.tar.gz')
            os.remove(function_name)
            if script_path:
                zf.write(script_path, 'init_script.sh')
        # Return the zip as an array of bytes
        with open(Config.zif_file_path, 'rb') as f:
            return f.read()

    def log(self, args):
        try:
            log_group_name = "/aws/lambda/%s" % args.name
            full_msg = ""
            if args.log_stream_name:
                response = self.get_aws_client().get_log().get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=args.log_stream_name,
                    startFromHead=True
                )
                for event in response['events']:
                    full_msg += event['message']
            else:
                response = self.get_aws_client().get_log().filter_log_events(logGroupName=log_group_name)
                data = []

                for event in response['events']:
                    data.append((event['message'], event['timestamp']))

                while(('nextToken' in response) and response['nextToken']):
                    response = self.get_aws_client().get_log().filter_log_events(logGroupName=log_group_name,
                                                                                 nextToken=response['nextToken'])
                    for event in response['events']:
                        data.append((event['message'], event['timestamp']))

                sorted_data = sorted(data, key=lambda time: time[1])
                for sdata in sorted_data:
                    full_msg += sdata[0]

            response['completeMessage'] = full_msg
            if args.request_id:
                print (self.parse_aws_logs(full_msg, args.request_id))
            else:
                print (full_msg)

        except ClientError as ce:
            print(ce)

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

    def get_aws_client(self):
        return AwsClient()

class StringUtils(object):

    def create_image_based_name(self, image_id):
        parsed_id = image_id.replace('/', ',,,').replace(':', ',,,').replace('.', ',,,').split(',,,')
        name = 'scar-%s' % '-'.join(parsed_id)
        i = 1
        while AwsClient().find_function_name(name):
            name = 'scar-%s-%s' % ('-'.join(parsed_id), str(i))
            i = i + 1
        return name

    def validate_function_name(self, name):
        aws_name_regex = "((arn:(aws|aws-us-gov):lambda:)?([a-z]{2}(-gov)?-[a-z]+-\d{1}:)?(\d{12}:)?(function:)?([a-zA-Z0-9-]+)(:($LATEST|[a-zA-Z0-9-]+))?)"
        pattern = re.compile(aws_name_regex)
        func_name = pattern.match(name)
        return func_name and (func_name.group() == name)

    def find_expression(self, rgx_pattern, string_to_search):
        '''Returns the first group that matches the rgx_pattern in the string_to_search'''
        pattern = re.compile(rgx_pattern)
        match = pattern.search(string_to_search)
        if  match :
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

    def parse_environment_variables(self, env_vars):
        for var in env_vars:
            var_parsed = var.split("=")
            # Add an specific prefix to be able to find the variables defined by the user
            Config.lambda_env_variables['Variables']['CONT_VAR_' + var_parsed[0]] = var_parsed[1]

class Config(object):

    lambda_name = ""
    lambda_runtime = "python3.6"
    lambda_handler = lambda_name + ".lambda_handler"
    lambda_role = ""
    lambda_region = 'us-east-1'
    lambda_env_variables = {"Variables" : {"UDOCKER_DIR":"/tmp/home/.udocker",
                                           "UDOCKER_TARBALL":"/var/task/udocker-1.1.0-RC2.tar.gz"}}
    lambda_memory = 128
    lambda_time = 300
    lambda_timeout_threshold = 10
    lambda_description = "Automatically generated lambda function"
    lambda_tags = { 'createdby' : 'scar' }

    lambda_event = { "Records" : [
                        { "eventSource" : "aws:s3",
                          "s3" : {
                              "bucket" : {
                                  "name" : ""},
                              "object" : {
                                  "key" : "" }
                            }
                        }
                    ]}

    version = "v1.0.0"
    botocore_client_read_timeout=360

    dir_path = os.path.dirname(os.path.realpath(__file__))

    zif_file_path = dir_path + '/function.zip'

    config_parser = configparser.ConfigParser()

    def create_config_file(self, file_dir):

        self.config_parser['scar'] = {'lambda_description' : "Automatically generated lambda function",
                          'lambda_memory' : Config.lambda_memory,
                          'lambda_time' : Config.lambda_time,
                          'lambda_region' : 'us-east-1',
                          'lambda_role' : '',
                          'lambda_timeout_threshold' : Config.lambda_timeout_threshold}
        with open(file_dir + "/scar.cfg", "w") as configfile:
            self.config_parser.write(configfile)

        print ("Config file %s/scar.cfg created.\nPlease, set first a valid lambda role to be used." % file_dir)
        sys.exit(0)

    def check_config_file(self):
        scar_dir = os.path.expanduser("~") + "/.scar"
        # Check if the scar directory exists
        if os.path.isdir(scar_dir):
            # Check if the config file exists
            if os.path.isfile(scar_dir + "/scar.cfg"):
                self.config_parser.read(scar_dir + "/scar.cfg")
                self.parse_config_file_values()
            else:
                self.create_config_file(scar_dir)
        else:
            # Create scar dir
            os.makedirs(scar_dir)
            self.create_config_file(scar_dir)


    def parse_config_file_values(self):
        scar_config = Config.config_parser['scar']
        Config.lambda_role = scar_config.get('lambda_role', fallback=Config.lambda_role)
        if not Config.lambda_role or Config.lambda_role == "":
            print ("Please, specify first a lambda role in the ~/.scar/scar.cfg file.")
            sys.exit(1)
        Config.lambda_region = scar_config.get('lambda_region', fallback=Config.lambda_region)
        Config.lambda_memory = scar_config.getint('lambda_memory', fallback=Config.lambda_memory)
        Config.lambda_time = scar_config.getint('lambda_time', fallback=Config.lambda_time)
        Config.lambda_description = scar_config.get('lambda_description', fallback=Config.lambda_description)
        Config.lambda_timeout_threshold = scar_config.get('lambda_timeout_threshold', fallback=Config.lambda_timeout_threshold)

class AwsClient(object):

    def check_memory(self, lambda_memory):
        """ Check if the memory introduced by the user is correct.
        If the memory is not specified in 64mb increments,
        transforms the request to the next available increment."""
        if (lambda_memory < 128) or (lambda_memory > 1536):
            raise Exception('Incorrect memory size specified')
        else:
            res = lambda_memory % 64
            if (res == 0):
                return lambda_memory
            else:
                return lambda_memory - res + 64

    def check_time(self, lambda_time):
        if (lambda_time <= 0) or (lambda_time > 300):
            raise Exception('Incorrect time specified')
        return lambda_time

    def get_user_name_or_id(self):
        try:
            user = self.get_iam().get_user()['User']
            return user.get('UserName', user['UserId'])
        except ClientError as ce:
            # If the user doesn't have access rights to IAM
            return StringUtils().find_expression('(?<=user\/)(\S+)', str(ce))

    def get_access_key(self):
        session = boto3.Session()
        credentials = session.get_credentials()
        return credentials.access_key

    def get_boto3_client(self, client_name, region=None):
        if region is None:
            region = Config.lambda_region
        config = botocore.config.Config(read_timeout=Config.botocore_client_read_timeout)            
        return boto3.client(client_name, region_name=region, config=config)

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

    def find_function_name(self, function_name):
        try:
            paginator = AwsClient().get_lambda().get_paginator('list_functions')
            for functions in paginator.paginate():
                for lfunction in functions['Functions']:
                    if function_name == lfunction['FunctionName']:
                        return True
            return False
        except ClientError as ce:
            print ("Error listing the lambda functions: %s" % ce)
            sys.exit(1)

    def check_function_name_not_exists(self, function_name, json):
        if not self.find_function_name(function_name):
            if json:
                StringUtils().print_json({"Error" : "Function '%s' doesn't exist." % function_name})
            else:
                print("Error: Function '%s' doesn't exist." % function_name)
            sys.exit(1)

    def check_function_name_exists(self, function_name, json):
        if self.find_function_name(function_name):
            if json:
                StringUtils().print_json({"Error" : "Function '%s' already exists." % function_name})
            else:
                print ("Error: Function '%s' already exists." % function_name)
            sys.exit(1)

    def update_function_timeout(self, function_name, timeout):
        try:
            self.get_lambda().update_function_configuration(FunctionName=function_name,
                                                                   Timeout=self.check_time(timeout))
        except ClientError as ce:
            print ("Error updating lambda function timeout: %s" % ce)

    def update_function_memory(self, function_name, memory):
        try:
            self.get_lambda().update_function_configuration(FunctionName=function_name,
                                                                   MemorySize=self.check_memory(memory))
        except ClientError as ce:
            print ("Error updating lambda function memory: %s" % ce)

    def get_function_environment_variables(self, function_name):
        return self.get_lambda().get_function(FunctionName=function_name)['Configuration']['Environment']

    def update_function_env_variables(self, function_name, env_vars):
        try:
            # Retrieve the global variables already defined
            Config.lambda_env_variables = self.get_function_environment_variables(function_name)
            StringUtils().parse_environment_variables(env_vars)
            self.get_lambda().update_function_configuration(FunctionName=function_name,
                                                                    Environment=Config.lambda_env_variables)
        except ClientError as ce:
            print ("Error updating the environment variables of the lambda function: %s" % ce)

    def create_trigger_from_bucket(self, bucket_name, function_arn):
        notification = { "LambdaFunctionConfigurations": [
                            { "Id": "string",
                              "LambdaFunctionArn": function_arn,
                              "Events": [ "s3:ObjectCreated:*" ],
                              "Filter":
                                { "Key":
                                    { "FilterRules": [
                                        { "Name": "prefix",
                                          "Value": "input/"
                                        }]
                                    }
                                }
                            }]
                        }
        try:
            self.get_s3().put_bucket_notification_configuration( Bucket=bucket_name,
                                                                 NotificationConfiguration=notification )

        except ClientError as ce:
            print ("Error configuring S3 bucket: %s" % ce)

    def add_lambda_permissions(self, bucket_name):
        try:
            self.get_lambda().add_permission(FunctionName=Config.lambda_name,
                                             StatementId=str(uuid.uuid4()),
                                             Action="lambda:InvokeFunction",
                                             Principal="s3.amazonaws.com",
                                             SourceArn='arn:aws:s3:::%s' % bucket_name
                                            )
        except ClientError as ce:
            print ("Error setting lambda permissions: %s" % ce)

    def check_and_create_s3_bucket(self, bucket_name):
        try:
            buckets = self.get_s3().list_buckets()
            # Search for the bucket
            found_bucket = [bucket for bucket in buckets['Buckets'] if bucket['Name'] == bucket_name]
            if not found_bucket:
                # Create the bucket if not found
                self.create_s3_bucket(bucket_name)
            # Add folder structure
            self.add_s3_bucket_folders(bucket_name)
        except ClientError as ce:
            print ("Error getting the S3 buckets list: %s" % ce)

    def create_s3_bucket(self, bucket_name):
        try:
            self.get_s3().create_bucket(ACL='private', Bucket=bucket_name)
        except ClientError as ce:
            print ("Error creating the S3 bucket '%s': %s" % (bucket_name, ce))

    def add_s3_bucket_folders(self, bucket_name):
        try:
            self.get_s3().put_object(Bucket=bucket_name, Key="input/")
            self.get_s3().put_object(Bucket=bucket_name, Key="output/")
        except ClientError as ce:
            print ("Error creating the S3 bucket '%s' folders: %s" % (bucket_name, ce))

    def get_functions_arn_list(self):
        arn_list = []
        try:
            # Creation of a function filter by tags
            client = self.get_resource_groups_tagging_api()
            tag_filters = [ { 'Key': 'owner', 'Values': [ self.get_user_name_or_id() ] },
                            { 'Key': 'createdby', 'Values': ['scar'] } ]
            response = client.get_resources(TagFilters=tag_filters,
                                                 TagsPerPage=100)

            for function in response['ResourceTagMappingList']:
                arn_list.append(function['ResourceARN'])

            while ('PaginationToken' in response) and (response['PaginationToken']):
                response = client.get_resources(PaginationToken=response['PaginationToken'],
                                                TagFilters=tag_filters,
                                                TagsPerPage=100)
                for function in response['ResourceTagMappingList']:
                    arn_list.append(function['ResourceARN'])

        except ClientError as ce:
            print ("Error getting function arn by tag: %s" % ce)

        return arn_list

    def get_all_functions(self):
        function_list = []
        # Get the filtered resources from AWS
        functions_arn = self.get_functions_arn_list()
        try:
            for function_arn in functions_arn:
                function_list.append(self.get_lambda().get_function(FunctionName=function_arn))
        except ClientError as ce:
            print ("Error getting function info by arn: %s" % ce)
        return function_list

    def delete_lambda_function(self, function_name, result):
        try:
            # Delete the lambda function
            lambda_response = self.get_lambda().delete_function(FunctionName=function_name)
            result.append_to_verbose('LambdaOutput', lambda_response)
            result.append_to_json('LambdaOutput', { 'RequestId' : lambda_response['ResponseMetadata']['RequestId'],
                                         'HTTPStatusCode' : lambda_response['ResponseMetadata']['HTTPStatusCode'] })
            result.append_to_plain_text("Function '%s' successfully deleted." % function_name)
        except ClientError as ce:
            print ("Error deleting the lambda function: %s" % ce)

    def delete_cloudwatch_group(self, function_name, result):
        try:
            # Delete the cloudwatch log group
            log_group_name = '/aws/lambda/%s' % function_name
            cw_response = self.get_log().delete_log_group(logGroupName=log_group_name)
            result.append_to_verbose('CloudWatchOutput', cw_response)
            result.append_to_json('CloudWatchOutput', { 'RequestId' : cw_response['ResponseMetadata']['RequestId'],
                                             'HTTPStatusCode' : cw_response['ResponseMetadata']['HTTPStatusCode'] })
            result.append_to_plain_text("Log group '%s' successfully deleted." % function_name)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                result.add_warning_message("Cannot delete log group '%s'. Group not found." % log_group_name)
            else:
                print ("Error deleting the cloudwatch log: %s" % ce)

    def delete_resources(self, function_name, json, verbose):
        result = Result()
        self.check_function_name_not_exists(function_name, json or verbose)
        self.delete_lambda_function(function_name, result)
        self.delete_cloudwatch_group(function_name, result)
        # Show results
        result.print_results(json, verbose)

    def invoke_function(self, function_name, invocation_type, log_type, payload):
        response = {}
        try:
            response = self.get_lambda().invoke(FunctionName=function_name,
                                                InvocationType=invocation_type,
                                                LogType=log_type,
                                                Payload=payload)
        except ClientError as ce:
            print ("Error invoking lambda function: %s" % ce)
            sys.exit(1)

        except ReadTimeout as rt:
            print ("Timeout reading connection pool: %s" % rt)
            sys.exit(1)
        return response

class Result(object):

    def __init__(self):
        self.verbose = {}
        self.json = {}
        self.plain_text = ""

    def append_to_verbose(self, key, value):
        self.verbose[key] = value

    def append_to_json(self, key, value):
        self.json[key] = value

    def append_to_plain_text(self, value):
        self.plain_text += value + "\n"

    def print_verbose_result(self):
        print(json.dumps(self.verbose))

    def print_json_result(self):
        print(json.dumps(self.json))

    def print_plain_text_result(self):
        print(self.plain_text)

    def print_results(self, json=False, verbose=False):
        # Verbose output has precedence against json output
        if verbose:
            self.print_verbose_result()
        elif json:
            self.print_json_result()
        else:
            self.print_plain_text_result()

    def generate_table(self, functions_info):
        headers = ['NAME', 'MEMORY', 'TIME', 'IMAGE_ID']
        table = []
        for function in functions_info:
            table.append([function['Name'],
                          function['Memory'],
                          function['Timeout'],
                          function['Image_id']])
        print (tabulate(table, headers))

    def add_warning_message(self, message):
        self.append_to_verbose('Warning', message)
        self.append_to_json('Warning', message)
        self.append_to_plain_text ("Warning: %s" % message)

class CmdParser(object):

    def __init__(self):
        scar = Scar()
        self.parser = argparse.ArgumentParser(prog="scar",
                                              description="Deploy containers in serverless architectures",
                                              epilog="Run 'scar COMMAND --help' for more information on a command.")
        subparsers = self.parser.add_subparsers(title='Commands')

        # Create the parser for the 'version' command
        self.parser.add_argument('--version', action='version', version='%(prog)s ' + Config.version)

        # 'init' command
        parser_init = subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=scar.init)
        # Set the positional arguments
        parser_init.add_argument("image_id", help="Container image id (i.e. centos:7)")
        # Set the optional arguments
        parser_init.add_argument("-d", "--description", help="Lambda function description.")
        parser_init.add_argument("-e", "--env", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_init.add_argument("-tt", "--time_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_init.add_argument("-s", "--script", help="Path to the input file passed to the function")
        parser_init.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
        parser_init.add_argument("-lr", "--lambda_role", help="Lambda role used in the management of the functions")
        parser_init.add_argument("-r", "--recursive", help="Launch a recursive lambda function", action="store_true")

        # 'ls' command
        parser_ls = subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=scar.ls)
        parser_ls.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_ls.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")

        # 'run' command
        parser_run = subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=scar.run)
        parser_run.add_argument("name", help="Lambda function name")
        parser_run.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_run.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_run.add_argument("-e", "--env", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_run.add_argument("--async", help="Tell Scar to wait or not for the lambda function return", action="store_true")
        parser_run.add_argument("-s", "--script", nargs='?', type=argparse.FileType('r'), help="Path to the input file passed to the function")
        parser_run.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_run.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_run.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
        parser_run.add_argument('cont_args', nargs=argparse.REMAINDER, help="Arguments passed to the container.")

        # Create the parser for the 'rm' command
        parser_rm = subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=scar.rm)
        group = parser_rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Delete all lambda functions", action="store_true")
        parser_rm.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_rm.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")

        # 'log' command
        parser_log = subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=scar.log)
        parser_log.add_argument("name", help="Lambda function name")
        parser_log.add_argument("-ls", "--log_stream_name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request_id", help="Return the output for the request id specified.")

    def execute(self):
        Config().check_config_file()
        """Command parsing and selection"""
        args = self.parser.parse_args()
        try:
            args.func(args)
        except AttributeError as ae:
            print("Error: %s" % ae)
            print("Use scar -h to see the options available")

if __name__ == "__main__":
    CmdParser().execute()
