#! /usr/bin/python

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
import unittest
import sys
import os
import base64
import json
from io import StringIO
from mock import MagicMock
from mock import patch

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.controller import AWS


class TestController(unittest.TestCase):

    def __init__(self, *args):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        unittest.TestCase.__init__(self, *args)

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.Lambda')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_invoke(self, load_tmp_config_file, lambda_cli, iam_cli):
        lcli = MagicMock(['call_http_endpoint'])
        response = MagicMock(["ok", "headers", "text"])
        response.ok.return_value = True
        response.text = base64.b64encode(b"text")
        response.headers = {'amz-lambda-request-id': 'id', 'amz-log-group-name': 'group', 'amz-log-stream-name': 'stream'}
        lcli.call_http_endpoint.return_value = response
        lambda_cli.return_value = lcli
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli

        AWS("invoke")
        self.assertEqual(lambda_cli.call_args_list[0][0][0]['lambda']['name'], "fname")

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.S3')
    @patch('scar.providers.aws.controller.APIGateway')
    @patch('scar.providers.aws.controller.CloudWatchLogs')
    @patch('scar.providers.aws.controller.Lambda')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    @patch('scar.providers.aws.controller.SupervisorUtils.check_supervisor_version')
    def test_init(self, check_supervisor_version, load_tmp_config_file, lambda_cli,
                  cloud_watch_cli, api_gateway_cli, s3_cli, iam_cli):
        lcli = MagicMock(['find_function', 'create_function', 'get_access_key', 'wait_function_active',
                          'add_invocation_permission_from_api_gateway', 'link_function_and_bucket'])
        lcli.find_function.return_value = False
        lcli.create_function.return_value = {'FunctionName': 'fname', 'FunctionArn': 'arn', 'Timeout': 10, 'MemorySize': 512}
        lcli.wait_function_active.return_value = True
        lambda_cli.return_value = lcli
        cwcli = MagicMock(['create_log_group', 'get_log_group_name'])
        cwcli.create_log_group.return_value = {'Payload': {'Body': 'body'}}
        cwcli.get_log_group_name.return_value = "group"
        agcli = MagicMock(['create_api_gateway'])
        s3cli = MagicMock(['create_bucket_and_folders', 'set_input_bucket_notification'])
        s3cli.create_bucket_and_folders.return_value = "name", "folders"
        s3_cli.return_value = s3cli
        api_gateway_cli.return_value = agcli
        cloud_watch_cli.return_value = cwcli
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "input": [{"storage_provider": "s3",
                                                                                          "path": "some"}],
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"},
                                                                    "api_gateway": {"name": "api_name"}}]}}
        check_supervisor_version.return_value = '1.4.2'

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        AWS("init")
        res = sys.stdout.getvalue()
        sys.stdout = old_stdout
        expected_res = "Function 'fname' successfully created.\n"
        expected_res += "Log group 'group' successfully created.\n"
        expected_res += "Wait function to be 'Active'\n"
        expected_res += "Function 'Active'\n"
        self.assertEqual(res, expected_res)
        self.assertEqual(lcli.create_function.call_count, 1)
        self.assertEqual(cwcli.create_log_group.call_count, 1)
        self.assertEqual(agcli.create_api_gateway.call_count, 1)
        self.assertEqual(iamcli.get_user_name_or_id.call_count, 1)
        self.assertEqual(s3cli.create_bucket_and_folders.call_args_list[0][0][0], 'some')

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.Lambda')
    @patch('scar.providers.aws.controller.S3')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    @patch('scar.providers.aws.controller.SupervisorUtils.check_supervisor_version')
    @patch('scar.providers.aws.controller.input')
    def test_run(self, mock_input, check_supervisor_version, load_tmp_config_file, s3_cli, lambda_cli, iam_cli):
        lcli = MagicMock(['launch_lambda_instance', 'launch_request_response_event', 'process_asynchronous_lambda_invocations'])
        payload = MagicMock(['read'])
        payload_json = {'headers': {'amz-log-group-name': 'group',
                                    'amz-log-stream-name': 'stream'},
                        'isBase64Encoded': False,
                        'body': 'body'}
        payload.read.return_value = json.dumps(payload_json).encode()
        response = {'LogResult': base64.b64encode(b"log"),
                    'Payload': payload,
                    'StatusCode': 200,
                    'ResponseMetadata': {'RequestId': 'reqid',
                                         'HTTPHeaders': {'x-amz-log-result': base64.b64encode(b"log2")}}}
        lcli.launch_lambda_instance.return_value = {'OutputFile': 'file', 'Response': response,
                                                    'IsAsynchronous': False}
        lambda_cli.return_value = lcli
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "input": [{"storage_provider": "s3",
                                                                                          "path": "some"}],
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        check_supervisor_version.return_value = '1.4.2'
        s3cli = MagicMock(['get_bucket_file_list', 'get_s3_event', 'get_s3_event_list'])
        s3cli.get_bucket_file_list.return_value = ['f1', 'f2']
        s3_cli.return_value = s3cli
        mock_input.return_value = "Y"

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        AWS("run")
        res = sys.stdout.getvalue()
        sys.stdout = old_stdout
        self.assertEqual(res, "This function has an associated 'S3' input bucket.\nFiles found: '['f1', 'f2']'\n")
        self.assertEqual(lambda_cli.call_args_list[0][0][0]['lambda']['name'], "fname")

        # Test run witout input file
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        AWS("run")
        res = sys.stdout.getvalue()
        sys.stdout = old_stdout
        self.assertEqual(res, 'Request Id: reqid\nLog Group Name: group\nLog Stream Name: stream\nbody\n')
        self.assertEqual(lambda_cli.call_args_list[1][0][0]['lambda']['name'], "fname")

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.Lambda')
    @patch('scar.providers.aws.controller.APIGateway')
    @patch('scar.providers.aws.controller.CloudWatchLogs')
    @patch('scar.providers.aws.controller.Batch')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_rm(self, load_tmp_config_file, batch_cli, cloud_watch_cli, api_gateway_cli, lambda_cli, iam_cli):
        lcli = MagicMock(['find_function', 'get_function_configuration', 'get_fdl_config', 'delete_function'])
        lcli.get_function_configuration.return_value = {'Environment': {'Variables': {'API_GATEWAY_ID': 'i'}}}
        lcli.find_function.return_value = True
        lcli.get_fdl_config.return_value = {'input': False}
        lcli.delete_function.return_value = ""
        lambda_cli.return_value = lcli
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "environment": {'Variables': {}},
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        agcli = MagicMock(['delete_api_gateway'])
        agcli.delete_api_gateway.return_value = ""
        api_gateway_cli.return_value = agcli
        cwcli = MagicMock(['delete_log_group', 'get_log_group_name'])
        cwcli.delete_log_group.return_value = ""
        cwcli.get_log_group_name.return_value = "gname"
        cloud_watch_cli.return_value = cwcli
        bcli = MagicMock(['exist_compute_environments', 'delete_compute_environment'])
        bcli.exist_compute_environments.return_value = True
        batch_cli.return_value = bcli

        AWS("rm")
        self.assertEqual(lambda_cli.call_args_list[0][0][0]['lambda']['name'], "fname")
        self.assertEqual(cwcli.delete_log_group.call_count, 1)
        self.assertEqual(agcli.delete_api_gateway.call_count, 1)
        self.assertEqual(lcli.delete_function.call_count, 1)
        self.assertEqual(bcli.delete_compute_environment.call_count, 1)

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.S3')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_get(self, load_tmp_config_file, s3_cli, iam_cli):
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "input": [{"storage_provider": "s3",
                                                                                          "path": "some"}],
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        s3cli = MagicMock(['get_bucket_file_list', 'download_file'])
        s3cli.get_bucket_file_list.return_value = ['f1', 'f2']
        s3_cli.return_value = s3cli

        AWS("get")
        self.assertEqual(s3cli.download_file.call_args_list[0][0], ('some', 'f1', 'f1'))
        self.assertEqual(s3cli.download_file.call_args_list[1][0], ('some', 'f2', 'f2'))

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.S3')
    @patch('os.path.isdir')
    @patch('scar.providers.aws.controller.FileUtils.get_all_files_in_directory')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_put(self, load_tmp_config_file, get_all_files_in_directory, is_dir, s3_cli, iam_cli):
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "input": [{"storage_provider": "s3",
                                                                                          "path": "some"}],
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        s3cli = MagicMock(['create_bucket_and_folders', 'upload_file'])
        s3cli.create_bucket_and_folders.return_value = 'bucket', 'folder'
        s3_cli.return_value = s3cli
        is_dir.return_value = True
        get_all_files_in_directory.return_value = ['f1', 'f2']

        AWS("put")
        self.assertEqual(s3cli.upload_file.call_args_list[0][1], {'bucket': 'bucket',
                                                                  'folder_name': 'folder',
                                                                  'file_path': 'f1'})
        self.assertEqual(s3cli.upload_file.call_args_list[1][1], {'bucket': 'bucket',
                                                                  'folder_name': 'folder',
                                                                  'file_path': 'f2'})

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.CloudWatchLogs')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_log(self, load_tmp_config_file, cloud_watch_cli, iam_cli):
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "input": [{"storage_provider": "s3",
                                                                                          "path": "some"}],
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        cwcli = MagicMock(['get_aws_logs'])
        cwcli.get_aws_logs.return_value = "log\nlog2"
        cloud_watch_cli.return_value = cwcli

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        AWS("log")
        res = sys.stdout.getvalue()
        sys.stdout = old_stdout
        self.assertEqual(cwcli.get_aws_logs.call_count, 1)
        self.assertEqual(res, 'log\nlog2\n')

    @patch('scar.providers.aws.controller.IAM')
    @patch('scar.providers.aws.controller.S3')
    @patch('scar.providers.aws.controller.ResourceGroups')
    @patch('scar.providers.aws.controller.Lambda')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_ls(self, load_tmp_config_file, lambda_cli, res_cli, s3_cli, iam_cli):
        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "input": [{"storage_provider": "s3",
                                                                                          "path": "some"}],
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        iamcli = MagicMock(['get_user_name_or_id'])
        iamcli.get_user_name_or_id.return_value = "username"
        iam_cli.return_value = iamcli
        s3cli = MagicMock(['get_bucket_file_list'])
        s3cli.get_bucket_file_list.return_value = ['f1', 'f2']
        s3_cli.return_value = s3cli
        rcli = MagicMock(['get_resource_arn_list'])
        res_cli.return_value = rcli
        rcli.get_resource_arn_list.return_value = ['rarn']



        old_stdout = sys.stdout
        sys.stdout = StringIO()
        AWS("ls")
        res = sys.stdout.getvalue()
        sys.stdout = old_stdout
        self.assertEqual(res, 'f1\nf2\n')

        load_tmp_config_file.return_value = {"functions": {"aws": [{"lambda": {"name": "fname",
                                                                               "supervisor": {"version": "latest"}},
                                                                    "iam": {"account_id": "id",
                                                                            "role": "role"}}]}}
        lcli = MagicMock(['get_all_functions'])
        lcli.get_all_functions.return_value = [{"lambda": {"environment": {"Variables": {"API_GATEWAY_ID": "aid",
                                                                                         "IMAGE_ID": "image"}},
                                                            "supervisor": {"version": "latest"},
                                                            "memory": 1024,
                                                            "timeout": 300,
                                                            "name": "fname"},
                                                "api_gateway": {"stage_name": "stage",
                                                                "region": "region"}}]
        lambda_cli.return_value = lcli

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        AWS("ls")
        res = sys.stdout.getvalue()
        sys.stdout = old_stdout
        expected_res = """AWS FUNCTIONS:
NAME      MEMORY    TIME  IMAGE_ID    API_URL                                                    SUPERVISOR_VERSION
------  --------  ------  ----------  ---------------------------------------------------------  --------------------
fname       1024     300  image       https://aid.execute-api.region.amazonaws.com/stage/launch  latest\n"""
        self.assertEqual(res, expected_res)
