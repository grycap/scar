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

from typing import Dict, List
import yaml
from scar.providers.aws import GenericClient
import scar.logger as logger
from scar.providers.aws.launchtemplates import LaunchTemplates
from scar.providers.aws.functioncode import create_function_config
from scar.utils import FileUtils, StrUtils


def _get_job_definitions(jobs_info: Dict) -> List:
    return [f"{job_def.get('jobDefinitionName', '')}:{job_def.get('revision', '')}"
            for job_def in jobs_info.get('jobDefinitions', {})]


class Batch(GenericClient):

    def __init__(self, resources_info):
        super().__init__(resources_info.get('batch'))
        self.resources_info = resources_info
        self.batch = resources_info.get('batch')
        self.function_name = self.resources_info.get('lambda').get('name')

    def _set_required_environment_variables(self) -> None:
        self._set_batch_environment_variable('AWS_LAMBDA_FUNCTION_NAME', self.function_name)
        self._set_batch_environment_variable('SCRIPT', self._get_user_script())
        self._set_batch_environment_variable('FUNCTION_CONFIG', self._get_config_file())
        if self.resources_info.get('lambda').get('container').get('environment').get('Variables', False):
            for key, value in self.resources_info.get('lambda').get('container').get('environment').get('Variables').items():
                self._set_batch_environment_variable(key, value)

    def _set_batch_environment_variable(self, key: str, value: str) -> None:
        self.resources_info['batch']['environment']['Variables'].update({key: value})

    def _get_user_script(self) -> str:
        script = ''
        if self.resources_info.get('lambda').get('init_script', False):
            file_content = FileUtils.read_file(self.resources_info.get('lambda').get('init_script'))
            script = StrUtils.utf8_to_base64_string(file_content)
        return script

    def _get_config_file(self) -> str:
        cfg_file = ''
        config = create_function_config(self.resources_info)
        yaml_str = yaml.safe_dump(config)
        cfg_file = StrUtils.utf8_to_base64_string(yaml_str)
        return cfg_file

    def _delete_job_definitions(self) -> None:
        # Get main job definition
        kwargs = {"jobDefinitionName": self.function_name}
        job_info = self.client.describe_job_definitions(**kwargs)
        for job_def in _get_job_definitions(job_info):
            kwars = {"jobDefinition": job_def}
            self.client.deregister_job_definition(**kwars)
        logger.info("Job definitions successfully deleted.")

    def _get_job_queue_info(self):
        job_queue_info_args = {'jobQueues': [self.function_name]}
        return self.client.describe_job_queues(**job_queue_info_args)

    def _delete_job_queue(self):
        response = self._get_job_queue_info()
        while response["jobQueues"]:
            state = response["jobQueues"][0]["state"]
            status = response["jobQueues"][0]["status"]
            if status == "VALID":
                self._delete_valid_job_queue(state)
            response = self._get_job_queue_info()

    def _delete_valid_job_queue(self, state):
        if state == "ENABLED":
            updating_args = {'jobQueue': self.function_name,
                             'state': 'DISABLED'}
            self.client.update_job_queue(**updating_args)
        elif state == "DISABLED":
            deleting_args = {'jobQueue': self.function_name}
            self.client.delete_job_queue(**deleting_args)
            logger.info("Job queue successfully deleted.")

    def _get_describe_compute_env_args(self):
        return {'computeEnvironments': [self.function_name]}

    def _get_compute_env_info(self):
        creation_args = self._get_describe_compute_env_args()
        return self.client.describe_compute_environments(**creation_args)

    def _delete_compute_env(self):
        response = self._get_compute_env_info()
        while response["computeEnvironments"]:
            state = response["computeEnvironments"][0]["state"]
            status = response["computeEnvironments"][0]["status"]
            if status == "VALID":
                self._delete_valid_compute_environment(state)
            response = self._get_compute_env_info()

    def _delete_valid_compute_environment(self, state):
        if state == "ENABLED":
            update_args = {'computeEnvironment': self.function_name,
                           'state': 'DISABLED'}
            self.client.update_compute_environment(**update_args)
        elif state == "DISABLED":
            delete_args = {'computeEnvironment': self.function_name}
            self.client.delete_compute_environment(**delete_args)
            logger.info("Compute environment successfully deleted.")

    def _get_compute_env_args(self):
        account_id = self.resources_info.get('iam').get('account_id')
        return {
            'computeEnvironmentName': self.function_name,
            'serviceRole': self.batch.get('service_role').format(account_id=account_id),
            'type': self.batch.get('type'),
            'state':  self.batch.get('state'),
            'computeResources': {
                'type': self.batch.get('compute_resources').get('type'),
                'minvCpus': self.batch.get('compute_resources').get('min_v_cpus'),
                'maxvCpus': self.batch.get('compute_resources').get('max_v_cpus'),
                'desiredvCpus': self.batch.get('compute_resources').get('desired_v_cpus'),
                'instanceTypes': self.batch.get('compute_resources').get('instance_types'),
                'subnets': self.batch.get('compute_resources').get('subnets'),
                'securityGroupIds': self.batch.get('compute_resources').get('security_group_ids'),
                'instanceRole': self.batch.get('compute_resources').get('instance_role').format(account_id=account_id),
                'launchTemplate': {
                    'launchTemplateName': self.batch.get('compute_resources').get('launch_template_name'),
                    'version': str(LaunchTemplates(self.resources_info).get_launch_template_version())
                }
            }
        }

    def _get_creations_job_queue_args(self):
        return {
            'computeEnvironmentOrder': [{'computeEnvironment': self.function_name,
                                         'order': 1}, ],
            'jobQueueName':  self.function_name,
            'priority': 1,
            'state': self.batch.get('state'),
        }

    def _get_job_definition_args(self):
        job_def_args = {
            'jobDefinitionName': self.function_name
        }
        if self.batch.get('multi_node_parallel').get('enabled'):
            job_def_args['nodeProperties'] = self._get_node_properties_multi_node_args()
            job_def_args['type'] = 'multinode'
        else:
            job_def_args['containerProperties'] = self._get_container_properties_single_node_args()
            job_def_args['type'] = 'container'
        return job_def_args

    def _get_container_properties_single_node_args(self):
        job_def_args = {
            'image': self.resources_info.get('lambda').get('container').get('image'),
            'memory': int(self.batch.get('memory')),
            'vcpus': int(self.batch.get('vcpus')),
            'command': [
                '/bin/sh',
                '-c',
                'echo $EVENT | /opt/faas-supervisor/bin/supervisor'
            ],
            'volumes': [
                {
                    'host': {
                        'sourcePath': '/opt/faas-supervisor/bin'
                    },
                    'name': 'supervisor-bin'
                }
            ],
            'environment': [{'name': key, 'value': value} for key, value in self.resources_info['batch']['environment']['Variables'].items()],
            'mountPoints': [
                {
                    'containerPath': '/opt/faas-supervisor/bin',
                    'sourceVolume': 'supervisor-bin'
                }
            ]
        }
        if self.batch.get('enable_gpu'):
            job_def_args['resourceRequirements'] = [
                {
                    'value': '1',
                    'type': 'GPU'
                }
            ]
        return job_def_args

    def _get_node_properties_multi_node_args(self):
        targetNodes = self.batch.get('multi_node_parallel').get('number_nodes') - 1
        job_def_args = {
            "numNodes": int(self.batch.get('multi_node_parallel').get('number_nodes')),
            "mainNode": int(self.batch.get('multi_node_parallel').get('main_node_index')),
            "nodeRangeProperties": [
                {
                "targetNodes": "0:", #+ str(targetNodes),
                "container": self._get_container_properties_single_node_args()
                }
            ]#[self._get_node_node_range_property_multi_node_args(target_nodes) for target_nodes in self.batch.get('multi_node_parallel').get('target_nodes')]
        }
        return job_def_args

    def _get_state_and_status_of_compute_env(self):
        creation_args = self._get_describe_compute_env_args()
        response = self.client.describe_compute_environments(**creation_args)
        return (response["computeEnvironments"][0]["state"],
                response["computeEnvironments"][0]["status"])

    def create_batch_environment(self):
        self._set_required_environment_variables()
        creation_args = self._get_compute_env_args()
        self.client.create_compute_environment(**creation_args)
        while True:
            state, status = self._get_state_and_status_of_compute_env()
            if state == "ENABLED" and status == "VALID":
                creation_args = self._get_creations_job_queue_args()
                logger.info("Compute environment successfully created.")
                self.client.create_job_queue(**creation_args)
                logger.info('Job queue successfully created.')
                creation_args = self._get_job_definition_args()
                logger.info(f"Registering '{self.function_name}' job definition.")
                return self.client.register_job_definition(**creation_args)

    def delete_compute_environment(self):
        self._delete_job_definitions()
        self._delete_job_queue()
        self._delete_compute_env()

    def exist_compute_environments(self):
        creation_args = self._get_describe_compute_env_args()
        response = self.client.describe_compute_environments(**creation_args)
        return len(response["computeEnvironments"]) > 0

    def get_jobs_with_request_id(self) -> Dict:
        describe_args = {'jobs': [self.resources_info.get('cloudwatch').get('request_id')]}
        return self.client.describe_jobs(**describe_args)

#     def exist_job(self, job_id: str) -> bool:
#         response = self.describe_jobs(job_id)
#         return len(response["jobs"]) != 0
