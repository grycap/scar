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
from copy import deepcopy
from scar.cmdtemplate import Commands
from scar.providers.aws.apigateway import APIGateway
from scar.providers.aws.batchfunction import Batch
from scar.providers.aws.cloudwatchlogs import CloudWatchLogs
from scar.providers.aws.iam import IAM
from scar.providers.aws.lambdafunction import Lambda
# from scar.providers.aws.properties import AwsProperties, ScarProperties
from scar.providers.aws.resourcegroups import ResourceGroups
from scar.providers.aws.s3 import S3, get_bucket_and_folders
from scar.providers.aws.validators import AWSValidator
import scar.exceptions as excp
import scar.logger as logger
import scar.providers.aws.response as response_parser
from scar.utils import StrUtils, FileUtils, SupervisorUtils

_ACCOUNT_ID_REGEX = r'\d{12}'


def _get_owner(resources_info: Dict):
    return IAM(resources_info).get_user_name_or_id()


def _check_function_defined(resources_info: Dict):
    if Lambda(resources_info).find_function():
        raise excp.FunctionExistsError(function_name=resources_info.get('lambda', {}).get('name', ''))


def _check_function_not_defined(resources_info: Dict):
    if not Lambda(resources_info).find_function():
        raise excp.FunctionNotFoundError(function_name=resources_info.get('lambda', {}).get('name', ''))


def _choose_function(aws_resources: Dict) -> int:
    function_names = [resources_info.get('lambda').get('name') for resources_info in aws_resources]
    print("Please choose a function:")
    print("0) Apply to all")
    for idx, element in enumerate(function_names):
        print(f"{idx+1}) {element}")
    i = input("Enter number: ")
    if 0 <= int(i) <= len(function_names):
        return int(i) - 1
    return None


def _get_all_functions(resources_info: Dict):
    arn_list = ResourceGroups(resources_info).get_resource_arn_list(IAM(resources_info).get_user_name_or_id())
    return Lambda(resources_info).get_all_functions(arn_list)


def _check_preheat_function(resources_info: Dict):
    if resources_info.get('lambda').get('preheat', False):
        Lambda(resources_info).preheat_function()

############################################
###          ADD EXTRA PROPERTIES        ###
############################################


def _add_extra_aws_properties(scar: Dict, aws_resources: Dict) -> None:
    for resources_info in aws_resources:
        _add_tags(resources_info)
        _add_handler(resources_info)
        _add_account_id(resources_info)
        add_output(scar)
        _add_config_file_path(scar, resources_info)


def _add_tags(resources_info: Dict):
    resources_info['lambda']['tags'] = {"createdby": "scar", "owner": _get_owner(resources_info)}


def _add_account_id(resources_info: Dict):
    resources_info['iam']['account_id'] = StrUtils.find_expression(resources_info['iam']['role'], _ACCOUNT_ID_REGEX)


def _add_handler(resources_info: Dict):
    resources_info['lambda']['handler'] = f"{resources_info.get('lambda').get('name')}.lambda_handler"


def add_output(scar_info: Dict):
    scar_info['cli_output'] = response_parser.OutputType.PLAIN_TEXT.value
    if scar_info.get("json", False):
        scar_info['cli_output'] = response_parser.OutputType.JSON.value
    # Override json ouput if both of them are defined
    if scar_info.get("verbose", False):
        scar_info['cli_output'] = response_parser.OutputType.VERBOSE.value
    if scar_info.get("output_file", False):
        scar_info['cli_output'] = response_parser.OutputType.BINARY.value


def _add_config_file_path(scar_info: Dict, resources_info: Dict):
    if scar_info.get("conf_file", False):
        resources_info['lambda']['config_path'] = os.path.dirname(scar_info.get("conf_file"))
        # Update the path of the files based on the path of the yaml (if any)
        if resources_info['lambda'].get('init_script', False):
            resources_info['lambda']['init_script'] = FileUtils.join_paths(resources_info['lambda']['config_path'],
                                                                           resources_info['lambda']['init_script'])
        if resources_info['lambda'].get('image_file', False):
            resources_info['lambda']['image_file'] = FileUtils.join_paths(resources_info['lambda']['config_path'],
                                                                          resources_info['lambda']['image_file'])
        if resources_info['lambda'].get('run_script', False):
            resources_info['lambda']['run_script'] = FileUtils.join_paths(resources_info['lambda']['config_path'],
                                                                          resources_info['lambda']['run_script'])

