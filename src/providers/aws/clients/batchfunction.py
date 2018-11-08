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

from src.providers.aws.clients.boto import BotoClient
import src.logger as logger

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
        logger.debug("creating compute environment.")
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
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch.html#Batch.Client.delete_job_queue
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

    
    