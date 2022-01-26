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

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.utils import StrUtils
from scar.providers.aws.lambdafunction import Lambda


class TestLambda(unittest.TestCase):

    def __init__(self, *args):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        unittest.TestCase.__init__(self, *args)

    def _init_mocks(self, call_list):
        session = MagicMock(['client'])
        client = MagicMock(call_list)
        session.client.return_value = client

        resource_info = {'lambda': {'name': 'fname',
                                    'runtime': 'python3.7',
                                    'timeout': 300,
                                    'memory': 512,
                                    'layers': [],
                                    'log_type': 'Tail',
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
                         'ecr': {"delete_image": True},
                         'api_gateway': {'endpoint': 'https://{api_id}.{api_region}/{stage_name}/l',
                                         'region': 'us-east-1',
                                         'stage_name': 'scar'},
                         'iam': {'role': 'iamrole'}}

        lam = Lambda(resource_info)
        return session, lam, client

    def test_init(self):
        cli = Lambda({'lambda': {'name': 'fname',
                                 'supervisor': {'version': '1.4.2'}}})
        self.assertEqual(type(cli.client.client).__name__, "Lambda")

    @patch('boto3.Session')
    @patch('scar.providers.aws.launchtemplates.SupervisorUtils.download_supervisor')
    @patch('scar.providers.aws.udocker.Udocker.prepare_udocker_image')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_create_function(self, load_tmp_config_file, prepare_udocker_image,
                             download_supervisor, boto_session):
        session, lam, _ = self._init_mocks(['list_layers', 'publish_layer_version', 'get_bucket_location', 'put_object',
                                            'create_function', 'list_layer_versions'])
        boto_session.return_value = session

        load_tmp_config_file.return_value = {}

        tests_path = os.path.dirname(os.path.abspath(__file__))
        download_supervisor.return_value = os.path.join(tests_path, "../../files/supervisor.zip")

        lam.client.client.list_layers.return_value = {'Layers': [{'LayerName': 'layername'}]}
        lam.client.client.publish_layer_version.return_value = {'LayerVersionArn': '1'}
        lam.client.client.create_function.return_value = {'FunctionArn': 'farn'}
        lam.client.client.list_layer_versions.return_value = {'LayerVersions': []}

        lam.create_function()

        fdl = {"storage_providers": {},
               "name": "fname",
               "runtime": "python3.7",
               "timeout": 300,
               "memory": 512,
               "layers": ["1"],
               "log_type": "Tail",
               "tags": {"createdby": "scar"},
               "handler": "some.handler",
               "description": "desc",
               "deployment": {"bucket": "someb", "max_s3_payload_size": 262144000},
               "environment": {"Variables": {"IMAGE_ID": "some/image:tag"}},
               "container": {"image": "some/image:tag", "image_file": "some.tgz", "environment": {"Variables": {}}},
               "supervisor": {"version": "1.4.2", "layer_name": "layername"}}
        res = {'FunctionName': 'fname',
               'Role': 'iamrole',
               'Environment': {'Variables': {'IMAGE_ID': 'some/image:tag',
                                             'FDL': StrUtils.dict_to_base64_string(fdl)}},
               'Description': 'desc',
               'Timeout': 300,
               'MemorySize': 512,
               'Tags': {'createdby': 'scar'},
               'Code': {'S3Bucket': 'someb', 'S3Key': 'lambda/fname.zip'},
               'Runtime': 'python3.7',
               'Handler': 'some.handler',
               'Architectures': ['x86_64'],
               'Layers': ['1']}
        self.assertEqual(lam.client.client.create_function.call_args_list[0][1], res)

        self.assertEqual(lam.client.client.publish_layer_version.call_args_list[0][1]['LayerName'], "layername")
        self.assertEqual(lam.client.client.publish_layer_version.call_args_list[0][1]['Description'], "1.4.2")
        self.assertEqual(len(lam.client.client.publish_layer_version.call_args_list[0][1]['Content']['ZipFile']), 99662)

    @patch('boto3.Session')
    @patch('scar.providers.aws.launchtemplates.SupervisorUtils.download_supervisor_asset')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    @patch('scar.providers.aws.lambdafunction.FileUtils.unzip_folder')
    @patch('docker.from_env')
    def test_create_function_image(self, from_env, unzip_folder, load_tmp_config_file,
                                   download_supervisor_asset, boto_session):
        session, lam, client = self._init_mocks(['create_function', 'create_repository',
                                                 'describe_registry', 'get_authorization_token'])
        boto_session.return_value = session

        load_tmp_config_file.return_value = {}

        tests_path = os.path.dirname(os.path.abspath(__file__))
        download_supervisor_asset.return_value = os.path.join(tests_path, "../../files/supervisor.zip")

        docker = MagicMock(['login', 'images'])
        docker.images = MagicMock(['build', 'push'])
        from_env.return_value = docker

        client.create_repository.return_value = {"repository": {"repositoryUri": "repouri"}}
        client.describe_registry.return_value = {'registryId': 'regid'}
        client.get_authorization_token.return_value = {'authorizationData': [{'authorizationToken': 'QVdTOnRva2Vu'}]}

        lam.resources_info['lambda']['runtime'] = 'image'
        lam.resources_info['lambda']['supervisor']['version'] = lam.supervisor_version = '1.5.0'
        lam.resources_info['lambda']['vpc'] = {'SubnetIds': ['subnet'],
                                               'SecurityGroupIds': ['sg']}
        lam.resources_info['lambda']['file_system'] = [{'Arn': 'efsaparn', '': '/mnt'}]

        lam.create_function()
        fdl = {"storage_providers": {},
               "name": "fname",
               "runtime": "image",
               "timeout": 300,
               "memory": 512,
               "layers": [],
               "log_type": "Tail",
               "tags": {"createdby": "scar"},
               "handler": "some.handler",
               "description": "desc",
               "deployment": {"bucket": "someb", "max_s3_payload_size": 262144000},
               "environment": {"Variables": {"IMAGE_ID": "repouri:latest"}},
               "container": {"image": "repouri:latest", "image_file": "some.tgz", "environment": {"Variables": {}}},
               "supervisor": {"version": "1.5.0", "layer_name": "layername"},
               "vpc": {"SubnetIds": ["subnet"], "SecurityGroupIds": ["sg"]},
               "file_system": [{'Arn': 'efsaparn', '': '/mnt'}],
               "ecr": {"delete_image": True}}
        res = {'FunctionName': 'fname',
               'Role': 'iamrole',
               'Environment': {'Variables': {'IMAGE_ID': 'repouri:latest',
                                             'FDL': StrUtils.dict_to_base64_string(fdl)}},
               'Description': 'desc',
               'Timeout': 300,
               'MemorySize': 512,
               'PackageType': 'Image',
               'Tags': {'createdby': 'scar'},
               'Architectures': ['x86_64'],
               'VpcConfig': {'SubnetIds': ['subnet'],
                             'SecurityGroupIds': ['sg']},
               'FileSystemConfigs': [{'Arn': 'efsaparn', '': '/mnt'}],
               'Code': {'ImageUri': 'repouri:latest'}}
        self.assertEqual(lam.client.client.create_function.call_args_list[0][1], res)
        self.assertEqual(docker.images.push.call_args_list[0][0][0], "repouri")
        self.assertEqual(docker.images.build.call_args_list[0][1]['tag'], "repouri")

    @patch('boto3.Session')
    def test_delete_function(self, boto_session):
        session, lam, _ = self._init_mocks(['delete_function', 'get_function'])
        boto_session.return_value = session

        lam.client.client.get_function.return_value = {'Configuration': {'Environment': {'Variables': {'FDL': 'e30='}}}}
        lam.client.client.delete_function.return_value = {}

        lam.delete_function()
        self.assertEqual(lam.client.client.delete_function.call_args_list[0][1], {'FunctionName': 'fname'})

    @patch('boto3.Session')
    @patch('scar.providers.aws.containerimage.ECR')
    def test_delete_function_image(self, ecr_client, boto_session):
        session, lam, _ = self._init_mocks(['delete_function', 'get_function'])
        boto_session.return_value = session

        ecr = MagicMock(['get_repository_uri', 'delete_repository'])
        ecr.get_repository_uri.return_value = "repouri"
        ecr_client.return_value = ecr

        lam.client.client.get_function.return_value = {'Configuration': {'Environment': {'Variables': {'FDL': 'cnVudGltZTogaW1hZ2U='}}}}
        lam.client.client.delete_function.return_value = {}
        lam.resources_info['lambda']['runtime'] = 'image'

        lam.delete_function()
        self.assertEqual(lam.client.client.delete_function.call_args_list[0][1], {'FunctionName': 'fname'})
        self.assertEqual(ecr.delete_repository.call_args_list[0][0][0], 'fname')

    @patch('boto3.Session')
    def test_preheat_function(self, boto_session):
        session, lam, _ = self._init_mocks(['invoke'])
        boto_session.return_value = session

        lam.preheat_function()
        res = {'FunctionName': 'fname', 'InvocationType': 'Event', 'LogType': 'None', 'Payload': '{}'}
        self.assertEqual(lam.client.client.invoke.call_args_list[0][1], res)

    @patch('boto3.Session')
    def test_find_function(self, boto_session):
        session, lam, _ = self._init_mocks(['get_function_configuration'])
        boto_session.return_value = session

        lam.client.client.get_function_configuration.return_value = {}

        self.assertEqual(lam.find_function('fname'), True)
        res = {'FunctionName': 'fname'}
        self.assertEqual(lam.client.client.get_function_configuration.call_args_list[0][1], res)

    @patch('boto3.Session')
    def test_process_asynchronous_lambda_invocations(self, boto_session):
        session, lam, _ = self._init_mocks(['invoke', 'get_function_configuration'])
        boto_session.return_value = session

        lam.client.client.get_function_configuration.return_value = {}

        event = {'Records': [{'s3': {'object': {'key': 'okey'}}}]}
        lam.process_asynchronous_lambda_invocations([event])

        res = {'FunctionName': 'fname',
               'InvocationType': 'Event',
               'LogType': 'None',
               'Payload': '{"Records": [{"s3": {"object": {"key": "okey"}}}]}'}
        self.assertEqual(lam.client.client.invoke.call_args_list[0][1], res)

    @patch('boto3.Session')
    @patch('requests.get')
    @patch('requests.post')
    @patch('scar.providers.aws.validators.FileUtils.get_file_size')
    def test_call_http_endpoint(self, get_file_size, post, get, boto_session):
        session, lam, _ = self._init_mocks(['get_function_configuration'])
        boto_session.return_value = session

        lam.client.client.get_function_configuration.return_value = {'Environment': {'Variables': {'API_GATEWAY_ID': 'apiid'}}}
        lam.call_http_endpoint()
        self.assertEqual(get.call_args_list[0][0][0], 'https://apiid.us-east-1/scar/l')

        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
        tmpfile.write(b"somedata\n")
        tmpfile.close()

        lam.resources_info['api_gateway']['data_binary'] = tmpfile.name
        lam.resources_info['api_gateway']['parameters'] = {'key': 'value'}

        get_file_size.return_value = 1024

        lam.call_http_endpoint()

        os.unlink(tmpfile.name)
        self.assertEqual(post.call_args_list[0][0][0], 'https://apiid.us-east-1/scar/l')
        self.assertEqual(post.call_args_list[0][1]['data'], b'c29tZWRhdGEK')
        self.assertEqual(post.call_args_list[0][1]['params'], {'key': 'value'})

    @patch('boto3.Session')
    @patch('requests.get')
    @patch('scar.providers.aws.lambdafunction.ZipFile')
    def test_get_fdl_config(self, zipfile, get, boto_session):
        session, lam, _ = self._init_mocks(['get_function'])
        boto_session.return_value = session

        response = MagicMock(['content'])
        response.content = b"aa"
        get.return_value = response
        lam.client.client.get_function.return_value = {'SupervisorVersion': '1.4.2',
                                                       'Code': {'Location': 'http://loc.es'}}

        zfile = MagicMock(['__enter__', '__exit__'])
        zipfile.return_value = zfile

        filedata = MagicMock(['read'])
        filedata.read.side_effect = ["- item\n- item2\n", ""]
        filecont = MagicMock(['__enter__', '__exit__'])
        filecont.__enter__.return_value = filedata

        thezip = MagicMock(['open'])
        thezip.open.return_value = filecont
        zfile.__enter__.return_value = thezip

        self.assertEqual(lam.get_fdl_config('arn'), ['item', 'item2'])
        self.assertEqual(get.call_args_list[0][0][0], "http://loc.es")

    @patch('boto3.Session')
    def test_get_all_functions(self, boto_session):
        session, lam, _ = self._init_mocks(['get_function_configuration'])
        boto_session.return_value = session

        lam.client.client.get_function_configuration.return_value = {'FunctionName': 'fname',
                                                                     'FunctionArn': 'arn1',
                                                                     'Timeout': 600,
                                                                     'MemorySize': 1024}

        res = lam.get_all_functions(['arn1'])
        self.assertEqual(res[0]['lambda']['memory'], 1024)
        self.assertEqual(res[0]['lambda']['supervisor']['version'], '-')

    @patch('boto3.Session')
    @patch('time.sleep')
    def test_wait_function_active(self, sleep, boto_session):
        session, lam, _ = self._init_mocks(['get_function_configuration'])
        boto_session.return_value = session

        lam.client.client.get_function_configuration.return_value = {'State': 'Active'}

        self.assertEqual(lam.wait_function_active('farn'), True)
        self.assertEqual(sleep.call_count, 1)
