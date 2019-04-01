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
from scar.providers.aws.properties import AwsProperties, ScarProperties,\
    S3Properties
from scar.providers.aws.resourcegroups import ResourceGroups
from scar.providers.aws.s3 import S3
from scar.providers.aws.validators import AWSValidator
import os
import scar.exceptions as excp
import scar.logger as logger
import scar.providers.aws.response as response_parser
import scar.utils as utils

class AWS(Commands):

    @utils.lazy_property
    def _lambda(self):
        '''It's called _lambda because 'lambda'
        it's a restricted word in python'''
        _lambda = Lambda(self.aws_properties)
        return _lambda

    @utils.lazy_property
    def batch(self):
        batch = Batch(self.aws_properties)
        return batch
    
    @utils.lazy_property
    def cloudwatch_logs(self):
        cloudwatch_logs = CloudWatchLogs(self.aws_properties)
        return cloudwatch_logs
    
    @utils.lazy_property
    def api_gateway(self):
        api_gateway = APIGateway(self.aws_properties)
        return api_gateway    
    
    @utils.lazy_property
    def s3(self):
        s3 = S3(self.aws_properties)
        return s3      
    
    @utils.lazy_property
    def resource_groups(self):
        resource_groups = ResourceGroups(self.aws_properties)
        return resource_groups
    
    @utils.lazy_property
    def iam(self):
        iam = IAM(self.aws_properties)
        return iam    
    
    @excp.exception(logger)
    def init(self):
        if self._lambda.find_function():
            raise excp.FunctionExistsError(function_name=self.aws_properties._lambda.name)
        # We have to create the gateway before creating the function
        self._create_api_gateway()
        self._create_lambda_function()
        self._create_log_group()
        self._create_s3_buckets()
        # The api_gateway permissions are added after the function is created
        self._add_api_gateway_permissions()
        self._create_batch_environment()
        self._preheat_function()

    @excp.exception(logger)    
    def invoke(self):
        response = self._lambda.call_http_endpoint()
        response_parser.parse_http_response(response, 
                                            self.aws_properties._lambda.name,
                                            self.aws_properties._lambda.asynchronous)
    
    @excp.exception(logger)    
    def run(self):
        if hasattr(self.aws_properties, "s3") and hasattr(self.aws_properties.s3, "input_bucket"):
            self._process_input_bucket_calls()
        else:
            if self._lambda.is_asynchronous():
                self._lambda.set_asynchronous_call_parameters()
            self._lambda.launch_lambda_instance()
    
    @excp.exception(logger)    
    def update(self):
        if hasattr( self.aws_properties._lambda, "supervisor_layer") and \
                    self.aws_properties._lambda.supervisor_layer:
            self._lambda.layers.update_supervisor_layer()
        if hasattr(self.scar_properties, "all") and self.scar_properties.all:
            self._update_all_functions(self._get_all_functions())        
        else:
            self._lambda.update_function_configuration()
    
    @excp.exception(logger)
    def ls(self):
        if hasattr(self.aws_properties, "s3"):
            file_list = self.s3.get_bucket_file_list()
            for file_info in file_list:
                print(file_info)
        elif hasattr(self.aws_properties._lambda, "layers"):
            self._lambda.layers.print_layers_info()
        else:
            lambda_functions = self._get_all_functions()
            response_parser.parse_ls_response(lambda_functions, 
                                              self.aws_properties.output)
    
    @excp.exception(logger)    
    def rm(self):
        if hasattr(self.scar_properties, "all") and self.scar_properties.all:
            self.delete_all_resources(self._get_all_functions())        
        else:
            self.delete_resources()

    @excp.exception(logger)
    def log(self):
        aws_log = self.cloudwatch_logs.get_aws_log()
        batch_logs = self._get_batch_logs()
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
        self.aws_properties = AwsProperties(**kwargs['aws'])
        self.scar_properties = ScarProperties(kwargs['scar'])
        self.add_extra_aws_properties()

    def add_extra_aws_properties(self):
        self._add_tags()
        self._add_output()
        self._add_account_id()
        self._add_config_file_path()
        
    def _add_tags(self):
        self.aws_properties.tags = {"createdby" : "scar",
                                    "owner" : self.iam.get_user_name_or_id() }
                
    def _add_output(self):
        self.aws_properties.output = response_parser.OutputType.PLAIN_TEXT
        if hasattr(self.scar_properties, "json") and self.scar_properties.json:
            self.aws_properties.output = response_parser.OutputType.JSON
        # Override json ouput if both of them are defined
        if hasattr(self.scar_properties, "verbose") and self.scar_properties.verbose:
            self.aws_properties.output = response_parser.OutputType.VERBOSE
            
    def _add_account_id(self):
        self.aws_properties.account_id = utils.find_expression(self.aws_properties.iam.role, '\d{12}')
        
    def _add_config_file_path(self):
        if hasattr(self.scar_properties, "conf_file") and self.scar_properties.conf_file:
            self.aws_properties.config_path = os.path.dirname(self.scar_properties.conf_file)

    def _get_all_functions(self):
        functions_arn_list = self.resource_groups.get_lambda_functions_arn_list(self.iam.get_user_name_or_id())        
        return self._lambda.get_all_functions(functions_arn_list)        

    def _get_batch_logs(self):
        if hasattr(self.aws_properties.cloudwatch, "request_id") and \
        self.batch.exist_job(self.aws_properties.cloudwatch.request_id):
            batch_jobs = self.batch.describe_jobs(self.aws_properties.cloudwatch.request_id)
            return self.cloudwatch_logs.get_batch_job_log(batch_jobs["jobs"])

    @excp.exception(logger)
    def _create_lambda_function(self):
        response = self._lambda.create_function()
        response_parser.parse_lambda_function_creation_response(response,
                                                                self.aws_properties._lambda.name,
                                                                self._lambda.client.get_access_key(),
                                                                self.aws_properties.output)

    @excp.exception(logger)        
    def _create_log_group(self):
        response = self.cloudwatch_logs.create_log_group()
        response_parser.parse_log_group_creation_response(response,
                                                          self.cloudwatch_logs.get_log_group_name(),
                                                          self.aws_properties.output)

    @excp.exception(logger)
    def _create_s3_buckets(self):
        if hasattr(self.aws_properties, "s3"):        
            if hasattr(self.aws_properties.s3, "input_bucket"):
                self.s3.create_input_bucket(create_input_folder=True)
                self._lambda.link_function_and_input_bucket()
                self.s3.set_input_bucket_notification()
            if hasattr(self.aws_properties.s3, "output_bucket"):
                self.s3.create_output_bucket()
        
    def _create_api_gateway(self):
        if hasattr(self.aws_properties, "api_gateway"):
            self.api_gateway.create_api_gateway()

    def _add_api_gateway_permissions(self):
        if hasattr(self.aws_properties, "api_gateway"):
            self._lambda.add_invocation_permission_from_api_gateway()
            
    def _create_batch_environment(self):
        if self.aws_properties.execution_mode == "batch" or \
        self.aws_properties.execution_mode == "lambda-batch":
            self.batch.create_compute_environment()
            
    def _preheat_function(self):
        # If preheat is activated, the function is launched at the init step
        if hasattr(self.scar_properties, "preheat"):
            self._lambda.preheat_function()
        
    def _process_input_bucket_calls(self):
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
        path_to_upload = self.scar_properties.path
        self.s3.create_input_bucket()
        files = utils.get_all_files_in_directory(path_to_upload) if os.path.isdir(path_to_upload) else [path_to_upload]
        for file_path in files:
            self.s3.upload_file(folder_name=self.aws_properties.s3.input_folder, file_path=file_path)
     
    def _get_download_file_path(self, file_key=None, prefix=None):
        file_path = file_key
