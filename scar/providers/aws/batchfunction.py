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

import random
from typing import Dict, List
from scar.providers.aws import GenericClient
import scar.logger as logger
from scar.providers.aws.launchtemplates import LaunchTemplates
from scar.utils import lazy_property, FileUtils, StrUtils

_LAUNCH_TEMPLATE_NAME = 'faas-supervisor'


def _get_job_definitions(jobs_info: Dict) -> List:
    return [f"{job_def.get('jobDefinitionName', '')}:{job_def.get('revision', '')}"
            for job_def in jobs_info.get('jobDefinitions', {})]


class Batch(GenericClient):

    @lazy_property
    def launch_templates(self):
        launch_templates = LaunchTemplates(self.aws, self.supervisor_version)
        return launch_templates

    def __init__(self, aws_properties, supervisor_version):
        super().__init__(aws_properties)
        self.supervisor_version = supervisor_version
        self.aws.batch.instance_role = (f"arn:aws:iam::{self.aws.account_id}:"
                                        "instance-profile/ecsInstanceRole")
        self.aws.batch.service_role = (f"arn:aws:iam::{self.aws.account_id}:"
                                       "role/service-role/AWSBatchServiceRole")
        self.aws.batch.env_vars = []
        self._set_required_environment_variables()

    def _set_required_environment_variables(self):
        self._set_batch_environment_variable('AWS_LAMBDA_FUNCTION_NAME', self.aws.lambdaf.name)
        self._set_batch_environment_variable('SCRIPT', self._get_user_script())
        if (hasattr(self.aws.lambdaf, 'environment_variables') and
                self.aws.lambdaf.environment_variables):
            self._add_custom_environment_variables(self.aws.lambdaf.environment_variables)
        if (hasattr(self.aws.lambdaf, 'lambda_environment') and
                self.aws.lambdaf.lambda_environment):
            self._add_custom_environment_variables(self.aws.lambdaf.lambda_environment)
        if hasattr(self.aws, "s3"):
            self._add_s3_environment_vars()

    def _add_custom_environment_variables(self, env_vars):
        if isinstance(env_vars, dict):
            for key, val in env_vars.items():
                self._set_batch_environment_variable(key, val)
        else:
            for env_var in env_vars:
                self._set_batch_environment_variable(*env_var.split("="))

    def _set_batch_environment_variable(self, key, value):
        if key and value is not None:
            self.aws.batch.env_vars.append({'name': key, 'value': value})

    def _add_s3_environment_vars(self):
        provider_id = random.randint(1, 1000001)
        if hasattr(self.aws.s3, "input_bucket"):
            self._set_batch_environment_variable(f'STORAGE_PATH_INPUT_{provider_id}',
                                                 self.aws.s3.storage_path_input)
        if hasattr(self.aws.s3, "output_bucket"):
            self._set_batch_environment_variable(f'STORAGE_PATH_OUTPUT_{provider_id}',
                                                 self.aws.s3.storage_path_output)
        else:
            self._set_batch_environment_variable(f'STORAGE_PATH_OUTPUT_{provider_id}',
                                                 self.aws.s3.storage_path_input)
        self._set_batch_environment_variable(f'STORAGE_AUTH_S3_USER_{provider_id}', 'scar')

    def _get_user_script(self):
        script = ''
        if hasattr(self.aws.lambdaf, "init_script"):
            file_content = FileUtils.read_file(self.aws.lambdaf.init_script)
            script = StrUtils.utf8_to_base64_string(file_content)
        return script

    def _delete_job_definitions(self, name):
        job_definitions = []
        # Get IO definitions (if any)
        kwargs = {"jobDefinitionName": '{0}-io'.format(name)}
        io_job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(_get_job_definitions(io_job_info))
        # Get main job definition
        kwargs = {"jobDefinitionName": name}
        job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(_get_job_definitions(job_info))
        for job_def in job_definitions:
            kwars = {"jobDefinition": job_def}
            self.client.deregister_job_definition(**kwars)
        logger.info("Job definitions deleted")

    def _get_job_queue_info(self, name):
        job_queue_info_args = {'jobQueues': [self._get_resource_name(name)]}
        return self.client.describe_job_queues(**job_queue_info_args)

    def _delete_job_queue(self, name):
        response = self._get_job_queue_info(name)
        while response["jobQueues"]:
            state = response["jobQueues"][0]["state"]
            status = response["jobQueues"][0]["status"]
            if status == "VALID":
                self._delete_valid_job_queue(state, name)
            response = self._get_job_queue_info(name)

    def _delete_valid_job_queue(self, state, name):
        if state == "ENABLED":
            updating_args = {'jobQueue': self._get_resource_name(name),
                             'state': 'DISABLED'}
            self.client.update_job_queue(**updating_args)
        elif state == "DISABLED":
            deleting_args = {'jobQueue': self._get_resource_name(name)}
            logger.info("Job queue deleted")
            self.client.delete_job_queue(**deleting_args)

    def _get_compute_env_info(self, name):
        creation_args = self._get_describe_compute_env_args(name_c=name)
        return self.client.describe_compute_environments(**creation_args)

    def _delete_compute_env(self, name):
        response = self._get_compute_env_info(name)
        while response["computeEnvironments"]:
            state = response["computeEnvironments"][0]["state"]
            status = response["computeEnvironments"][0]["status"]
            if status == "VALID":
                self._delete_valid_compute_environment(state, name)
            response = self._get_compute_env_info(name)

    def _delete_valid_compute_environment(self, state, name):
        if state == "ENABLED":
            update_args = {'computeEnvironment': self._get_resource_name(name),
                           'state': 'DISABLED'}
            self.client.update_compute_environment(**update_args)
        elif state == "DISABLED":
            delete_args = {'computeEnvironment': self._get_resource_name(name)}
            logger.info("Compute environment deleted")
            self.client.delete_compute_environment(**delete_args)

    def _get_compute_env_args(self):
        return {
            'computeEnvironmentName': self.aws.lambdaf.name,
            'serviceRole': self.aws.batch.service_role,
            'type': self.aws.batch.compute_resources['type'],
            'state':  self.aws.batch.compute_resources['state'],
            'computeResources': {
                'type': self.aws.batch.compute_resources['comp_type'],
                'minvCpus': self.aws.batch.compute_resources['min_v_cpus'],
                'maxvCpus': self.aws.batch.compute_resources['max_v_cpus'],
                'desiredvCpus': self.aws.batch.compute_resources['desired_v_cpus'],
                'instanceTypes': self.aws.batch.compute_resources['instance_types'],
                'subnets': self.aws.batch.compute_resources['subnets'],
                'securityGroupIds': self.aws.batch.compute_resources['security_group_ids'],
                'instanceRole': self.aws.batch.instance_role,
                'launchTemplate': {
                    'launchTemplateName': _LAUNCH_TEMPLATE_NAME,
                    'version': str(self.launch_templates.get_launch_template_version())
                }
            }
        }

    def _get_creations_job_queue_args(self):
        return {
            'computeEnvironmentOrder': [{'computeEnvironment': self.aws.lambdaf.name,
                                         'order': 1}, ],
            'jobQueueName':  self.aws.lambdaf.name,
            'priority': 1,
            'state': self.aws.batch.compute_resources['state'],
        }

    def _get_resource_name(self, name=None):
        return name if name else self.aws.lambdaf.name

    def _get_describe_compute_env_args(self, name_c=None):
        return {'computeEnvironments': [self._get_resource_name(name_c)]}

    def _get_job_definition_args(self):
        job_def_args = {
            'jobDefinitionName': self.aws.lambdaf.name,
            'type': 'container',
            'containerProperties': {
                'image': self.aws.lambdaf.image,
                'memory': int(self.aws.batch.memory),
                'vcpus': int(self.aws.batch.vcpus),
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
                'environment': self.aws.batch.env_vars,
                'mountPoints': [
                    {
                        'containerPath': '/opt/faas-supervisor/bin',
                        'sourceVolume': 'supervisor-bin'
                    }
                ]
            }
        }
        if self.aws.batch.enable_gpu:
            job_def_args['containerProperties']['resourceRequirements'] = [
                {
                    'value': '1',
                    'type': 'GPU'
                }
            ]
        return job_def_args

    def _get_state_and_status_of_compute_env(self, name=None):
        creation_args = self._get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return (response["computeEnvironments"][0]["state"],
                response["computeEnvironments"][0]["status"])

    def create_batch_environment(self):
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
                logger.info(f"Registering '{self.aws.lambdaf.name}' job definition.")
                return self.client.register_job_definition(**creation_args)

    def delete_compute_environment(self, name):
        self._delete_job_definitions(name)
        self._delete_job_queue(name)
        self._delete_compute_env(name)

    def exist_compute_environments(self, name):
        creation_args = self._get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return len(response["computeEnvironments"]) > 0

    def describe_jobs(self, job_id):
        describe_args = {'jobs': [job_id]}
        return self.client.describe_jobs(**describe_args)

    def exist_job(self, job_id):
        response = self.describe_jobs(job_id)
        return len(response["jobs"]) != 0
