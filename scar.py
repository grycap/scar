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

from aws.lambdafunction import AWSLambda
from aws.awsmanager import AWSManager
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
            self.aws_manager.add_event_source()
        # If preheat is activated, the function is launched at the init step
        if self.aws_lambda.preheat:    
            self.aws_manager.preheat_function()
    
    def run(self):
        if self.aws_lambda.has_event_source():
            self.process_event_source_calls()               
        else:
            self.launch_lambda_instance()
    
    def ls(self):
        lambda_function_info_list = self.aws_manager.get_all_functions_info()
        self.aws_manager.response_parser.parse_ls_response(lambda_function_info_list, self.aws_lambda.output)
    
    def rm(self):
        if self.aws_lambda.delete_all:
            self.aws_manager.delete_all_resources()
        else:
            self.aws_manager.delete_function_resources()
    
    def log(self):
        print(self.aws_manager.get_function_log())


if __name__ == "__main__":
    logging.info('----------------------------------------------------')
    logging.info('SCAR execution started')
    aws_lambda = AWSLambda()
    scar = Scar(aws_lambda)
    args = CommandParser(scar).parse_arguments()
    aws_lambda.set_attributes(args)
    args.func()
    logging.info('SCAR execution finished')
    logging.info('----------------------------------------------------')   
    