#         # Parse file path
#         if prefix:
#             # Get folder name
#             dir_name_to_add = os.path.basename(os.path.dirname(prefix))
#             # Don't replace last '/'
#             file_path = file_key.replace(prefix[:-1], dir_name_to_add)
        if hasattr(self.scar_properties, "path") and self.scar_properties.path:
            file_path = utils.join_paths(self.scar_properties.path, file_path)
        return file_path
    
    def download_file_or_folder_from_s3(self):
        bucket_name = self.aws_properties.s3.input_bucket
        file_prefix = self.aws_properties.s3.input_folder
        s3_file_list = self.s3.get_bucket_file_list()
        for s3_file in s3_file_list:
            # Avoid download s3 'folders'
            if not s3_file.endswith('/'):
                file_path = self._get_download_file_path(file_key=s3_file, prefix=file_prefix)
                print("PATH", file_path)
                # make sure the path folders are created
                dir_path = os.path.dirname(file_path)    
                if dir_path and not os.path.isdir(dir_path):
                    os.makedirs(dir_path, exist_ok=True) 
                self.s3.download_file(bucket_name, s3_file, file_path)                    
     
    def _update_all_functions(self, lambda_functions):
        for function_info in lambda_functions:
            self._lambda.update_function_configuration(function_info)
     
    def delete_all_resources(self, lambda_functions):
        for function in lambda_functions:
            self.aws_properties._lambda.name = function['FunctionName']
            self.delete_resources()
        
    def delete_resources(self):
        if not self._lambda.find_function():
            raise excp.FunctionNotFoundError(self.aws_properties._lambda.name)
        # Delete associated api
        if hasattr(self.aws_properties, "api_gateway"):
            self._delete_api_gateway()
        # Delete associated log
        self._delete_logs()
        # Delete associated notifications
        self._delete_bucket_notifications()        
        # Delete function
        self._delete_lambda_function()
        # Delete resources batch
        if hasattr(self.aws_properties, "batch"):
            self._delete_batch_resources()

    def _delete_api_gateway(self):
        self.aws_properties.api_gateway.id = self._lambda.get_api_gateway_id()
        if self.aws_properties.api_gateway.id:
            response = self.api_gateway.delete_api_gateway()
            response_parser.parse_delete_api_response(response,
                                                      self.aws_properties.api_gateway.id,
                                                      self.aws_properties.output)
                
    def _delete_logs(self):
        response = self.cloudwatch_logs.delete_log_group()
        response_parser.parse_delete_log_response(response,
                                                  self.cloudwatch_logs.get_log_group_name(),
                                                  self.aws_properties.output)

    def _delete_bucket_notifications(self):
        func_info = self._lambda.get_function_info()
        self.aws_properties._lambda.arn = func_info['FunctionArn']
        self.aws_properties._lambda.environment = {'Variables' : func_info['Environment']['Variables']}
        
        s3_provider_id = utils.get_storage_provider_id('S3', self.aws_properties._lambda.environment['Variables'])
        input_bucket_id = 'STORAGE_PATH_INPUT_{}'.format(s3_provider_id) if s3_provider_id else ''
        if input_bucket_id in self.aws_properties._lambda.environment['Variables']:
            input_bucket_name = self.aws_properties._lambda.environment['Variables'][input_bucket_id]
            setattr(self.aws_properties, 's3', S3Properties({'input_bucket': input_bucket_name}))
            self.s3.delete_bucket_notification()
            logger.info("Successfully delete bucket notifications")
            
    def _delete_lambda_function(self):
        response = self._lambda.delete_function()
        response_parser.parse_delete_function_response(response,
                                                       self.aws_properties._lambda.name,
                                                       self.aws_properties.output)

    def _delete_batch_resources(self):
        if self.batch.exist_compute_environments(self.aws_properties._lambda.name):
            self.batch.delete_compute_environment(self.aws_properties._lambda.name)
