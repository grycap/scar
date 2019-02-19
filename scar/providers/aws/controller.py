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

from scar.cmdtemplate import Commands
from scar.providers.aws.apigateway import APIGateway
from scar.providers.aws.batchfunction import Batch
from scar.providers.aws.cloudwatchlogs import CloudWatchLogs
from scar.providers.aws.iam import IAM
from scar.providers.aws.lambdafunction import Lambda
from scar.providers.aws.resourcegroups import ResourceGroups
from scar.providers.aws.s3 import S3
from scar.providers.aws.validators import AWSValidator
import os
import scar.exceptions as excp
import scar.logger as logger
import scar.providers.aws.response as response_parser
import scar.utils as utils

class AWS(Commands):

    properties = {}

    @utils.lazy_property
    def _lambda(self):
        '''It's called _lambda because 'lambda'
        it's a restricted word in python'''
        _lambda = Lambda(self.properties)
        return _lambda

    @utils.lazy_property
    def batch(self):
        batch = Batch(self.properties)
        return batch
    
    @utils.lazy_property
    def cloudwatch_logs(self):
        cloudwatch_logs = CloudWatchLogs(self.properties)
        return cloudwatch_logs
    
    @utils.lazy_property
    def api_gateway(self):
        api_gateway = APIGateway(self.properties)
        return api_gateway    
    
    @utils.lazy_property
    def s3(self):
        s3 = S3(self.properties)
        return s3      
    
    @utils.lazy_property
    def resource_groups(self):
        resource_groups = ResourceGroups(self.properties)
        return resource_groups
    
    @utils.lazy_property
    def iam(self):
        iam = IAM(self.properties)
        return iam    
       
    @excp.exception(logger)
    def init(self):
        if self._lambda.find_function():
            raise excp.FunctionExistsError(function_name=self._lambda.properties['name'])
        
        if 'api_gateway' in self.properties:
            self.api_gateway.create_api_gateway()

        response = self._lambda.create_function()
        response_parser.parse_lambda_function_creation_response(response,
                                                                self._lambda.properties['name'],
                                                                self._lambda.client.get_access_key(),
                                                                self.properties['output'])
        response = self.cloudwatch_logs.create_log_group()
        response_parser.parse_log_group_creation_response(response,
                                                          self.cloudwatch_logs.get_log_group_name(),
                                                          self.properties['output'])        
    
        if 's3' in self.properties:
            self.manage_s3_init()
        if 'api_gateway' in self.properties:
            self._lambda.add_invocation_permission_from_api_gateway() 
        # If preheat is activated, the function is launched at the init step
        if 'preheat' in self.scar_properties:
            self._lambda.preheat_function()
        if self.is_batch_execution():
            self.batch.create_compute_environment()
    
    @excp.exception(logger)    
    def invoke(self):
        response = self._lambda.call_http_endpoint()
        response_parser.parse_http_response(response, 
                                            self._lambda.properties['name'],
                                            self._lambda.is_asynchronous())
    
    @excp.exception(logger)    
    def run(self):
        if 's3' in self.properties and 'input_bucket' in self.properties['s3']:
            self.process_input_bucket_calls()
        else:
            if self._lambda.is_asynchronous():
                self._lambda.set_asynchronous_call_parameters()
            self._lambda.launch_lambda_instance()
    
    @excp.exception(logger)    
    def update(self):
        if 'supervisor_layer' in self.properties['lambda'] and self.properties['lambda']['supervisor_layer']:
            self._lambda.layers.update_supervisor_layer()
        if 'all' in self.scar_properties and self.scar_properties['all']:
            self.update_all_functions(self.get_all_functions())        
        else:
            self._lambda.update_function_attributes()
    
    @excp.exception(logger)
    def ls(self):
        if 's3' in self.properties:
            file_list = self.s3.get_bucket_file_list()
            for file_info in file_list:
                print(file_info)
        elif 'layers' in self.properties['lambda']:
            self._lambda.layers.print_layers_info()
        else:
            lambda_functions = self.get_all_functions()
            response_parser.parse_ls_response(lambda_functions, 
                                              self.properties['output'])
    
    @excp.exception(logger)    
    def rm(self):
        if 'all' in self.scar_properties and self.scar_properties['all']:
            self.delete_all_resources(self.get_all_functions())        
        else:
            self.delete_resources()

    @excp.exception(logger)
    def log(self):
        aws_log = self.cloudwatch_logs.get_aws_log()
        batch_logs = self.get_batch_logs()
        aws_log += batch_logs if batch_logs else ""
        print(aws_log)
        
    @excp.exception(logger)        
    def put(self):
        self.upload_file_or_folder_to_s3()
    
    @excp.exception(logger)        
    def get(self):
        self.download_file_or_folder_from_s3()

    @AWSValidator.validate()
    @excp.exception(logger)
    def parse_arguments(self, **kwargs):
        self.properties = kwargs['aws']
        self.scar_properties = kwargs['scar']
        self.add_extra_aws_properties()

    def add_extra_aws_properties(self):
        self.add_tags()
        self.add_output()
        self.add_account_id()
        self.add_config_file_path()
        
    def add_tags(self):
        self.properties["tags"] = {}
        self.properties["tags"]['createdby'] = 'scar'
        self.properties["tags"]['owner'] = self.iam.get_user_name_or_id()
                
    def add_output(self):
        self.properties["output"] = response_parser.OutputType.PLAIN_TEXT
        if 'json' in self.scar_properties and self.scar_properties['json']:
            self.properties["output"] = response_parser.OutputType.JSON
        # Override json ouput if both of them are defined
        if 'verbose' in self.scar_properties and self.scar_properties['verbose']:
            self.properties["output"] = response_parser.OutputType.VERBOSE
            
    def add_account_id(self):
        self.properties['account_id'] = utils.find_expression(self.properties['iam']['role'], '\d{12}')
        
    def add_config_file_path(self):
        if 'conf_file' in self.scar_properties and self.scar_properties['conf_file']:
            self.properties['config_path'] = os.path.dirname(self.scar_properties['conf_file'])

    def get_all_functions(self):
        user_id = self.iam.get_user_name_or_id()
        functions_arn_list = self.resource_groups.get_lambda_functions_arn_list(user_id)        
        return self._lambda.get_all_functions(functions_arn_list)        

    def get_batch_logs(self):
        if 'request_id' in self.properties["cloudwatch"] and self.batch.exist_job(self.properties["cloudwatch"]["request_id"]):
            batch_jobs = self.batch.describe_jobs(self.properties["cloudwatch"]["request_id"])
            return self.cloudwatch_logs.get_batch_job_log(batch_jobs["jobs"])

    def manage_s3_init(self):
        if 'input_bucket' in self.properties['s3']:
            self.create_s3_source()
        if 'output_bucket' in self.properties['s3']:
            self.s3.create_output_bucket()
        
    @excp.exception(logger)
    def create_s3_source(self):
        self.s3.create_input_bucket(create_input_folder=True)
        self._lambda.link_function_and_input_bucket()
        self.s3.set_input_bucket_notification()
        
    def process_input_bucket_calls(self):
        s3_file_list = self.s3.get_bucket_file_list()
        logger.info("Files found: '{0}'".format(s3_file_list))
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_event = self.s3.get_s3_event(s3_file_list.pop(0))
            self._lambda.launch_request_response_event(s3_event)
        # If the list has more elements, invoke functions asynchronously    
        if s3_file_list:
            s3_event_list = self.s3.get_s3_event_list(s3_file_list)
            self._lambda.process_asynchronous_lambda_invocations(s3_event_list)      

    def upload_file_or_folder_to_s3(self):
        path_to_upload = self.scar_properties['path']
        bucket_folder = self.s3.properties['input_folder']
        self.s3.create_input_bucket()
        files = utils.get_all_files_in_directory(path_to_upload) if os.path.isdir(path_to_upload) else [path_to_upload]
        for file_path in files:
            self.s3.upload_file(folder_name=bucket_folder, file_path=file_path)
     
    def get_download_file_path(self, s3_file_key, file_prefix):
        file_path = s3_file_key
        # Parse file path
        if file_prefix:
            # Get folder name
            dir_name_to_add = os.path.basename(os.path.dirname(file_prefix))
            # Don't replace last '/'
            file_path = s3_file_key.replace(file_prefix[:-1], dir_name_to_add)
        if 'path' in self.scar_properties and self.scar_properties['path']:
            path_to_download = self.scar_properties['path']
            file_path = utils.join_paths(path_to_download, file_path)
        return file_path

    def download_file_or_folder_from_s3(self):
        bucket_name = self.s3.properties['input_bucket']
        file_prefix = self.s3.properties['input_folder']
        s3_file_list = self.s3.get_bucket_file_list()
        for s3_file in s3_file_list:
            # Avoid download s3 'folders'
            if not s3_file.endswith('/'):
                file_path = self.get_download_file_path(s3_file, file_prefix)
                # make sure the path folders are created
                dir_path = os.path.dirname(file_path)              
                if dir_path and not os.path.isdir(dir_path):
                    os.makedirs(dir_path, exist_ok=True) 
                self.s3.download_file(bucket_name, s3_file, file_path)                    
     
    def update_all_functions(self, lambda_functions):
        for function_info in lambda_functions:
            self._lambda.update_function_attributes(function_info)
     
    def delete_all_resources(self, lambda_functions):
        for function in lambda_functions:
            self._lambda.properties['name'] = function['FunctionName']
            self.delete_resources()
        
    def delete_resources(self):
        if not self._lambda.find_function():
            raise excp.FunctionNotFoundError(self.properties['lambda']['name'])
        # Delete associated api
        self.delete_api_gateway()
        # Delete associated log
        self.delete_logs()
        # Delete associated notifications
        self.delete_bucket_notifications()        
        # Delete function
        self.delete_lambda_function()
        # Delete resources batch  
        self.delete_batch_resources()

    def delete_batch_resources(self):
        if(self.batch.exist_compute_environments(self._lambda.properties['name'])):
            self.batch.delete_compute_environment(self._lambda.properties['name'])

    def delete_lambda_function(self):
        response = self._lambda.delete_function()
        if response:
            response_parser.parse_delete_function_response(response,
                                                           self.properties['lambda']['name'],
                                                           self.properties['output'])         

    def delete_bucket_notifications(self):
        func_info = self._lambda.get_function_info()
        self.properties['lambda']['arn'] = func_info['FunctionArn']
        self.properties['lambda']['environment'] = {'Variables' : func_info['Environment']['Variables']}
        if 'INPUT_BUCKET' in self.properties['lambda']['environment']['Variables']:
            self.properties['s3'] = {'input_bucket' : self.properties['lambda']['environment']['Variables']['INPUT_BUCKET']}
            self.s3.delete_bucket_notification() 

    def delete_logs(self):
        response = self.cloudwatch_logs.delete_log_group()
        if response:
            response_parser.parse_delete_log_response(response,
                                                      self.cloudwatch_logs.get_log_group_name(),
                                                      self.properties['output'])        

    def delete_api_gateway(self):
        self.properties['api_gateway'] = {'id' : self._lambda.get_api_gateway_id() }
        if self.properties['api_gateway']['id']:
            response = self.api_gateway.delete_api_gateway()
            if response:
                response_parser.parse_delete_api_response(response,
                                                          self.properties['api_gateway']['id'],
                                                          self.properties['output'])
    
    def is_batch_execution(self):
        return self.properties["execution_mode"] == "batch" or self.properties["execution_mode"] == "lambda-batch"
