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
from mock import patch

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.apigateway import APIGateway


class TestAPIGateway(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        ecr = APIGateway({})
        self.assertEqual(type(ecr.client.client).__name__, "APIGateway")

    @patch('boto3.Session')
    def test_create_api_gateway(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['create_rest_api', 'get_resources', 'create_resource', 'put_method',
                            'put_integration', 'create_deployment'])
        session.client.return_value = client
        boto_session.return_value = session
        apig = APIGateway({'lambda': {'name': 'fname',
                                      'environment': {'Variables': {}}},
                           'api_gateway': {'name': 'apiname',
                                           'path_part': 'path',
                                           'http_method': 'ANY',
                                           'stage_name': 'scar',
                                           'integration': {'uri': 'arn:aws:apigateway...'}}})
        apig.client.client.create_rest_api.return_value = {'id': 'apiid'}
        apig.client.client.create_resource.return_value = {'id': 'resid'}
        apig.client.client.get_resources.return_value = {'items': [{'path': '/', 'id': 'rid'}]}

        apig.create_api_gateway()

        res = {'name': 'apiname',
               'description': 'API created automatically with SCAR',
               'endpointConfiguration': {'types': ['REGIONAL']}}
        self.assertEqual(apig.client.client.create_rest_api.call_args_list[0][1], res)
        res = {'parentId': 'rid', 'pathPart': 'path', 'restApiId': 'apiid'}
        self.assertEqual(apig.client.client.create_resource.call_args_list[0][1], res)
        res = {'httpMethod': 'ANY', 'resourceId': 'resid', 'restApiId': 'apiid'}
        self.assertEqual(apig.client.client.put_method.call_args_list[0][1], res)
        res = {'restApiId': 'apiid', 'resourceId': 'resid', 'httpMethod': 'ANY', 'uri': 'arn:aws:apigateway...'}
        self.assertEqual(apig.client.client.put_integration.call_args_list[0][1], res)
        res = {'restApiId': 'apiid', 'stageName': 'scar'}
        self.assertEqual(apig.client.client.create_deployment.call_args_list[0][1], res)

    @patch('boto3.Session')
    def test_delete_api_gateway(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['delete_rest_api'])
        session.client.return_value = client
        boto_session.return_value = session
        apig = APIGateway({'lambda': {'name': 'fname',
                                      'environment': {'Variables': {'API_GATEWAY_ID': 'apiid'}}}})

        apig.delete_api_gateway()

        res = {'restApiId': 'apiid'}
        self.assertEqual(apig.client.client.delete_rest_api.call_args_list[0][1], res)
