# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from src.providers.aws.botoclientfactory import GenericClient
import src.logger as logger

class Batch(GenericClient):

    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.lambda_properties = aws_properties['lambda']
        self.batch_properties = aws_properties['batch']
        self.iam_properties = aws_properties['iam']
        self.instance_role = "arn:aws:iam::{0}:instance-profile/ecsInstanceRole".format(aws_properties['account_id'])
        self.service_role = "arn:aws:iam::{0}:role/service-role/AWSBatchServiceRole".format(aws_properties['account_id'])  
    
    def exist_compute_environments(self,name):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        response = self.client.describe_compute_environments(**creation_args)
        return len(response["computeEnvironments"]) > 0

    def delete_compute_environment(self,name):
        self.delete_job_definitions(name)
        self.delete_job_queue(name)
        self.delete_compute_env(name)
            
    def get_job_definitions(self, jobs_info):
        return ["{0}:{1}".format(definition['jobDefinitionName'], definition['revision']) for definition in jobs_info['jobDefinitions']]
            
    def delete_job_definitions(self, name):
        job_definitions = []
        # Get IO definitions (if any)
        kwargs = {"jobDefinitionName" : '{0}-io'.format(name)}
        io_job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(self.get_job_definitions(io_job_info))
        # Get main job definition
        kwargs = {"jobDefinitionName" : name}
        job_info = self.client.describe_job_definitions(**kwargs)
        job_definitions.extend(self.get_job_definitions(job_info))
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
        creation_args = {'jobQueues' : [self.get_resource_name(name)]}
        return self.client.describe_job_queues(**creation_args)                 
    
    def delete_job_queue(self, name):
        while True:
            response = self.get_job_queue_info(name)
            state = response["jobQueues"][0]["state"]
            status = response["jobQueues"][0]["status"]
            if status == "VALID":
                if state == "ENABLED":
                    updating_args = {'jobQueue' : self.get_resource_name(name),
                                     'state':'DISABLED'}
                    self.client.update_job_queue(**updating_args)
                elif state == "DISABLED":
                    deleting_args = {'jobQueue': self.get_resource_name(name)}
                    logger.info("Job queue deleted")
                    return self.client.delete_job_queue(**deleting_args)
                    
    def delete_compute_env(self, name):
        while True:
            state, status = self.get_state_and_status_of_compute_env(name)
            if(state=="ENABLED"):
                update_args = {'computeEnvironment': self.get_resource_name(name),
                               'state':'DISABLED'}
                self.client.update_compute_environment(**update_args)
            elif(state == "DISABLED" and status == "VALID" and (not self.exist_jobs_queue(name))):
                delete_args = {'computeEnvironment' : self.get_resource_name(name)}
                logger.info("Compute environment deleted")
                return self.client.delete_compute_environment(**delete_args)

    def get_compute_env_args(self):
        return {'computeEnvironmentName' : self.lambda_properties['name'],
                'serviceRole' : self.service_role,
                'type' : self.batch_properties['type'],
                'state' :  self.batch_properties['state'],
                'computeResources':{
                    'type': self.batch_properties['comp_type'],
                    'minvCpus': self.batch_properties['min_v_cpus'],
                    'maxvCpus': self.batch_properties['max_v_cpus'],
                    'desiredvCpus': self.batch_properties['desired_v_cpus'],
                    'instanceTypes': self.batch_properties['instance_types'],                    
                    'subnets' : self.batch_properties['subnets'],
                    'securityGroupIds': self.batch_properties['security_group_ids'],
                    'instanceRole' : self.instance_role,
                    }
                }
        
    def get_creations_job_queue_args(self):
        return { 
            'computeEnvironmentOrder': [{'computeEnvironment': self.lambda_properties["name"], 'order': 1},],
            'jobQueueName': self.lambda_properties["name"],
            'priority': 1,
            'state': self.batch_properties['state'],
        }

    def get_resource_name(self, name=None):
        return  name if name else self.lambda_properties["name"]
        
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
