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
import configparser
import json
import os
import re
import shutil
import sys
import zipfile
from botocore.exceptions import ClientError
from subprocess import call
from tabulate import tabulate

class Scar(object):
    """Implements most of the command line interface.
    These methods correspond directly to the commands that can
    be invoked via the command line interface.
    """
            
    def init(self, args):
        if self.find_function_name(args.name):
            if args.verbose or args.json:
                error = {'Error' : 'Cannot execute function. Function name \'' + args.name + '\' already defined.'}
                print(json.dumps(error))           
            else:
                print("ERROR: Cannot create function. Function name '" + args.name + "' already defined.")
            return        
        if args.name:
            Config.lambda_name = args.name
            Config.lambda_handler = Config.lambda_name + ".lambda_handler"
            Config.lambda_zip_file = {"ZipFile": self.create_zip_file(args.name)}
        else:
            # Create zip file with default values
            Config.lambda_zip_file = {"ZipFile": self.create_zip_file(Config.lambda_name)}
        if args.memory:
            Config.lambda_memory = self.check_memory(args.memory)
        if args.time:
            Config.lambda_time = self.check_time(args.time)
        if args.description:
            Config.lambda_description = args.description  
        if args.image_id:
            Config.lambda_env_variables['Variables']['IMAGE_ID'] = args.image_id
        # Update lambda tags
        Config.lambda_tags['owner'] = AwsClient().get_user_name()
        # Call the AWS service
        lambda_response = AwsClient().get_lambda().create_function(FunctionName=Config.lambda_name,
                                                     Runtime=Config.lambda_runtime,
                                                     Role=Config.lambda_role,
                                                     Handler=Config.lambda_handler,
                                                     Code=Config.lambda_zip_file,
                                                     Environment=Config.lambda_env_variables,
                                                     Description=Config.lambda_description,
                                                     Timeout=Config.lambda_time,
                                                     MemorySize=Config.lambda_memory,
                                                     Tags=Config.lambda_tags)
        # Remove the zip created in the operation
        os.remove(Config.zif_file_path)
        # Create log group
        cw_response = AwsClient().get_log().create_log_group(
            logGroupName='/aws/lambda/' + args.name,
            tags={ 'owner' : AwsClient().get_user_name(), 
                   'createdby' : 'scar' }
        )
        # Set retention policy in the logs
        AwsClient().get_log().put_retention_policy(
            logGroupName='/aws/lambda/' + args.name,
            retentionInDays=30
        )
        full_response = {'LambdaOutput' : lambda_response,
                         'CloudWatchOuput' : cw_response}
        # Generate results
        result = {'LambdaOutput' : {'AccessKey' : AwsClient().get_access_key(), 
                                    'FunctionArn' : lambda_response['FunctionArn'], 
                                    'Timeout' : lambda_response['Timeout'], 
                                    'MemorySize' : lambda_response['MemorySize'], 
                                    'FunctionName' : lambda_response['FunctionName']},
                  'CloudWatchOutput' : { 'RequestId' : cw_response['ResponseMetadata']['RequestId'], 
                                         'HTTPStatusCode' : cw_response['ResponseMetadata']['HTTPStatusCode'] }} 
        # Parse output
        if args.verbose:
            print(json.dumps(full_response))
        elif args.json:        
            print (json.dumps(result))
        else:
            print ("Function '" + args.name + "' successfully created.")
            print ("Log group '/aws/lambda/" + args.name + "' successfully created.")
    
    def find_function_name(self, function_name):
        paginator = AwsClient().get_lambda().get_paginator('list_functions')  
        for functions in paginator.paginate():         
            for lfunction in functions['Functions']:
                if function_name == lfunction['FunctionName']:
                    return True
        return False
    
    def check_function_name(self, function_name, json=False):
        if not self.find_function_name(function_name):
            if json:
                error = {'Error' : 'Function name \'' + function_name + '\' doesn\'t exist.'}
                print(json.dumps(error))           
            else:
                print("ERROR: Function name '" + function_name + "' doesn't exist.")
            sys.exit(1)  
       
    def ls(self, args):
        # Get the filtered resources from AWS
        client = AwsClient().get_resource_groups_tagging_api()
        tag_filters = [ { 'Key': 'owner', 'Values': [ AwsClient().get_user_name() ] }, { 'Key': 'createdby', 'Values': ['scar'] } ]
        response = client.get_resources(TagFilters=tag_filters, TagsPerPage=100)
        filtered_functions = response['ResourceTagMappingList']
        # Create the data structure
        result = {'Functions': []}
        for function_arn in filtered_functions:
            function_info = AwsClient().get_lambda().get_function(FunctionName=function_arn['ResourceARN'])
            function = {'Name' : function_info['Configuration']['FunctionName'],
                        'Memory' : function_info['Configuration']['MemorySize'],
                        'Timeout' : function_info['Configuration']['Timeout']}
            result['Functions'].append(function)
        # Parse output
        if args.verbose:
            print(json.dumps(response))
        elif args.json:
            print(json.dumps(result))
        else:  
            headers = ['NAME', 'MEMORY', 'TIME']
            table = []
            for function in result['Functions']:
                table.append([function['Name'],
                              function['Memory'],
                              function['Timeout']])            
            print (tabulate(table, headers))
        
    def run(self, args):
        self.check_function_name(args.name, (True if args.verbose or args.json else False))
        
        invocation_type = 'RequestResponse'
        log_type = 'Tail'
        if args.async:
            invocation_type = 'Event'
            log_type = 'None' 
        
        if args.memory:
            AwsClient().get_lambda().update_function_configuration(FunctionName=args.name,
                                                            MemorySize=self.check_memory(args.memory))   
        if args.time:
            AwsClient().get_lambda().update_function_configuration(FunctionName=args.name,
                                                            Timeout=self.check_time(args.time))   
        if args.env:
            # Retrieve the global variables already defined
            Config.lambda_env_variables = AwsClient().get_lambda().get_function(FunctionName=args.name)['Configuration']['Environment']
            for var in args.env:
                var_parsed = var.split("=")
                # Add an specific prefix to be able to find the variables defined by the user
                Config.lambda_env_variables['Variables']['CONT_VAR_' + var_parsed[0]] = var_parsed[1]
            AwsClient().get_lambda().update_function_configuration(FunctionName=args.name,
                                                            Environment=Config.lambda_env_variables)
            
        script = ""
        if args.payload:
            script = "{ \"script\" : \"" + StringUtils().escape_string(args.payload.read()) + "\"}"
        elif args.cont_args:
            script = "{ \"cmd_args\" : " + StringUtils().escape_list(args.cont_args) + "}"
        # Invoke lambda function 
        response = AwsClient().get_lambda().invoke(FunctionName=args.name,
                                              InvocationType=invocation_type,
                                              LogType=log_type,
                                              Payload=script)
        if args.async:
            if args.verbose:
                print(json.dumps(self.parse_payload(response))) 
            elif args.json:
                result = {'StatusCode' : response['StatusCode'],
                          'RequestId' : response['ResponseMetadata']['RequestId']}
                print(json.dumps(result))            
            else:
                if response['StatusCode'] == 202:
                    print("Function '" + args.name + "' launched correctly")
                else:
                    print("Error launching function.")            
        else:
            # Transform the base64 encoded results to something legible
            response['LogResult'] = StringUtils().base64_to_utf8(response['LogResult'])        
            response['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'] = StringUtils().base64_to_utf8(response['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'])
    
            # Extract log_group_name and log_stream_name from payload
            function_output = response['Payload'].read().decode("utf-8")[1:-1]
            response['Payload'] = function_output.replace('\\n', '\n')
            result = 'SCAR: Request Id: ' + response['ResponseMetadata']['RequestId'] + '\n'
            result += response['Payload']
            
            parsed_output = result.split('\n')
            response['LogGroupName'] = parsed_output[1][22:]
            response['LogStreamName'] = parsed_output[2][23:]
            
            if args.verbose:
                print(json.dumps(response))
            elif args.json:
                result = {'StatusCode' : response['StatusCode'],
                          'Payload' : response['Payload'],
                          'LogGroupName' : response['LogGroupName'],
                          'LogStreamName' : response['LogStreamName'],
                          'RequestId' : response['ResponseMetadata']['RequestId']}
                print(json.dumps(result))            
            else:
                print(result)
        
    def rm(self, args):
        self.check_function_name(args.name, (True if args.verbose or args.json else False))       
        
        # Delete the lambda function
        lambda_response = AwsClient().get_lambda().delete_function(FunctionName=args.name)
        # Delete the cloudwatch log group
        cw_response = AwsClient().get_log().delete_log_group(logGroupName='/aws/lambda/' + args.name)
        full_response = {'LambdaOutput' : lambda_response,
                         'CloudWatchOuput' : cw_response}
        # Parse output
        if args.verbose:
            print(json.dumps(full_response))
        elif args.json:
            result = {'LambdaOutput' : { 'RequestId' : lambda_response['ResponseMetadata']['RequestId'],
                                         'HTTPStatusCode' : lambda_response['ResponseMetadata']['HTTPStatusCode'] },
                      'CloudWatchOutput' : { 'RequestId' : cw_response['ResponseMetadata']['RequestId'],
                                             'HTTPStatusCode' : cw_response['ResponseMetadata']['HTTPStatusCode'] }                      
                      }
            print(json.dumps(result))
        else:
            if (lambda_response['ResponseMetadata']['HTTPStatusCode'] == 204) and (cw_response['ResponseMetadata']['HTTPStatusCode'] == 200):
                print ("Function '" + args.name + "' and logs correctly deleted.")
            else:
                print("Error deleting function '" + args.name + "'.")

    def log(self, args):
        try:
            response = AwsClient().get_log().get_log_events(
                logGroupName=args.log_group_name,
                logStreamName=args.log_stream_name,
                startFromHead=True
            )
            full_msg = ""
            for event in response['events']:
                full_msg += event['message']
            response['completeMessage'] = full_msg
            if args.request_id:
                print (self.parse_logs(full_msg, args.request_id))
            else:
                print (full_msg)
            
        except ClientError as ce:
            print(ce)
            
    def parse_payload(self, response):
        response['Payload'] = response['Payload'].read().decode("utf-8")[1:-1].replace('\\n', '\n')
        return response
    
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
    
    def create_zip_file(self, file_name):
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
        # Return the zip as an array of bytes
        with open(Config.zif_file_path, 'rb') as f:
            return f.read()
        
    def parse_logs(self, logs, request_id):
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

