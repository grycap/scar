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
"""Module with classes and methods used to manage the AWS tools."""

import os
from typing import Dict
from scar.cmdtemplate import Commands
from scar.providers.aws.apigateway import APIGateway
from scar.providers.aws.batchfunction import Batch
from scar.providers.aws.cloudwatchlogs import CloudWatchLogs
from scar.providers.aws.iam import IAM
from scar.providers.aws.lambdafunction import Lambda
# from scar.providers.aws.properties import AwsProperties, ScarProperties
from scar.providers.aws.resourcegroups import ResourceGroups
from scar.providers.aws.s3 import S3
from scar.providers.aws.validators import AWSValidator
import scar.exceptions as excp
import scar.logger as logger
import scar.providers.aws.response as response_parser
from scar.utils import StrUtils, FileUtils

_ACCOUNT_ID_REGEX = r'\d{12}'

# def _get_storage_provider_id(storage_provider: str, env_vars: Dict) -> str:
#     """Searches the storage provider id in the environment variables:
#         get_provider_id(S3, {'STORAGE_AUTH_S3_USER_41807' : 'scar'})
#         returns -> 41807"""
#     res = ""
#     for env_key in env_vars.keys():
#         if env_key.startswith(f'STORAGE_AUTH_{storage_provider}'):
#             res = env_key.split('_', 4)[-1]
#             break
#     return res


def _get_owner(resources_info: Dict):
    return IAM(resources_info).get_user_name_or_id()

def _check_function_defined(resources_info: Dict):
    if Lambda(resources_info).find_function():
        raise excp.FunctionExistsError(function_name=resources_info.get('lambda', {}).get('name', ''))

def _check_function_not_defined(resources_info: Dict):
    if not Lambda(resources_info).find_function():
        raise excp.FunctionNotFoundError(function_name=resources_info.get('lambda', {}).get('name', ''))

############################################
###          ADD EXTRA PROPERTIES        ###
############################################


def _add_extra_aws_properties(scar: Dict, aws_functions: Dict) -> None:
    for function in aws_functions:
        _add_tags(function)
        _add_handler(function)
        _add_account_id(function)
        _add_output(scar, function)
        _add_config_file_path(scar, function)


def _add_tags(function: Dict):
    function['lambda']['tags'] = {"createdby": "scar",
                                  "owner": _get_owner(function)}


def _add_account_id(function: Dict):
    function['iam']['account_id'] = StrUtils.find_expression(function['iam']['role'],
                                                              _ACCOUNT_ID_REGEX)


def _add_handler(function: Dict):
    function['lambda']['handler'] = f"{function.get('lambda', {}).get('name', '')}.lambda_handler"


def _add_output(scar_props: Dict, function: Dict):
    function['lambda']['cli_output'] = response_parser.OutputType.PLAIN_TEXT.value
    if scar_props.get("json", False):
        function['lambda']['cli_output'] = response_parser.OutputType.JSON.value
    # Override json ouput if both of them are defined
    if scar_props.get("verbose", False):
        function['lambda']['cli_output'] = response_parser.OutputType.VERBOSE.value
    if scar_props.get("output_file", False):
        function['lambda']['cli_output'] = response_parser.OutputType.BINARY.value
        function['lambda']['output_file'] = scar_props.get("output_file")


def _add_config_file_path(scar_props: Dict, function: Dict):
    if scar_props.get("conf_file", False):
        function['lambda']['config_path'] = os.path.dirname(scar_props.get("conf_file"))
        # Update the path of the files based on the path of the yaml (if any)
        if function['lambda'].get('init_script', False):
            function['lambda']['init_script'] = FileUtils.join_paths(function['lambda']['config_path'],
                                                                    function['lambda']['init_script'])
        if function['lambda'].get('image_file', False):
            function['lambda']['image_file'] = FileUtils.join_paths(function['lambda']['config_path'],
                                                                    function['lambda']['image_file'])
        if function['lambda'].get('run_script', False):
            function['lambda']['run_script'] = FileUtils.join_paths(function['lambda']['config_path'],
                                                                    function['lambda']['run_script'])            

#############################################################################
###                   Methods to create AWS resources                     ###
#############################################################################

@excp.exception(logger)
def _create_api_gateway(resources_info: Dict):
    if resources_info.get("api_gateway", {}).get('name', False):
        APIGateway(resources_info).create_api_gateway()
        
