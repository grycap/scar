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

class Function:
    def __init__(self, name, image):
        self.name = name
        self.image_id = image

class YamlParser(object):
    
    def __init__(self, args):
        file_path = args.conf_file
        self.func = args.func
        if os.path.isfile(file_path):
            with open(file_path) as cfg_file:
                self.__setattr__("yaml_data", yaml.safe_load(cfg_file))
        
    def parse_arguments(self):
        functions = []
        for function in self.yaml_data['functions']:
            functions.append(self.parse_function(function, self.yaml_data['functions'][function]))
        return functions[0]
    
    def parse_function(self, function_name, function_data):
        args = {'func' : self.func }
        # Get function name
        args['name'] = function_name
        # Parse function information
        if 'image' in function_data:
            args['image_id'] = function_data['image']
        if 'image_file' in function_data:
            args['image_file'] = function_data['image_file']
        if 'time' in function_data:
            args['time'] = function_data['time']
        if 'memory' in function_data:
            args['memory'] = function_data['memory']
        if 'timeout_threshold' in function_data:
            args['timeout_threshold'] = function_data['timeout_threshold']
        if 'lambda_role' in function_data:
            args['lambda_role'] = function_data['lambda_role']
        if 'description' in function_data:
            args['description'] = function_data['description']
        if 'init_script' in function_data:
            args['init_script'] = function_data['init_script']
        if 'run_script' in function_data:
            args['run_script'] = function_data['run_script']            
        if 'extra_payload' in function_data:
            args['extra_payload'] = function_data['extra_payload']
        if 'log_level' in function_data:
            args['log_level'] = function_data['log_level']            
        if 'environment' in function_data:
            variables = []
            for k,v in function_data['environment'].items():
                variables.append(str(k) + '=' + str(v))
            args['environment_variables'] = variables
        if 's3' in function_data:
            s3_data = function_data['s3']
            if 'deployment_bucket' in s3_data:
                args['deployment_bucket'] = s3_data['deployment_bucket']
            if 'input_bucket' in s3_data:
                args['input_bucket'] = s3_data['input_bucket']
            if 'input_folder' in s3_data:
                args['input_folder'] = s3_data['input_folder']
            if 'output_bucket' in s3_data:
                args['output_bucket'] = s3_data['output_bucket']
            if 'output_folder' in s3_data:
                args['output_folder'] = s3_data['output_folder']
        if 'api_gateway' in function_data:
            api_data = function_data['api_gateway']
            if 'name' in api_data:
                args['api_gateway_name'] = api_data['name']                                                              

        return args
        