class StringUtils(object):

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

class Config(object):
    
    lambda_name = "scar_function"
    lambda_name = "scar_function"
    lambda_runtime = "python2.7"
    lambda_handler = lambda_name + ".lambda_handler"        
    lambda_role = "arn:aws:iam::974349055189:role/lambda-s3-execution-role"
    lambda_region = 'us-east-1'
    lambda_env_variables = {"Variables" : {"UDOCKER_DIR":"/tmp/home/.udocker", "UDOCKER_TARBALL":"/var/task/udocker-1.1.0-RC2.tar.gz"}}
    lambda_memory = 128
    lambda_time = 300
    lambda_description = "Automatically generated lambda function"
    lambda_tags = { 'createdby' : 'scar' }
        
    version = "v0.0.1"
        
    dir_path = os.path.dirname(os.path.realpath(__file__))
        
    zif_file_path = dir_path + '/function.zip'        
        
    config = configparser.ConfigParser()    
    
    def create_config_file(self, file_dir):
        
        self.config['scar'] = {'lambda_name' : "scar_function",
                          'lambda_description' : "Automatically generated lambda function",
                          'lambda_memory' : 128,
                          'lambda_time' : 300,
                          'lambda_region' : 'us-east-1'}
        with open(file_dir + "/scar.cfg","w") as configfile:
            self.config.write(configfile)
    
    def check_config_file(self):
        scar_dir = os.path.expanduser("~") + "/.scar"
        # Check if the scar directory exists
        if os.path.isdir(scar_dir):
            # Check if the config file exists
            if os.path.isfile(scar_dir + "/scar.cfg"):
                self.config.read(scar_dir + "/scar.cfg")
                self.parse_config_file_values()
            else:
                self.create_config_file(scar_dir)
        else:
            # Create scar dir
            call(["mkdir", "-p", scar_dir])
            self.create_config_file(scar_dir)
    
    def parse_config_file_values(self):
        scar_config = Config.config['scar']
        if 'lambda_name' in scar_config:
            self.lambda_name = scar_config.get('lambda_name')
            self.lambda_handler = Config.lambda_name + ".lambda_handler"
        Config.lambda_role = scar_config.get('lambda_role', fallback=Config.lambda_role)
        Config.lambda_region = scar_config.get('lambda_region', fallback=Config.lambda_region)
        Config.lambda_memory = scar_config.getint('lambda_memory', fallback=Config.lambda_memory)
        Config.lambda_time = scar_config.getint('lambda_time', fallback=Config.lambda_time)
        Config.lambda_description = scar_config.get('lambda_description', fallback=Config.lambda_description)

