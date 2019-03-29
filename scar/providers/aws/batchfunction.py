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

from scar.providers.aws.botoclientfactory import GenericClient
import scar.logger as logger

class Batch(GenericClient):

    def __init__(self, aws_properties):
        super().__init__(aws_properties)
        self._initialize_properties()

    def _initialize_properties(self):
        self.aws.batch.instance_role = "arn:aws:iam::{0}:instance-profile/ecsInstanceRole".format(self.aws.account_id)
        self.aws.batch.service_role = "arn:aws:iam::{0}:role/service-role/AWSBatchServiceRole".format(self.aws.account_id)
    
    def exist_compute_environments(self, name):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return len(response["computeEnvironments"]) > 0

    def delete_compute_environment(self,name):
        self._delete_job_definitions(name)
        self._delete_job_queue(name)
        self._delete_compute_env(name)
            
    def _get_job_definitions(self, jobs_info):
        return ["{0}:{1}".format(definition['jobDefinitionName'], definition['revision']) for definition in jobs_info['jobDefinitions']]
            
    def _delete_job_definitions(self, name):
        job_definitions = []
        # Get IO definitions (if any)
        kwargs = {"jobDefinitionName" : '{0}-io'.format(name)}
        io_job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(self._get_job_definitions(io_job_info))
        # Get main job definition
        kwargs = {"jobDefinitionName" : name}
        job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(self._get_job_definitions(job_info))
        for job_def in job_definitions:
            kwars = {"jobDefinition" : job_def}
            self.client.deregister_job_definition(**kwars)
        logger.info("Job definitions deleted")            
            
    def describe_jobs(self, job_id):
        describe_args = {'jobs' : [job_id]}
        return self.client.describe_jobs(**describe_args)            
            
    def exist_job(self, job_id):
        response = self.describe_jobs(job_id)
        return len(response["jobs"]) != 0            
            
    def exist_jobs_queue(self, name):
        response = self.get_job_queue_info(name)
        return len(response["jobQueues"]) != 0            
            
    def get_job_queue_info(self, name):
        job_queue_info_args = {'jobQueues' : [self.get_resource_name(name)]}
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
            updating_args = {'jobQueue' : self.get_resource_name(name),
                             'state':'DISABLED'}
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
                           'state':'DISABLED'}
            self.client.update_compute_environment(**update_args)
        elif state == "DISABLED":
            delete_args = {'computeEnvironment' : self.get_resource_name(name)}
            logger.info("Compute environment deleted")
            return self.client.delete_compute_environment(**delete_args)        

    def get_compute_env_args(self):
        return {'computeEnvironmentName' : self.aws._lambda.name,
                'serviceRole' : self.aws.batch.service_role,
                'type' : self.aws.batch.type,
                'state' :  self.aws.batch.state,
                'computeResources':{
                    'type': self.aws.batch.comp_type,
                    'minvCpus': self.aws.batch.min_v_cpus,
                    'maxvCpus': self.aws.batch.max_v_cpus,
                    'desiredvCpus': self.aws.batch.desired_v_cpus,
                    'instanceTypes': self.aws.batch.instance_types,                    
                    'subnets' : self.aws.batch.subnets,
                    'securityGroupIds': self.aws.batch.security_group_ids,
                    'instanceRole' : self.aws.batch.instance_role,
                    }
                }
        
    def get_creations_job_queue_args(self):
        return { 
            'computeEnvironmentOrder': [{'computeEnvironment': self.aws._lambda.name, 'order': 1},],
            'jobQueueName':  self.aws._lambda.name,
            'priority': 1,
            'state': self.aws.batch.state,
        }

    def get_resource_name(self, name=None):
        return  name if name else self.aws._lambda.name
        
    def get_describe_compute_env_args(self, name_c=None):
        return {'computeEnvironments' : [self.get_resource_name(name_c)]}
    
    def get_state_and_status_of_compute_env(self, name=None):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return response["computeEnvironments"][0]["state"], response["computeEnvironments"][0]["status"]

    def create_compute_environment(self):
        creation_args = self.get_compute_env_args()
        self.client.create_compute_environment(**creation_args)
        while True:
            state, status = self.get_state_and_status_of_compute_env()
            if state == "ENABLED" and status == "VALID":
                creation_args = self.get_creations_job_queue_args()
                logger.info("Compute environment created.")
                return self.client.create_job_queue(**creation_args)
