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
from scar.providers.aws import GenericClient
import scar.logger as logger
from scar.providers.aws.launchtemplates import LaunchTemplates
from scar.utils import DataTypesUtils, FileUtils, StrUtils


class Batch(GenericClient):

    @DataTypesUtils.lazy_property
    def launch_templates(self):
        launch_templates = LaunchTemplates(self.aws, self.supervisor_version)
        return launch_templates

    def __init__(self, aws_properties, supervisor_version):
        super().__init__(aws_properties)
        self.supervisor_version = supervisor_version
        self.script = self._get_user_script()
        self._initialize_properties()

    def _initialize_properties(self):
        self.aws.batch.instance_role = "arn:aws:iam::{0}:instance-profile/ecsInstanceRole".format(
            self.aws.account_id)
        self.aws.batch.service_role = "arn:aws:iam::{0}:role/service-role/AWSBatchServiceRole".format(
            self.aws.account_id)
        self.aws.batch.env_vars = []
        self._set_required_environment_variables()

    def exist_compute_environments(self, name):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return len(response["computeEnvironments"]) > 0

    def delete_compute_environment(self, name):
        self._delete_job_definitions(name)
        self._delete_job_queue(name)
        self._delete_compute_env(name)

    def _get_user_script(self):
        script = ''
        if ('init_script' in self.aws._lambda and 
            self.aws._lambda.init_script):
            file_content = FileUtils.read_file(self.aws._lambda.init_script)
            script = StrUtils.utf8_to_base64_string(file_content)
        return script

    def _get_job_definitions(self, jobs_info):
        return ["{0}:{1}".format(definition['jobDefinitionName'], definition['revision']) for definition in jobs_info['jobDefinitions']]

    def _delete_job_definitions(self, name):
        job_definitions = []
        # Get IO definitions (if any)
        kwargs = {"jobDefinitionName": '{0}-io'.format(name)}
        io_job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(self._get_job_definitions(io_job_info))
        # Get main job definition
        kwargs = {"jobDefinitionName": name}
        job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(self._get_job_definitions(job_info))
        for job_def in job_definitions:
            kwars = {"jobDefinition": job_def}
            self.client.deregister_job_definition(**kwars)
        logger.info("Job definitions deleted")

    def describe_jobs(self, job_id):
        describe_args = {'jobs': [job_id]}
        return self.client.describe_jobs(**describe_args)

    def exist_job(self, job_id):
        response = self.describe_jobs(job_id)
        return len(response["jobs"]) != 0

    def exist_jobs_queue(self, name):
        response = self.get_job_queue_info(name)
        return len(response["jobQueues"]) != 0

    def get_job_queue_info(self, name):
        job_queue_info_args = {'jobQueues': [self.get_resource_name(name)]}
        return self.client.describe_job_queues(**job_queue_info_args)

    def _delete_job_queue(self, name):
        response = self.get_job_queue_info(name)
        while response["jobQueues"]:
            state = response["jobQueues"][0]["state"]
            status = response["jobQueues"][0]["status"]
            if status == "VALID":
                self.delete_valid_job_queue(state, name)
            response = self.get_job_queue_info(name)

    def delete_valid_job_queue(self, state, name):
        if state == "ENABLED":
            updating_args = {'jobQueue': self.get_resource_name(name),
                             'state': 'DISABLED'}
            self.client.update_job_queue(**updating_args)
        elif state == "DISABLED":
            deleting_args = {'jobQueue': self.get_resource_name(name)}
            logger.info("Job queue deleted")
            return self.client.delete_job_queue(**deleting_args)

    def get_compute_env_info(self, name):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        return self.client.describe_compute_environments(**creation_args)

    def _delete_compute_env(self, name):
        response = self.get_compute_env_info(name)
        while response["computeEnvironments"]:
            state = response["computeEnvironments"][0]["state"]
            status = response["computeEnvironments"][0]["status"]
            if status == "VALID":
                self.delete_valid_compute_environment(state, name)
            response = self.get_compute_env_info(name)

    def delete_valid_compute_environment(self, state, name):
        if state == "ENABLED":
            update_args = {'computeEnvironment': self.get_resource_name(name),
                           'state': 'DISABLED'}
            self.client.update_compute_environment(**update_args)
        elif state == "DISABLED":
            delete_args = {'computeEnvironment': self.get_resource_name(name)}
            logger.info("Compute environment deleted")
            return self.client.delete_compute_environment(**delete_args)

    def get_compute_env_args(self):
        return {
            'computeEnvironmentName': self.aws._lambda.name,
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
                    'launchTemplateName': 'faas-supervisor',
                    'version': str(self.launch_templates.get_launch_template_version())
                }
            }
        }

    def get_creations_job_queue_args(self):
        return {
            'computeEnvironmentOrder': [{'computeEnvironment': self.aws._lambda.name, 'order': 1}, ],
            'jobQueueName':  self.aws._lambda.name,
            'priority': 1,
            'state': self.aws.batch.compute_resources['state'],
        }

    def get_resource_name(self, name=None):
        return name if name else self.aws._lambda.name

    def get_describe_compute_env_args(self, name_c=None):
        return {'computeEnvironments': [self.get_resource_name(name_c)]}

    def _get_job_definition_args(self):
        job_def_args = {
            'jobDefinitionName': self.aws._lambda.name,
            'type': 'container',
            'containerProperties': {
                'image': self.aws._lambda.image,
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

    def _add_custom_environment_variables(self, env_vars):
        if isinstance(env_vars, dict):
            for key, val in env_vars.items():
                self._set_batch_environment_variable(key, val)
        else:
            for env_var in env_vars:
                key_val = env_var.split("=")
                self._set_batch_environment_variable(key_val[0], key_val[1])

    def _set_batch_environment_variable(self, key, value):
        self.aws.batch.env_vars.append({
            'name': key,
            'value': value
        })

    def _add_s3_environment_vars(self):
        if hasattr(self.aws, "s3"):
            provider_id = random.randint(1, 1000001)

            if hasattr(self.aws.s3, "input_bucket"):
                self._set_batch_environment_variable(
                    f'STORAGE_PATH_INPUT_{provider_id}',
                    self.aws.s3.storage_path_input
                )
            if hasattr(self.aws.s3, "output_bucket"):
                self._set_batch_environment_variable(
                    f'STORAGE_PATH_OUTPUT_{provider_id}',
                    self.aws.s3.storage_path_output
                )
            else:
                self._set_batch_environment_variable(
                    f'STORAGE_PATH_OUTPUT_{provider_id}',
                    self.aws.s3.storage_path_input
                )
            self._set_batch_environment_variable(
                f'STORAGE_AUTH_S3_USER_{provider_id}',
                'scar'
            )

    def _set_required_environment_variables(self):
        self._set_batch_environment_variable('AWS_LAMBDA_FUNCTION_NAME', self.aws._lambda.name)
        if self.script:
            self._set_batch_environment_variable('SCRIPT', self.script)
        if (hasattr(self.aws._lambda, 'environment_variables') and
                self.aws._lambda.environment_variables):
            self._add_custom_environment_variables(self.aws._lambda.environment_variables)
        if (hasattr(self.aws._lambda, 'lambda_environment') and
                self.aws._lambda.lambda_environment):
            self._add_custom_environment_variables(self.aws._lambda.lambda_environment)
        self._add_s3_environment_vars()

    def get_state_and_status_of_compute_env(self, name=None):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return response["computeEnvironments"][0]["state"], response["computeEnvironments"][0]["status"]

    def create_batch_environment(self):
        creation_args = self.get_compute_env_args()
        self.client.create_compute_environment(**creation_args)
        while True:
            state, status = self.get_state_and_status_of_compute_env()
            if state == "ENABLED" and status == "VALID":
                creation_args = self.get_creations_job_queue_args()
                logger.info("Compute environment successfully created.")
                self.client.create_job_queue(**creation_args)
                logger.info('Job queue successfully created.')
                creation_args = self._get_job_definition_args()
                logger.info(f'Registering \'{self.aws._lambda.name}\' job definition.')
                return self.client.register_job_definition(**creation_args)
