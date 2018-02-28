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

from aws.clients.lambdac import LambdaClient
from aws.clients.cloudwatchlogs import CloudWatchLogsClient
from aws.lambdafunction import AWSLambda
from aws.awsmanager import AWSManager
from botocore.exceptions import ClientError
from utils.commandparser import CommandParser
import logging

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='scar.log', level=logging.INFO, format=FORMAT)
                  
class Scar(object):
    
    def __init__(self, aws_lambda):
        self.aws_lambda = aws_lambda
        self.aws_manager = AWSManager(aws_lambda)
     
    def init(self):
        # Call the aws services
        self.aws_manager.create_lambda_function()
        self.aws_manager.create_log_group()
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
            self.aws_manager.delete_all_resources(self.aws_lambda.output)
        else:
            self.aws_manager.delete_resources(self.aws_lambda.name, self.aws_lambda.output)
    
    def log(self):
        try:
            log_client = CloudWatchLogsClient()
            full_msg = ""
            if self.aws_lambda.log_stream_name:
                response = log_client.get_log_events_by_group_name_and_stream_name(
                    self.aws_lambda.log_group_name,
                    self.aws_lambda.log_stream_name)
                for event in response['events']:
                    full_msg += event['message']
            else:
                response = log_client.get_log_events_by_group_name(self.aws_lambda.log_group_name)
                data = []
    
                for event in response['events']:
                    data.append((event['message'], event['timestamp']))
    
                while(('nextToken' in response) and response['nextToken']):
                    response = log_client.get_log_events_by_group_name(self.aws_lambda.log_group_name, response['nextToken'])
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
    
