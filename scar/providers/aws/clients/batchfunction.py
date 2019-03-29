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

from scar.providers.aws.clients.boto import BotoClient
import scar.logger as logger

class BatchClient(BotoClient):
    '''A low-level client representing aws batchClient.
    http://boto3.readthedocs.io/en/latest/reference/services/batch.html'''    
    
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'batch'
                
    def create_compute_environment(self, **kwargs):
        '''
        Creates a new compute environment.
        http://boto3.readthedocs.io/en/latest/reference/services/batch.html#Batch.Client.create_compute_environment
        '''
        logger.debug("Creating compute environment.")
        return self.client.create_compute_environment(**kwargs)
    
    def create_job_queue(self, **kwargs):
        '''
        Creates a new job queue.
        http://boto3.readthedocs.io/en/latest/reference/services/batch.html#Batch.Client.create_job_queue
        '''
        logger.debug("Creating job queue.")
        return self.client.create_job_queue(**kwargs)

    def describe_compute_environments(self, **kwargs):
        '''
        Creates a new job queue.
        http://boto3.readthedocs.io/en/latest/reference/services/batch.html#Batch.Client.describe_compute_environments
        '''
        logger.debug("Describing Compute Environment.")
        return self.client.describe_compute_environments(**kwargs)

    def describe_job_queues(self, **kwargs):
        '''
        Describe a new job queue.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.describe_job_queues
        '''
        logger.debug("Describing job queue.")
        return self.client.describe_job_queues(**kwargs)
    
    def describe_job_definitions(self, **kwargs):
        '''
        Describes a list of job definitions.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.describe_job_definitions
        '''
        logger.debug("Describing job definition.")
        return self.client.describe_job_definitions(**kwargs)
    
    def deregister_job_definition(self, **kwargs):
        '''
        Deregisters an AWS Batch job definition.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.deregister_job_definition
        '''
        logger.debug("Deleting job definition.")
        return self.client.deregister_job_definition(**kwargs)     

    def update_job_queue(self, **kwargs):
        '''
        update a job queue.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.update_job_queue
        '''
        logger.debug("Updating job queue.")
        return self.client.update_job_queue(**kwargs)
    
    def delete_job_queue(self, **kwargs):
        '''
        Delete a job queue.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client._delete_job_queue
        '''
        logger.debug("Deleting job queue.")
        return self.client.delete_job_queue(**kwargs)

    
    def update_compute_environment(self, **kwargs):
        '''
        update a compute environment.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.update_compute_environment
        '''
        logger.debug("Updating compute environment.")
        return self.client.update_compute_environment(**kwargs)
    
    def delete_compute_environment(self, **kwargs):
        '''
        Delete a compute environmet.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.delete_compute_environment
        '''
        logger.debug("Deleting compute environment.")
        return self.client.delete_compute_environment(**kwargs)
    
    def describe_jobs(self, **kwargs):
        '''
        Describe a job.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.describe_jobs
        '''
        logger.debug("Describing a job.")
        return self.client.describe_jobs(**kwargs)

    
    