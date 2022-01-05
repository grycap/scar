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
from mock import MagicMock
from mock import patch
from scar.providers.aws import response

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
    def test_init(self, load_tmp_config_file, lambda_cli, cloud_watch_cli, api_gateway_cli, s3_cli, iam_cli):
        lcli = MagicMock(['find_function', 'create_function', 'get_access_key',
                          'add_invocation_permission_from_api_gateway', 'link_function_and_bucket'])
        lcli.find_function.return_value = False
        lcli.create_function.return_value = {'FunctionName': 'fname', 'FunctionArn': 'arn', 'Timeout': 10, 'MemorySize': 512}
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
        AWS("init")
        self.assertEqual(lcli.create_function.call_count, 1)
        self.assertEqual(cwcli.create_log_group.call_count, 1)
        self.assertEqual(agcli.create_api_gateway.call_count, 1)
        self.assertEqual(iamcli.get_user_name_or_id.call_count, 1)
        self.assertEqual(s3cli.create_bucket_and_folders.call_args_list[0][0][0], 'some')
