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
from scar.providers.aws.properties import ApiGatewayProperties
import scar.exceptions as excp
import scar.logger as logger
import scar.providers.aws.response as response_parser
from scar.utils import lazy_property, StrUtils, FileUtils

_ACCOUNT_ID_REGEX = r'\d{12}'


def _get_storage_provider_id(storage_provider: str, env_vars: Dict) -> str:
    """Searches the storage provider id in the environment variables:
        get_provider_id(S3, {'STORAGE_AUTH_S3_USER_41807' : 'scar'})
        returns -> 41807"""
    res = ""
    for env_key in env_vars.keys():
        if env_key.startswith(f'STORAGE_AUTH_{storage_provider}'):
            res = env_key.split('_', 4)[-1]
            break
    return res


def _get_owner(function):
    return _get_iam_client(function).get_user_name_or_id()

############################################
###              BOTO CLIENTS            ###
############################################


def _get_iam_client(aws_properties: Dict) -> IAM:
    return IAM(aws_properties)


def _get_lambda_client(aws_properties: Dict=None) -> Lambda:
    if not aws_properties:
        aws_properties = {}
    return Lambda(aws_properties)


def _get_api_gateway_client(aws_properties: Dict) -> APIGateway:
    return APIGateway(aws_properties)


def _get_s3_client(aws_properties: Dict) -> S3:
    return S3(aws_properties)


def _get_resource_groups_client(aws_properties: Dict) -> ResourceGroups:
    return ResourceGroups(aws_properties)


def _get_cloudwatch_logs_client(aws_properties: Dict) -> CloudWatchLogs:
    return CloudWatchLogs(aws_properties)

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


def _add_tags(function):
    function['lambda']['tags'] = {"createdby": "scar",
                                  "owner": _get_owner(function)}


def _add_account_id(function):
    function['iam']['account_id'] = StrUtils.find_expression(function['iam']['role'],
                                                              _ACCOUNT_ID_REGEX)


def _add_handler(function):
    function['lambda']['handler'] = f"{function.get('lambda', {}).get('name', '')}.lambda_handler"


def _add_output(scar_properties, function):
    function['lambda']['output'] = response_parser.OutputType.PLAIN_TEXT.value
    if scar_properties.get("json", False):
        function['lambda']['output'] = response_parser.OutputType.JSON.value
    # Override json ouput if both of them are defined
    if scar_properties.get("verbose", False):
        function['lambda']['output'] = response_parser.OutputType.VERBOSE.value
    if scar_properties.get("output_file", False):
        function['lambda']['output'] = response_parser.OutputType.BINARY.value
        function['lambda']['output_file'] = scar_properties.get("output_file")


def _add_config_file_path(scar_properties, function):
    if scar_properties.get("conf_file", False):
        function['lambda']['config_path'] = os.path.dirname(scar_properties.get("conf_file"))
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

############################################
###             AWS CONTROLLER           ###
############################################


class AWS(Commands):
    """AWS controller.
    Used to manage all the AWS calls and functionalities."""

    @lazy_property
    def batch(self):
        batch = Batch(self.aws_properties,
                      self.scar.supervisor_version)
        return batch

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
        for function in self.aws_functions:
            lambda_client = _get_lambda_client(function)
            if lambda_client.find_function():
                raise excp.FunctionExistsError(function_name=function.get('lambda', {}).get('name', ''))
            # We have to create the gateway before creating the function
            # self._create_api_gateway(function)
            self._create_lambda_function(function, lambda_client)
            self._create_log_group(function)
            # self._create_s3_buckets()
            # The api_gateway permissions are added after the function is created
            # self._add_api_gateway_permissions()
            # self._create_batch_environment()
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
        if len(self.aws_functions) > 1:
            logger.info("Not allowed yet")
        else:
            lambda_client = _get_lambda_client(self.aws_functions[0])
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
                                          self.aws_functions[0].get('lambda').get('output'))        
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
            function = self.aws_functions[0]
            lambda_client = _get_lambda_client(function)