class AwsClient(object):
    
    def get_user_name(self):
        try:
            return self.get_iam().get_user()['User']['UserName']
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
        return boto3.client(client_name, region_name=region)    
    
    def get_lambda(self, region=None):
        return self.get_boto3_client('lambda', region)
    
    def get_log(self, region=None):
        return self.get_boto3_client('logs', region)
    
    def get_iam(self, region=None):
        return self.get_boto3_client('iam', region)
    
    def get_resource_groups_tagging_api(self, region=None):
        return self.get_boto3_client('resourcegroupstaggingapi', region)
        
class CmdParser(object):
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="scar",
                                              description="Deploy containers in serverless architectures",
                                              epilog="Run 'scar COMMAND --help' for more information on a command.")
        subparsers = self.parser.add_subparsers(title='Commands')
        
        # Create the parser for the 'version' command
        self.parser.add_argument('--version', action='version', version='%(prog)s ' + Config.version)        
                
        # 'init' command
        parser_init = subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=Scar().init)
        # Set the positional arguments
        parser_init.add_argument("image_id", help="Container image id (i.e. centos:7)") 
        # Set the optional arguments
        parser_init.add_argument("-d", "--description", help="Lambda function description.")        
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
    
        # 'ls' command
        parser_ls = subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=Scar().ls)
        parser_ls.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_ls.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        
        # 'run' command
        parser_run = subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=Scar().run)
        parser_run.add_argument("name", help="Lambda function name")
        parser_run.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_run.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_run.add_argument("-e", "--env", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_run.add_argument("--async", help="Tell Scar to wait or not for the lambda function return", action="store_true")
        parser_run.add_argument("-p", "--payload", nargs='?', type=argparse.FileType('r'), help="Path to the input file passed to the function")        
        parser_run.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_run.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_run.add_argument('cont_args', nargs=argparse.REMAINDER, help="Arguments passed to the container.")
        
        # Create the parser for the 'rm' command
        parser_rm = subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=Scar().rm)
        parser_rm.add_argument("name", help="Lambda function name")
        parser_rm.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_rm.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        
        # 'log' command
        parser_log = subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=Scar().log)
        parser_log.add_argument("log_group_name", help="The name of the log group.")
        parser_log.add_argument("log_stream_name", help="The name of the log stream.")
        parser_log.add_argument("-ri", "--request_id", help="Id of the request that generated the log.")
        
    def execute(self):
        Config().check_config_file()
        """Command parsing and selection"""
        args = self.parser.parse_args()
        args.func(args)        
        
if __name__ == "__main__":
    CmdParser().execute()        
