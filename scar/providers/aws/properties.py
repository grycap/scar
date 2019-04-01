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

class ScarProperties(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

class AwsProperties(dict):
    
    def __init__(self, *args, **kwargs):
        '''
        {'account_id': '914332',
         'batch': see_batch_props_class,
         'boto_profile': 'default',
         'cloudwatch': see_cloudwatch_props_class,
         'config_path': 'cowsay',
         'execution_mode': 'lambda',
         'iam': see_iam_props_class,
         'lambda': see_lambda_props_class,
         'output': <OutputType.PLAIN_TEXT: 1>,
         'region': 'us-east-1',
         's3': see_s3_props_class,
         'tags': {'createdby': 'scar', 'owner': 'alpegon'}}        
        '''        
        super().__init__(*args, **kwargs)
        self.__dict__ = self
        self._initialize_properties()
        
    def _initialize_properties(self):
        if hasattr(self, "api_gateway"):
            self.api_gateway = ApiGatewayProperties(self.api_gateway)
        if hasattr(self, "batch"):
            self.batch = BatchProperties(self.batch)
        if hasattr(self, "cloudwatch"):
            self.cloudwatch = CloudWatchProperties(self.cloudwatch)
        if hasattr(self, "iam"):
            self.iam = IamProperties(self.iam)        
        if hasattr(self, "lambda"):
            self._lambda = LambdaProperties(self.__dict__['lambda'])
            self.__dict__.pop('lambda', None)
        if hasattr(self, "s3"):
            self.s3 = S3Properties(self.s3)                        

class ApiGatewayProperties(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self    

class BatchProperties(dict):
    '''
    Example of dictionary used to initialize the class properties:
    {'comp_type': 'EC2',
    'desired_v_cpus': 0,
    'instance_types': ['m3.medium'],
    'max_v_cpus': 2,
    'min_v_cpus': 0,
    'security_group_ids': ['sg-2568'],
    'state': 'ENABLED',
    'subnets': ['subnet-568',
                'subnet-569',
                'subnet-570',
                'subnet-571',
                'subnet-572'],
    'type': 'MANAGED'}
    '''    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

class LambdaProperties(dict):
    '''
    Example of dictionary used to initialize the class properties:
    {'asynchronous': False,
    'description': 'Automatically generated lambda function',
    'environment': {'Variables': {'EXECUTION_MODE': 'lambda',
                                  'INPUT_BUCKET': 'test1',
                                  'LOG_LEVEL': 'INFO',
                                  'SUPERVISOR_TYPE': 'LAMBDA',
                                  'TIMEOUT_THRESHOLD': '10',
                                  'UDOCKER_BIN': '/opt/udocker/bin/',
                                  'UDOCKER_DIR': '/tmp/shared/udocker',
                                  'UDOCKER_EXEC': '/opt/udocker/udocker.py',
                                  'UDOCKER_LIB': '/opt/udocker/lib/'}},
    'extra_payload': '/test/',
    'handler': 'test.lambda_handler',
    'image_file': 'minicow.tar.gz',
    'init_script': 'test.sh',
    'invocation_type': 'RequestResponse',
    'layers': ['arn:aws:lambda:us-east-1:914332:layer:faas-supervisor:1'],
    'log_level': 'INFO',
    'log_type': 'Tail',
    'memory': 512,
    'name': 'test',
    'runtime': 'python3.6',
    'time': 300,
    'timeout_threshold': 10,
    'zip_file_path': '/tmp/function.zip'}
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
    
    def update_properties(self, **kwargs):
        self.__dict__.update(**kwargs)
        
class IamProperties(dict):
    '''
    Example of dictionary used to initialize the class properties:
    {'role': 'arn:aws:iam::914332:role/invented-role'}
    '''    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
        
class S3Properties(dict):
    '''
    Example of dictionary used to initialize the class properties:    
    {'input_bucket': 'test1'}
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
        self.process_storagePaths()
        
    def process_storagePaths(self):
        if hasattr(self, "input_bucket"):
            self.storage_path_input = self.input_bucket
            input_path = self.input_bucket.split("/")
            if len(input_path) > 1:
                # There are folders defined
                self.input_bucket = input_path[0]
                self.input_folder = "/".join(input_path[1:])
            
        if hasattr(self, "output_bucket"):
            self.storage_path_output = self.output_bucket
            output_path = self.output_bucket.split("/")
            if len(output_path) > 1:
                # There are folders defined
                self.output_bucket = output_path[0]
                self.output_folder = "/".join(output_path[1:])
        
class CloudWatchProperties(dict):
    '''
    Example of dictionary used to initialize the class properties:
    {'log_retention_policy_in_days': 30}
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self        
