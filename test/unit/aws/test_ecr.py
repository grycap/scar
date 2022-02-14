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
from mock import MagicMock
from mock import patch, call

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.ecr import ECR


class TestECR(unittest.TestCase):

    def __init__(self, *args):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        ecr = ECR({})
        self.assertEqual(type(ecr.client.client).__name__, "ECR")

    def _init_mocks(self, call_list):
        session = MagicMock(['client'])
        client = MagicMock(call_list)
        session.client.return_value = client
        return session   

    @patch('boto3.Session')
    def test_get_authorization_token(self, boto_session):
        boto_session.return_value = self._init_mocks(['get_authorization_token'])
        ecr = ECR({})
        token = "QVdTOnRva2Vu"
        ecr.client.client.get_authorization_token.return_value = {'authorizationData': [{'authorizationToken': token}]}
        self.assertEqual(ecr.get_authorization_token(), ["AWS", "token"])

    @patch('boto3.Session')
    def test_get_registry_url(self, boto_session):
        boto_session.return_value = self._init_mocks(['describe_registry'])
        ecr = ECR({})
        ecr.client.client.describe_registry.return_value = {'registryId': 'REG_ID'}
        self.assertEqual(ecr.get_registry_url(), "REG_ID.dkr.ecr.us-east-1.amazonaws.com")

    @patch('boto3.Session')
    def test_get_repository_uri(self, boto_session):
        boto_session.return_value = self._init_mocks(['describe_repositories'])
        ecr = ECR({})
        ecr.client.client.describe_repositories.return_value = {'repositories': [{'repositoryUri': 'URI'}]}
        self.assertEqual(ecr.get_repository_uri('repo_name'), 'URI')
        self.assertEqual(ecr.client.client.describe_repositories.call_args_list[0], call(repositoryNames=['repo_name']))

    @patch('boto3.Session')
    def test_create_repository(self, boto_session):
        boto_session.return_value = self._init_mocks(['create_repository'])
        ecr = ECR({})
        ecr.client.client.create_repository.return_value = {'repository': {'repositoryUri': 'URI'}}
        self.assertEqual(ecr.create_repository('repo_name'), 'URI')
        self.assertEqual(ecr.client.client.create_repository.call_args_list[0], call(repositoryName='repo_name'))

    @patch('boto3.Session')
    def test_delete_repository(self, boto_session):
        boto_session.return_value = self._init_mocks(['delete_repository'])
        ecr = ECR({})
        ecr.delete_repository('repo_name')
        self.assertEqual(ecr.client.client.delete_repository.call_args_list[0], call(repositoryName='repo_name', force=True))