############################################
###             AWS CONTROLLER           ###
############################################


class AWS(Commands):
    """AWS controller.
    Used to manage all the AWS calls and functionalities."""

    def __init__(self, func_call):
        self.raw_args = FileUtils.load_tmp_config_file()
        AWSValidator.validate_kwargs(self.raw_args)
        self.aws_resources = self.raw_args.get('functions', {}).get('aws', [])
        self.storage_providers = self.raw_args.get('storage_providers', {})
        self.scar_info = self.raw_args.get('scar', {})
        _add_extra_aws_properties(self.scar_info, self.aws_resources)
        # Call the user's command
        getattr(self, func_call)()

############################################
###              AWS COMMANDS            ###
############################################

    @excp.exception(logger)
    def init(self) -> None:
        for resources_info in self.aws_resources:
            resources_info = deepcopy(resources_info)
            # Check the specified supervisor version
            resources_info['lambda']['supervisor']['version'] = SupervisorUtils.check_supervisor_version(
                resources_info.get('lambda').get('supervisor').get('version'))
            _check_function_defined(resources_info)
            # We have to create the gateway before creating the function
            self._create_api_gateway(resources_info)
            self._create_lambda_function(resources_info)
            self._create_log_group(resources_info)
            self._create_s3_buckets(resources_info)
            # The api_gateway permissions must be added after the function is created
            self._add_api_gateway_permissions(resources_info)
            self._create_batch_environment(resources_info)
            _check_preheat_function(resources_info)

    @excp.exception(logger)
    def invoke(self):
        index = 0
        if len(self.aws_resources) > 1:
            index = _choose_function(self.aws_resources)
        if index >= 0:
            resources_info = self.aws_resources[index]
            response = Lambda(resources_info).call_http_endpoint()
            response_parser.parse_http_response(response,
                                                resources_info,
                                                self.scar_info)

    @excp.exception(logger)
    def run(self):
        index = 0
        if len(self.aws_resources) > 1:
            index = _choose_function(self.aws_resources)
        if index >= 0:
            resources_info = self.aws_resources[index]
            using_s3_bucket = False
            if resources_info.get('lambda').get('input', False):
                for storage in resources_info.get('lambda').get('input'):
                    if storage.get('storage_provider') == 's3':
                        print("This function has an associated 'S3' input bucket.")
                        response = input(f"Do you want to launch the function using the files in '{storage.get('path')}'? [Y/n] ")
                        if response in ('Y', 'y'):
                            using_s3_bucket = True
                            self._process_s3_input_bucket_calls(resources_info, storage)
            if not using_s3_bucket:
                response = Lambda(resources_info).launch_lambda_instance()
                if self.scar_info.get("output_file", False):
                    response['OutputFile'] = self.scar_info.get("output_file")
                response['OutputType'] = self.scar_info.get("cli_output")
                response_parser.parse_invocation_response(**response)

    @excp.exception(logger)
    def ls(self):
        # If a bucket is defined, then we list their files
        resources_info = self.aws_resources[0]
        if resources_info.get('lambda').get('input', False):
            file_list = S3(resources_info).get_bucket_file_list()
            for file_info in file_list:
                logger.info(file_info)
        else:
            # Return the resources of the region in the scar's configuration file
            aws_resources = _get_all_functions(self.aws_resources[0])
            response_parser.parse_ls_response(aws_resources, self.scar_info.get('cli_output'))

    @excp.exception(logger)
    def rm(self):
        if self.scar_info.get('all', False):
            # Return the resources of the region in the scar's configuration file
            for resources_info in _get_all_functions(self.aws_resources[0]):
                self._delete_resources(resources_info)
        else:
            # Selector disabled, delete all the functions defined in the file
            for resources_info in self.aws_resources:
                _check_function_not_defined(resources_info)
                self._delete_resources(resources_info)
            # index = 0
            # if len(self.aws_resources) > 1:
            #     index = _choose_function(self.aws_resources)
            # # -1 means apply to all functions
            # if index == -1:
            #     for resources_info in self.aws_resources:
            #         _check_function_not_defined(resources_info)
            #         self._delete_resources(resources_info)
            # else:
            #     print(self.aws_resources)
            #     resources_info = self.aws_resources[index]
            #     _check_function_not_defined(resources_info)
            #     self._delete_resources(resources_info)


    @excp.exception(logger)
    def log(self):
        index = 0
        if len(self.aws_resources) > 1:
            index = _choose_function(self.aws_resources)
        # We only return the logs of one function each time
        if index >= 0:
            logger.info(CloudWatchLogs(self.aws_resources[index]).get_aws_logs())

    @excp.exception(logger)
    def put(self):
        self._upload_file_or_folder_to_s3(self.aws_resources[0])

    @excp.exception(logger)
    def get(self):
        self._download_file_or_folder_from_s3(self.aws_resources[0])

