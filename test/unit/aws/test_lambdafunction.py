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
import tempfile
from mock import MagicMock
from mock import patch
from zipfile import ZipFile
from scar.providers.aws import clients

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.lambdafunction import Lambda


class TestLambda(unittest.TestCase):

    def __init__(self, *args):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        cli = Lambda({'lambda': {'name': 'fname',
                                 'supervisor': {'version': '1.4.2'}}})
        self.assertEqual(type(cli.client.client).__name__, "Lambda")

    @patch('boto3.Session')
    @patch('scar.providers.aws.launchtemplates.SupervisorUtils.download_supervisor')
    @patch('scar.providers.aws.udocker.Udocker.prepare_udocker_image')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    @patch('docker.from_env')
    def test_create_function(self, from_env, load_tmp_config_file, prepare_udocker_image, download_supervisor, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['list_layers', 'publish_layer_version', 'get_bucket_location', 'put_object',
                            'create_function', 'list_layer_versions'])
        session.client.return_value = client
        boto_session.return_value = session
        load_tmp_config_file.return_value = {}

        tests_path = os.path.dirname(os.path.abspath(__file__))
        download_supervisor.return_value = os.path.join(tests_path, "../../files/supervisor.zip")
        lam = Lambda({'lambda': {'name': 'fname',
                                 'runtime': 'python3.7',
                                 'timeout': 300,
                                 'memory': 512,
                                 'layers': [],
                                 'tags': {'createdby': 'scar'},
                                 'handler': 'some.handler',
                                 'description': 'desc',
                                 'deployment': {'bucket': 'someb',
                                                'max_s3_payload_size': 262144000},
                                 'environment': {'Variables': {'IMAGE_ID': 'some/image'}},
                                 'container': {'image': 'some/image:tag',
                                               'image_file': 'some.tgz',
                                               'environment': {'Variables': {}}},
                                 'supervisor': {'version': '1.4.2',
                                                'layer_name': 'layername'}},
                        'iam': {'role': 'iamrole'}})
        lam.client.client.list_layers.return_value = {'Layers': [{'LayerName': 'layername'}]}
        lam.client.client.publish_layer_version.return_value = {'LayerVersionArn': '1'}
        lam.client.client.create_function.return_value = {'FunctionArn': 'farn'}
        lam.client.client.list_layer_versions.return_value = {'LayerVersions': []}
        
        lam.create_function()

        res = {'FunctionName': 'fname',
               'Role': 'iamrole',
               'Environment': {'Variables': {'IMAGE_ID': 'some/image:tag'}},
               'Description': 'desc',
               'Timeout': 300,
               'MemorySize': 512,
               'Tags': {'createdby': 'scar'},
               'Code': {'S3Bucket': 'someb', 'S3Key': 'lambda/fname.zip'},
               'Runtime': 'python3.7',
               'Handler': 'some.handler',
               'Layers': ['1']}
        self.assertEqual(lam.client.client.create_function.call_args_list[0][1], res)

        self.assertEqual(lam.client.client.publish_layer_version.call_args_list[0][1]['LayerName'], "layername")
        self.assertEqual(lam.client.client.publish_layer_version.call_args_list[0][1]['Description'], "1.4.2")
        self.assertEqual(len(lam.client.client.publish_layer_version.call_args_list[0][1]['Content']['ZipFile']), 99662)

        # Test container image
        client = MagicMock(['create_repository', 'describe_registry', 'get_authorization_token'])
        docker = MagicMock(['login', 'images'])
        docker.images = MagicMock(['build', 'push'])
        from_env.return_value = docker
        session.client.return_value = client
        lam.resources_info['lambda']['runtime'] = 'image'

        client.create_repository.return_value = {"repository": {"repositoryUri": "repouri"}}
        client.describe_registry.return_value = {'registryId': 'regid'}
        client.get_authorization_token.return_value = {'authorizationData': [{'authorizationToken': 'QVdTOnRva2Vu'}]}

        lam.create_function()
        res = {'FunctionName': 'fname',
               'Role': 'iamrole',
               'Environment': {'Variables': {'IMAGE_ID': 'repouri:latest'}},
               'Description': 'desc',
               'Timeout': 300,
               'MemorySize': 512,
               'PackageType': 'Image',
               'Tags': {'createdby': 'scar'},
               'Code': {'ImageUri': 'repouri:latest'}}
        self.assertEqual(lam.client.client.create_function.call_args_list[1][1], res)
        self.assertEqual(docker.images.push.call_args_list[0][0][0], "repouri")
        self.assertEqual(docker.images.build.call_args_list[0][1]['tag'], "repouri")
