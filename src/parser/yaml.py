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

import yaml
import os
from src.exceptions import YamlFileNotFoundError
import src.utils as utils

class YamlParser(object):
    
    def __init__(self, scar_args):
        file_path = scar_args['conf_file']
        if os.path.isfile(file_path):
            with open(file_path) as cfg_file:
                self.__setattr__("yaml_data", yaml.safe_load(cfg_file))
        else:
            raise YamlFileNotFoundError(file_path=file_path)
        
    def parse_arguments(self):
        functions = []        
        for function in self.yaml_data['functions']:
            functions.append(self.parse_aws_function(function, self.yaml_data['functions'][function]))
        return functions[0]
    
    def parse_aws_function(self, function_name, function_data):
        
        aws_args = {}
        # Get function name
        aws_args['lambda'] = self.parse_lambda_args(function_data)
        aws_args['lambda']['name'] = function_name
        if 'iam' in function_data:
            aws_args['iam'] = function_data['iam']
        if 'cloudwatch' in function_data:            
            aws_args['cloudwatch'] = function_data['cloudwatch']
        if 's3' in function_data:        
            aws_args['s3'] = function_data['s3']
        if 'api_gateway' in function_data:        
            aws_args['api_gateway'] = function_data['api_gateway']
        ###    
        if 'batch' in function_data:        
            aws_args['batch'] = function_data['batch']
        ###    
        other_args = [('profile','boto_profile'),'region']
        aws_args.update(utils.parse_arg_list(other_args, function_data))
        aws = {}     
        aws['aws'] = aws_args
        return aws
    ###
    def parse_lambda_args(self, cmd_args):
        lambda_args = ['asynchronous', 'init_script', 'run_script', 'c_args', 'memory', 'time',
                       'timeout_threshold', 'log_level', 'image', 'image_file', 'description', 
                       'lambda_role', 'extra_payload','execution_mode', ('environment', 'environment_variables')]
        return utils.parse_arg_list(lambda_args, cmd_args)    
        