#############################################################################
###                   Methods to create AWS resources                     ###
#############################################################################

    @excp.exception(logger)
    def _create_api_gateway(self, resources_info: Dict):
        if resources_info.get("api_gateway", {}).get('name', False):
            APIGateway(resources_info).create_api_gateway()

    @excp.exception(logger)
    def _create_lambda_function(self, resources_info: Dict) -> None:
        lambda_client = Lambda(resources_info)
        response = lambda_client.create_function()
        response_parser.parse_lambda_function_creation_response(response,
                                                                self.scar_info.get('cli_output'),
                                                                lambda_client.get_access_key())

    @excp.exception(logger)
    def _create_log_group(self, resources_info: Dict) -> None:
        cloudwatch_logs = CloudWatchLogs(resources_info)
        response = cloudwatch_logs.create_log_group()
        response_parser.parse_log_group_creation_response(response,
                                                          cloudwatch_logs.get_log_group_name(),
                                                          self.scar_info.get('cli_output'))

    @excp.exception(logger)
    def _create_s3_buckets(self, resources_info: Dict) -> None:
        if resources_info.get('lambda').get('input', False):
            s3_service = S3(resources_info)
            for bucket in resources_info.get('lambda').get('input'):
                if bucket.get('storage_provider') == 's3':
                    bucket_name, folders = s3_service.create_bucket_and_folders(bucket.get('path'))
                    lambda_client = Lambda(resources_info)
                    lambda_client.link_function_and_bucket(bucket_name)
                    # Check if function is already available
                    logger.info("Wait function to be 'Active'")
                    if not lambda_client.wait_function_active(resources_info.get('lambda').get('arn')):
                        logger.error("Timeout waiting function.")
                    else:
                        logger.info("Function 'Active'")
                    s3_service.set_input_bucket_notification(bucket_name, folders)
                    if not folders:
                        logger.info(f'Input bucket "{bucket_name}" successfully created')

        if resources_info.get('lambda').get('output', False):
            s3_service = S3(resources_info)
            for bucket in resources_info.get('lambda').get('output'):
                if bucket.get('storage_provider') == 's3':
                    bucket_name, folders = s3_service.create_bucket_and_folders(bucket.get('path'))
                    if not folders:
                        logger.info(f'Output bucket "{bucket_name}" successfully created')

    @excp.exception(logger)
    def _add_api_gateway_permissions(self, resources_info: Dict):
        if resources_info.get("api_gateway").get('name', False):
            Lambda(resources_info).add_invocation_permission_from_api_gateway()

    @excp.exception(logger)
    def _create_batch_environment(self, resources_info: Dict) -> None:
        mode = resources_info.get('lambda').get('execution_mode')
        if mode in ("batch", "lambda-batch"):
            Batch(resources_info).create_batch_environment()