@excp.exception(logger)
def _create_lambda_function(resources_info: Dict) -> None:
    lambda_client = Lambda(resources_info)
    response = lambda_client.create_function()
    response_parser.parse_lambda_function_creation_response(response,
                                                            resources_info,
                                                            lambda_client.get_access_key())            

@excp.exception(logger)
def _create_log_group(resources_info: Dict) -> None:
    cloudwatch_logs = CloudWatchLogs(resources_info)
    response = cloudwatch_logs.create_log_group()
    response_parser.parse_log_group_creation_response(response,
                                                      cloudwatch_logs.get_log_group_name(),
                                                      resources_info.get('lambda').get('cli_output'))
    
@excp.exception(logger)
def _create_s3_buckets(resources_info: Dict) -> None:
    if resources_info.get('lambda').get('input', False):
        s3 = S3(resources_info)
        for bucket in resources_info.get('lambda').get('input'):
            if bucket.get('storage_provider') == 's3':
                bucket_name = s3.create_bucket_and_folders(bucket.get('path'))
                Lambda(resources_info).link_function_and_bucket(bucket_name)
                s3.set_input_bucket_notification(bucket_name)                    
                
    if resources_info.get('lambda').get('output', False):
        s3 = Lambda(resources_info)
        for bucket in resources_info.get('lambda').get('output'):
            if bucket.get('storage_provider') == 's3':
                s3.create_bucket_and_folders(bucket.get('path'))

@excp.exception(logger)
def _add_api_gateway_permissions(resources_info: Dict):
    if resources_info.get("api_gateway").get('name', False):
        Lambda(resources_info).add_invocation_permission_from_api_gateway()

@excp.exception(logger)
def _create_batch_environment(resources_info: Dict) -> None:
    mode = resources_info.get('lambda').get('execution_mode')
    if mode == "batch" or mode == "lambda-batch":
        Batch(resources_info).create_batch_environment()

#############################################################################
###                   Methods to delete AWS resources                     ###
#############################################################################

def _delete_all_resources():
    'TODO'
#         for function_info in self._get_all_functions():
#             self._delete_resources(function_info)

def _delete_resources(resources_info: Dict) -> None:
    # Delete associated api
    _delete_api_gateway(resources_info)
    # Delete associated log
    _delete_logs(resources_info)
    # Delete associated notifications
    _delete_bucket_notifications(resources_info)
    # Delete function
    _delete_lambda_function(resources_info)
    # Delete resources batch
    _delete_batch_resources(resources_info)

def _delete_api_gateway(resources_info: Dict) -> None:
    api_gateway_id = Lambda(resources_info).get_function_info().get('Environment').get('Variables').get('API_GATEWAY_ID')
    if api_gateway_id:
        resources_info['lambda']['environment']['Variables']['API_GATEWAY_ID'] = api_gateway_id
        response = APIGateway(resources_info).delete_api_gateway()
        response_parser.parse_delete_api_response(response,
                                                  api_gateway_id,
                                                  resources_info.get('lambda').get('cli_output'))

def _delete_logs(resources_info: Dict):
    cloudwatch_logs = CloudWatchLogs(resources_info)
    log_group_name = cloudwatch_logs.get_log_group_name(resources_info.get('lambda').get('name'))
    response = cloudwatch_logs.delete_log_group(log_group_name)
    response_parser.parse_delete_log_response(response,
                                              log_group_name,
                                              resources_info.get('lambda').get('cli_output'))

def _delete_bucket_notifications(resources_info: Dict) -> None:
    if resources_info.get('lambda').get('input', False):
        for input_storage in resources_info.get('lambda').get('input'):
            if input_storage.get('storage_provider') == 's3':
                bucket_name = input_storage.get('path').split("/", 1)[0]
                S3(resources_info).delete_bucket_notification(bucket_name)

def _delete_lambda_function(resources_info: Dict) -> None:
    response = Lambda(resources_info).delete_function()
    response_parser.parse_delete_function_response(response,
                                                   resources_info.get('lambda').get('name'),
                                                   resources_info.get('lambda').get('cli_output'))

def _delete_batch_resources(resources_info: Dict) -> None:
    batch = Batch(resources_info)
    if batch.exist_compute_environments():
        batch.delete_compute_environment()


