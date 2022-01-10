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
import base64
from mock import MagicMock
from mock import patch

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.batchfunction import Batch


class TestBatch(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        batch = Batch({'lambda': {'name': 'fname'}})
        self.assertEqual(type(batch.client.client).__name__, "Batch")

    @patch('boto3.Session')
    @patch('scar.providers.aws.launchtemplates.SupervisorUtils.get_supervisor_binary_url')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_create_batch_environment(self, load_tmp_config_file, get_supervisor_binary_url,
                                      boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['register_job_definition', 'describe_launch_templates',
                            'create_launch_template', 'create_compute_environment',
                            'describe_compute_environments', 'create_job_queue'])
        session.client.return_value = client
        boto_session.return_value = session
        load_tmp_config_file.return_value = {}
        get_supervisor_binary_url.return_value = "https://some.es"

        batch = Batch({'lambda': {'name': 'fname',
                                  'supervisor': {'version': '1.4.2'},
                                  'container': {'image': 'some/image:tag',
                                                'environment': {'Variables': {}}}},
                       'batch': {'service_role': 'srole',
                                 'memory': 1024,
                                 'vcpus': 1,
                                 'type': 'MANAGED',
                                 'state': 'ENABLED',
                                 'enable_gpu': True,
                                 'compute_resources': {'instance_role': 'irole',
                                                       'type': 'EC2',
                                                       'min_v_cpus': 0,
                                                       'max_v_cpus': 2,
                                                       'desired_v_cpus': 1,
                                                       'instance_types': ['m1.small'],
                                                       'subnets': [],
                                                       'security_group_ids': [],
                                                       'launch_template_name': 'temp_name'},
                                 'environment': {'Variables': {}},
                                 'multi_node_parallel': {'enabled': False}},
                       'iam': {'account_id': 'id', 'role': 'role'}})

        batch.client.client.register_job_definition.return_value = {}
        batch.client.client.describe_launch_templates.return_value = {}
        batch.client.client.create_launch_template.return_value = {
            'LaunchTemplate': {'LatestVersionNumber': '1'}
        }
        batch.client.client.create_compute_environment.return_value = {}
        batch.client.client.describe_compute_environments.return_value = {
            'computeEnvironments': [{'state': 'ENABLED', 'status': 'VALID'}]
        }
        batch.client.client.create_job_queue.return_value = {}
        batch.create_batch_environment()

        func_config = b"container:\n"
        func_config += b"  environment:\n"
        func_config += b"    Variables: {}\n"
        func_config += b"  image: some/image:tag\n"
        func_config += b"name: fname\n"
        func_config += b"storage_providers: {}\n"
        func_config += b"supervisor:\n"
        func_config += b"  version: 1.4.2\n"
        func_config_64 = base64.b64encode(func_config).decode()
        res = {'jobDefinitionName': 'fname',
               'containerProperties': {
                   'image': 'some/image:tag',
                   'memory': 1024,
                   'vcpus': 1,
                   'command': ['/bin/sh', '-c',
                               'echo $EVENT | /opt/faas-supervisor/bin/supervisor'],
                   'volumes': [{'host': {'sourcePath': '/opt/faas-supervisor/bin'},
                               'name': 'supervisor-bin'}],
                   'environment': [{'name': 'AWS_LAMBDA_FUNCTION_NAME', 'value': 'fname'},
                                   {'name': 'SCRIPT', 'value': ''},
                                   {'name': 'FUNCTION_CONFIG', 'value': func_config_64}],
                   'mountPoints': [{'containerPath': '/opt/faas-supervisor/bin',
                                   'sourceVolume': 'supervisor-bin'}],
                   'resourceRequirements': [{'value': '1',
                                             'type': 'GPU'}]},
               'type': 'container'}
        self.assertEqual(batch.client.client.register_job_definition.call_args_list[0][1], res)
        self.assertEqual(batch.client.client.create_launch_template.call_args_list[0][1]['LaunchTemplateName'], 'temp_name')
        self.assertEqual(batch.client.client.create_launch_template.call_args_list[0][1]['VersionDescription'], '1.4.2')
        res = {'computeEnvironmentName': 'fname',
               'serviceRole': 'srole',
               'type': 'MANAGED',
               'state': 'ENABLED',
               'computeResources': {'type': 'EC2',
                                    'minvCpus': 0,
                                    'maxvCpus': 2,
                                    'desiredvCpus': 1,
                                    'instanceTypes': ['m1.small'],
                                    'subnets': [],
                                    'securityGroupIds': [],
                                    'instanceRole': 'irole',
                                    'launchTemplate': {'launchTemplateName': 'temp_name',
                                                       'version': '1'}}}
        self.assertEqual(batch.client.client.create_compute_environment.call_args_list[0][1], res)

    @patch('boto3.Session')
    def test_delete_compute_environment(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['describe_job_definitions', 'deregister_job_definition',
                            'describe_job_queues', 'update_job_queue', 'delete_job_queue',
                            'describe_compute_environments', 'update_compute_environment',
                            'delete_compute_environment'])
        session.client.return_value = client
        boto_session.return_value = session

        batch = Batch({'lambda': {'name': 'fname'}})

        batch.client.client.describe_job_definitions.return_value = {}
        batch.client.client.describe_job_queues.side_effect = [{'jobQueues': [{'state': 'ENABLED',
                                                                               'status': 'VALID'}]},
                                                               {'jobQueues': [{'state': 'DISABLED',
                                                                               'status': 'VALID'}]},
                                                               {'jobQueues': []}]
        batch.client.client.describe_compute_environments.side_effect = [
            {'computeEnvironments': [{'state': 'ENABLED', 'status': 'VALID'}]},
            {'computeEnvironments': [{'state': 'DISABLED', 'status': 'VALID'}]},
            {'computeEnvironments': []}
        ]

        batch.delete_compute_environment()

        res = {'jobQueue': 'fname', 'state': 'DISABLED'}
        self.assertEqual(batch.client.client.update_job_queue.call_args_list[0][1], res)
        res = {'jobQueue': 'fname'}
        self.assertEqual(batch.client.client.delete_job_queue.call_args_list[0][1], res)

        res = {'computeEnvironment': 'fname', 'state': 'DISABLED'}
        self.assertEqual(batch.client.client.update_compute_environment.call_args_list[0][1], res)
        res = {'computeEnvironment': 'fname'}
        self.assertEqual(batch.client.client.delete_compute_environment.call_args_list[0][1], res)