#############################################################################
###                   Methods to delete AWS resources                     ###
#############################################################################

    def _delete_resources(self, resources_info: Dict) -> None:
        # Delete associated api
        self._delete_api_gateway(resources_info)
        # Delete associated log
        self._delete_logs(resources_info)
        # Delete associated notifications
        self._delete_bucket_notifications(resources_info)
        # Delete function
        self._delete_lambda_function(resources_info)
        # Delete resources batch
        self._delete_batch_resources(resources_info)

    def _delete_api_gateway(self, resources_info: Dict) -> None:
        api_gateway_id = Lambda(resources_info).get_function_configuration().get('Environment').get('Variables').get('API_GATEWAY_ID')
        if api_gateway_id:
            resources_info['lambda']['environment']['Variables']['API_GATEWAY_ID'] = api_gateway_id
            response = APIGateway(resources_info).delete_api_gateway()
            response_parser.parse_delete_api_response(response,
                                                      api_gateway_id,
                                                      self.scar_info.get('cli_output'))

    def _delete_logs(self, resources_info: Dict):
        cloudwatch_logs = CloudWatchLogs(resources_info)
        log_group_name = cloudwatch_logs.get_log_group_name(resources_info.get('lambda').get('name'))
        response = cloudwatch_logs.delete_log_group(log_group_name)
        response_parser.parse_delete_log_response(response,
                                                  log_group_name,
                                                  self.scar_info.get('cli_output'))

    def _delete_bucket_notifications(self, resources_info: Dict) -> None:
        lambda_client = Lambda(resources_info)
        function_name = resources_info.get('lambda').get('name')
        resources_info['lambda']['arn'] = lambda_client.get_function_configuration(function_name).get('FunctionArn')
        if not resources_info.get('lambda').get('input'):
            resources_info['lambda']['input'] = lambda_client.get_fdl_config(function_name).get('input', False)
        if resources_info.get('lambda').get('input'):
            for input_storage in resources_info.get('lambda').get('input'):
                if input_storage.get('storage_provider') == 's3':
                    bucket_name = input_storage.get('path').split("/", 1)[0]
                    S3(resources_info).delete_bucket_notification(bucket_name)

    def _delete_lambda_function(self, resources_info: Dict) -> None:
        response = Lambda(resources_info).delete_function()
        response_parser.parse_delete_function_response(response,
                                                       resources_info.get('lambda').get('name'),
                                                       self.scar_info.get('cli_output'))

    def _delete_batch_resources(self, resources_info: Dict) -> None:
        batch = Batch(resources_info)
        if batch.exist_compute_environments():
            batch.delete_compute_environment()

###########################################################
###            Methods to manage S3 resources           ###
###########################################################

    def _process_s3_input_bucket_calls(self, resources_info: Dict, storage: Dict) -> None:
        s3_service = S3(resources_info)
        lambda_service = Lambda(resources_info)
        s3_file_list = s3_service.get_bucket_file_list(storage)
        bucket_name, _ = get_bucket_and_folders(storage.get('path'))
        logger.info(f"Files found: '{s3_file_list}'")
        # First do a request response invocation to prepare the lambda environment
        if s3_file_list:
            s3_event = s3_service.get_s3_event(bucket_name, s3_file_list.pop(0))
            lambda_service.launch_request_response_event(s3_event)
        # If the list has more elements, invoke functions asynchronously
        if s3_file_list:
            s3_event_list = s3_service.get_s3_event_list(bucket_name, s3_file_list)
            lambda_service.process_asynchronous_lambda_invocations(s3_event_list)

    def _upload_file_or_folder_to_s3(self, resources_info: Dict) -> None:
        path_to_upload = self.scar_info.get('path')
        files = [path_to_upload]
        if os.path.isdir(path_to_upload):
            files = FileUtils.get_all_files_in_directory(path_to_upload)
        s3_service = S3(resources_info)
        storage_path = resources_info.get('lambda').get('input')[0].get('path')
        bucket, folder = s3_service.create_bucket_and_folders(storage_path)
        for file_path in files:
            s3_service.upload_file(bucket=bucket, folder_name=folder, file_path=file_path)

    def _get_download_file_path(self, file_key=None):
        file_path = file_key
        if self.scar_info.get('path', False):
            file_path = FileUtils.join_paths(self.scar_info.get('path'), file_path)
        return file_path

    def _download_file_or_folder_from_s3(self, resources_info: Dict) -> None:

        s3_service = S3(resources_info)
        s3_file_list = s3_service.get_bucket_file_list()
        for s3_file in s3_file_list:
            # Avoid download s3 'folders'
            if not s3_file.endswith('/'):
                file_path = self._get_download_file_path(file_key=s3_file)
                # make sure the path folders are created
                dir_path = os.path.dirname(file_path)
                if dir_path and not os.path.isdir(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                bucket, _ = get_bucket_and_folders(resources_info.get('lambda').get('input')[0].get('path'))
                s3_service.download_file(bucket, s3_file, file_path)
