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

import configparser
import logging
import utils.functionutils as utils
import os

config_file_folder = os.path.expanduser("~") + "/.scar"
config_file_name = "scar_aws.cfg"
config_file_path = config_file_folder + '/' + config_file_name

default_aws_lambda_name = 'scar_function'
default_aws_lambda_region = 'us-east-1'
default_aws_lambda_time = 300
default_aws_lambda_memory = 512
default_aws_lambda_description = 'Automatically generated lambda function'
default_aws_lambda_timeout_threshold = 10
default_aws_lambda_runtime = 'python3.6'
default_aws_cloudwatch_log_retention_policy_in_days = 30

class Config(object):

    def __init__(self):
        self.config_parser = configparser.ConfigParser()
        self.check_config_file()

    def check_config_file(self):
        # Check if the config file exists
        if os.path.isfile(config_file_path):
            self.config_parser.read(config_file_path)
        else:
            # Create scar config dir
            os.makedirs(config_file_folder, exist_ok=True)
            self.create_default_config_file()
        
    def create_default_config_file(self):
        self.config_parser['iam'] = {'role' : ''}
        self.config_parser['lambda'] = {'name' : default_aws_lambda_name, 
                                   'region' : default_aws_lambda_region,
                                   'execution_time' : default_aws_lambda_time,
                                   'memory' : default_aws_lambda_memory,
                                   'description' : default_aws_lambda_description,
                                   'timeout_threshold' : default_aws_lambda_timeout_threshold,
                                   'runtime' : default_aws_lambda_runtime }
        self.config_parser['cloudwatch'] = {'log_retention_policy_in_days' : default_aws_cloudwatch_log_retention_policy_in_days}
        
        with open(config_file_path, "w") as config_file:
            self.config_parser.write(config_file)
        message = "Config file '%s' created.\nPlease, set a valid iam role in the file field 'role' before the first execution." % config_file_path
        logging.warning(message)
        print(message)
        utils.finish_successful_execution()
        
    def get_iam_role(self):
        return self.config_parser['iam'].get('role')
    
    def get_lambda_name(self):
        return self.config_parser['lambda'].get('name')
    
    def get_lambda_region(self):
        return self.config_parser['lambda'].get('region')
    
    def get_lambda_execution_time(self):
        return self.config_parser['lambda'].getint('execution_time')  
    
    def get_lambda_memory(self):
        return self.config_parser['lambda'].getint('memory')
    
    def get_lambda_description(self):
        return self.config_parser['lambda'].get('description')
    
    def get_lambda_timeout_threshold(self):
        return self.config_parser['lambda'].getint('timeout_threshold')
    
    def get_lambda_runtime(self):
        return self.config_parser['lambda'].get('runtime')
    
    def get_cloudwatch_log_retention_policy_in_days(self):
        return self.config_parser['cloudwatch'].getint('log_retention_policy_in_days')                   
        