############################################
###             AWS CONTROLLER           ###
############################################


class AWS(Commands):
    """AWS controller.
    Used to manage all the AWS calls and functionalities."""

    def __init__(self, func_call):
        self.raw_args = FileUtils.load_config_file()
        self.validate_arguments(self.raw_args)
        self.aws_functions = self.raw_args.get('functions', {}).get('aws', {})
        self.storages = self.raw_args.get('storages', {})
        self.scar = self.raw_args.get('scar', {})
        _add_extra_aws_properties(self.scar, self.aws_functions)
        # Call the user's command
        getattr(self, func_call)()

    @AWSValidator.validate()
    @excp.exception(logger)        
    def validate_arguments(self, merged_args: Dict) -> None:
        pass

############################################
###              AWS COMMANDS            ###
############################################

    @excp.exception(logger)
    def init(self) -> None:
        # supervisor_version = self.scar.get('supervisor_version', 'latest')
        for resources_info in self.aws_functions:
            _check_function_defined(resources_info)
            # We have to create the gateway before creating the function
            _create_api_gateway(resources_info)
            _create_lambda_function(resources_info)
            _create_log_group(resources_info)
            _create_s3_buckets(resources_info)
            # The api_gateway permissions are added after the function is created
            _add_api_gateway_permissions(resources_info)
            _create_batch_environment()
            # self._preheat_function()

    @excp.exception(logger)
    def invoke(self):
        'TODO'
#         self._update_local_function_properties()
#         response = self.aws_lambda.call_http_endpoint()
#         response_parser.parse_http_response(response,
#                                             self.aws_properties.lambdaf.name,
#                                             self.aws_properties.lambdaf.asynchronous,
#                                             self.aws_properties.output,
#                                             getattr(self.scar, "output_file", ""))

    @excp.exception(logger)
    def run(self):
        resources_info = self.aws_functions[0]
        lambda_client = Lambda(resources_info)
        if lambda_client.is_asynchronous():
            lambda_client.set_asynchronous_call_parameters()
        lambda_client.launch_lambda_instance()        
        'TODO FINISH'
#         if hasattr(self.aws_properties, "s3") and hasattr(self.aws_properties.s3, "input_bucket"):
#             self._process_input_bucket_calls()
#         else:
#             if self.aws_lambda.is_asynchronous():
#                 self.aws_lambda.set_asynchronous_call_parameters()
#             self.aws_lambda.launch_lambda_instance()

    @excp.exception(logger)
    def update(self):
        'TODO'
#         if hasattr(self.aws_properties.lambdaf, "all") and self.aws_properties.lambdaf.all:
#             self._update_all_functions(self._get_all_functions())
#         else:
#             self.aws_lambda.update_function_configuration()

    @excp.exception(logger)
    def ls(self):
        lambda_functions = self._get_all_functions()
        response_parser.parse_ls_response(lambda_functions,
                                          self.aws_functions[0].get('lambda').get('cli_output'))        
        'TODO FINISH'
#         if self.storages:
#             file_list = _get_s3_client(self.aws_functions).get_bucket_file_list()
#             for file_info in file_list:
#                 print(file_info)
#         else:
#             lambda_functions = self._get_all_functions()
#             response_parser.parse_ls_response(lambda_functions,
#                                               self.aws_properties.output)

    @excp.exception(logger)
    def rm(self):
        'TODO FINISH'
#         function_info = _get_lambda_client(self.aws_functions[0]).get_function_info(self.aws_functions[0]['lambda']['name'])
#         self._delete_resources(function_info)
        if self.scar.get('all', False):
            "Delete all functions"
        elif len(self.aws_functions) > 1:
            "Please select the function to delete"
        else:
            "Delete selected function"
            resources_info = self.aws_functions[0]
            _check_function_not_defined(resources_info)
            self._delete_resources(resources_info)            
        
#         function = self.aws_functions[0]
#         lambda_client = _get_lambda_client(function)
#         if not lambda_client.find_function(function['lambda']['name']):
#             raise excp.FunctionNotFoundError(function_name=function['lambda']['name'])
        # self._delete_resources(function_info)
#         if hasattr(self.aws_properties.lambdaf, "all") and self.aws_properties.lambdaf.all:
#             self._delete_all_resources()
#         else:

    @excp.exception(logger)
    def log(self):
        'TODO'