#             function_info = lambda_client.get_function_info(function.get('lambda').get('name'))
            if not lambda_client.find_function(function.get('lambda').get('name')):
                raise excp.FunctionNotFoundError(function_name=function.get('lambda').get('name'))
            self._delete_resources(function)            
        
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
        function = self.aws_functions[0]
        arn_list = _get_resource_groups_client(function).get_resource_arn_list(_get_iam_client(function).get_user_name_or_id())
        return _get_lambda_client(function).get_all_functions(arn_list)

    def _get_batch_logs(self) -> str:
        logs = ""
        if hasattr(self.aws_properties.cloudwatch, "request_id") and \
        self.batch.exist_job(self.aws_properties.cloudwatch.request_id):
            batch_jobs = self.batch.describe_jobs(self.aws_properties.cloudwatch.request_id)
            logs = self.cloudwatch_logs.get_batch_job_log(batch_jobs["jobs"])
        return logs

    @excp.exception(logger)
    def _create_s3_buckets(self):
        if hasattr(self.aws_properties, "s3"):
            if hasattr(self.aws_properties.s3, "input_bucket"):
                self.aws_s3.create_input_bucket(create_input_folder=True)
                self.aws_lambda.link_function_and_input_bucket()
                self.aws_s3.set_input_bucket_notification()
            if hasattr(self.aws_properties.s3, "output_bucket"):
                self.aws_s3.create_output_bucket()

    def _add_api_gateway_permissions(self):
        if hasattr(self.aws_properties, "api_gateway"):
            self.aws_lambda.add_invocation_permission_from_api_gateway()

    def _create_batch_environment(self):
        if self.aws_properties.execution_mode == "batch" or \
        self.aws_properties.execution_mode == "lambda-batch":
            self.batch.create_batch_environment()

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
        """Update the defined properties with the AWS information."""
        if function_info:
            self.aws_properties.lambdaf.update_properties(**function_info)
        if 'API_GATEWAY_ID' in self.aws_properties.lambdaf.environment['Variables']:
            api_gtw_id = self.aws_properties.lambdaf.environment['Variables'].get('API_GATEWAY_ID',
                                                                                  "")
            if hasattr(self.aws_properties, 'api_gateway'):
                self.aws_properties.api_gateway.id = api_gtw_id
            else:
                self.aws_properties.api_gateway = ApiGatewayProperties({'id' : api_gtw_id})

#############################################################################
###                   Methods to create AWS resources                     ###
#############################################################################

    def _create_api_gateway(self, function: Dict):
        if function.get("api_gateway", {}).get('name', False):
            _get_api_gateway_client(function).create_api_gateway()
            
    @excp.exception(logger)
    def _create_lambda_function(self, function: Dict, lambda_client: Lambda) -> None:
        response = lambda_client.create_function()
        response_parser.parse_lambda_function_creation_response(response,
                                                                function,
                                                                lambda_client.get_access_key())            

    @excp.exception(logger)
    def _create_log_group(self, function: Dict):
        cloudwatch_logs = _get_cloudwatch_logs_client(function)
        response = cloudwatch_logs.create_log_group()
        response_parser.parse_log_group_creation_response(response,
                                                          cloudwatch_logs.get_log_group_name(),
                                                          function.get('lambda').get('output'))
#############################################################################
###                   Methods to delete AWS resources                     ###
#############################################################################

    def _delete_all_resources(self):
        for function_info in self._get_all_functions():
            self._delete_resources(function_info)

    def _delete_resources(self, function: Dict) -> None:
#         function_name = function_info['FunctionName']

#         # Delete associated api
#         self._delete_api_gateway(function_info['Environment']['Variables'])
        # Delete associated log
        self._delete_logs(function)
#         # Delete associated notifications
#         self._delete_bucket_notifications(function_info['FunctionArn'],
#                                           function_info['Environment']['Variables'])
        # Delete function
        self._delete_lambda_function(function)
#         # Delete resources batch
#         self._delete_batch_resources(function_name)

    def _delete_api_gateway(self, function_env_vars):
        api_gateway_id = function_env_vars.get('API_GATEWAY_ID')
        if api_gateway_id:
            response = self.api_gateway.delete_api_gateway(api_gateway_id)
            response_parser.parse_delete_api_response(response, api_gateway_id,
                                                      self.aws_properties.output)

    def _delete_logs(self, function: Dict):
        cloudwatch_logs = _get_cloudwatch_logs_client(function)
        log_group_name = cloudwatch_logs.get_log_group_name(function.get('lambda').get('name'))
        response = cloudwatch_logs.delete_log_group(log_group_name)
        response_parser.parse_delete_log_response(response,
                                                  log_group_name,
                                                  function.get('lambda').get('output'))

    def _delete_bucket_notifications(self, function_arn, function_env_vars):
        s3_provider_id = _get_storage_provider_id('S3', function_env_vars)
        input_bucket_id = f'STORAGE_PATH_INPUT_{s3_provider_id}' if s3_provider_id else ''
        if input_bucket_id in function_env_vars:
            input_path = function_env_vars[input_bucket_id]
            input_bucket_name = input_path.split("/", 1)[0]
            self.aws_s3.delete_bucket_notification(input_bucket_name, function_arn)

    def _delete_lambda_function(self, function: Dict):
        response = _get_lambda_client(function).delete_function(function.get('lambda').get('name'))
        response_parser.parse_delete_function_response(response,
                                                       function.get('lambda').get('name'),
                                                       function.get('lambda').get('output'))

    def _delete_batch_resources(self, function_name):
        if self.batch.exist_compute_environments(function_name):
            self.batch.delete_compute_environment(function_name)