#         aws_log = self.cloudwatch_logs.get_aws_log()
#         batch_logs = self._get_batch_logs()
#         aws_log += batch_logs if batch_logs else ""
#         print(aws_log)

    @excp.exception(logger)
    def put(self):
        'TODO'        
#         self.upload_file_or_folder_to_s3()

    @excp.exception(logger)
    def get(self):
        'TODO'        
#         self.download_file_or_folder_from_s3()

############################################
###              ------------            ###
############################################

    def _get_all_functions(self):
        # There can be several functions defined
        # We check all and merge their arns to list them
        
#         for function in self.aws_functions:
#             iam_info = _get_iam_client(function).get_user_name_or_id()
#             functions_arn.union(set(_get_resource_groups_client(function).get_resource_arn_list(iam_info)))
#         return _get_lambda_client(self.aws_functions[0]).get_all_functions(functions_arn)
        resources_info = self.aws_functions[0]
        arn_list = ResourceGroups(resources_info).get_resource_arn_list(IAM(resources_info).get_user_name_or_id())
        return Lambda(resources_info).get_all_functions(arn_list)

    def _get_batch_logs(self) -> str:
        logs = ""
        if hasattr(self.aws_properties.cloudwatch, "request_id") and \
        self.batch.exist_job(self.aws_properties.cloudwatch.request_id):
            batch_jobs = self.batch.describe_jobs(self.aws_properties.cloudwatch.request_id)
            logs = self.cloudwatch_logs.get_batch_job_log(batch_jobs["jobs"])
        return logs

    def _preheat_function(self):
        # If preheat is activated, the function is launched at the init step
        if hasattr(self.scar, "preheat"):
            self.aws_lambda.preheat_function()

    def _process_input_bucket_calls(self):
        s3_file_list = self.aws_s3.get_bucket_file_list()
        logger.info(f"Files found: '{s3_file_list}'")
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_event = self.aws_s3.get_s3_event(s3_file_list.pop(0))
            self.aws_lambda.launch_request_response_event(s3_event)
        # If the list has more elements, invoke functions asynchronously
        if s3_file_list:
            s3_event_list = self.aws_s3.get_s3_event_list(s3_file_list)
            self.aws_lambda.process_asynchronous_lambda_invocations(s3_event_list)

    def upload_file_or_folder_to_s3(self):
        path_to_upload = self.scar.path
        self.aws_s3.create_input_bucket()
        files = [path_to_upload]
        if os.path.isdir(path_to_upload):
            files = FileUtils.get_all_files_in_directory(path_to_upload)
        for file_path in files:
            self.aws_s3.upload_file(folder_name=self.aws_properties.s3.input_folder,
                                    file_path=file_path)

    def _get_download_file_path(self, file_key=None):
        file_path = file_key
        if hasattr(self.scar, "path") and self.scar.path:
            file_path = FileUtils.join_paths(self.scar.path, file_path)
        return file_path

    def download_file_or_folder_from_s3(self):
        bucket_name = self.aws_properties.s3.input_bucket
        s3_file_list = self.aws_s3.get_bucket_file_list()
        for s3_file in s3_file_list:
            # Avoid download s3 'folders'
            if not s3_file.endswith('/'):
                file_path = self._get_download_file_path(file_key=s3_file)
                # make sure the path folders are created
                dir_path = os.path.dirname(file_path)
                if dir_path and not os.path.isdir(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                self.aws_s3.download_file(bucket_name, s3_file, file_path)

    def _update_all_functions(self, lambda_functions):
        for function_info in lambda_functions:
            self.aws_lambda.update_function_configuration(function_info)

    def _update_local_function_properties(self, function_info):
        self._reset_aws_properties()
#         """Update the defined properties with the AWS information."""
#         if function_info:
#             self.aws_properties.lambdaf.update_properties(**function_info)
#         if 'API_GATEWAY_ID' in self.aws_properties.lambdaf.environment['Variables']:
#             api_gtw_id = self.aws_properties.lambdaf.environment['Variables'].get('API_GATEWAY_ID',
#                                                                                   "")
#             if hasattr(self.aws_properties, 'api_gateway'):
#                 self.aws_properties.api_gateway.id = api_gtw_id
#             else:
#                 self.aws_properties.api_gateway = ApiGatewayProperties({'id' : api_gtw_id})

