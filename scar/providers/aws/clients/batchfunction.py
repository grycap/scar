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
"""Module with the class necessary to manage the
Batch creation, deletion and configuration."""

from typing import Dict
from scar.providers.aws.clients import BotoClient
import scar.logger as logger
from scar.exceptions import exception


class BatchClient(BotoClient):
    """A low-level client representing aws batchClient.
    DOC_URL: http://boto3.readthedocs.io/en/latest/reference/services/batch.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'batch'

    @exception(logger)
    def create_compute_environment(self, **kwargs: Dict) -> Dict:
        """Creates a new compute environment."""
        logger.debug("Creating compute environment.")
        return self.client.create_compute_environment(**kwargs)

    @exception(logger)
    def create_job_queue(self, **kwargs: Dict) -> Dict:
        """Creates a new job queue."""
        logger.debug("Creating job queue.")
        return self.client.create_job_queue(**kwargs)

    @exception(logger)
    def register_job_definition(self, **kwargs: Dict) -> Dict:
        """Registers a new job definition."""
        logger.debug("Registering job definition.")
        return self.client.register_job_definition(**kwargs)

    @exception(logger)
    def describe_compute_environments(self, **kwargs: Dict) -> Dict:
        """Describes compute environments."""
        logger.debug("Describing Compute Environment.")
        return self.client.describe_compute_environments(**kwargs)

    @exception(logger)
    def describe_job_queues(self, **kwargs: Dict) -> Dict:
        """Describe a new job queue."""
        logger.debug("Describing job queue.")
        return self.client.describe_job_queues(**kwargs)

    @exception(logger)
    def describe_job_definitions(self, **kwargs: Dict) -> Dict:
        """Describes a list of job definitions."""
        logger.debug("Describing job definition.")
        return self.client.describe_job_definitions(**kwargs)

    @exception(logger)
    def deregister_job_definition(self, **kwargs: Dict) -> Dict:
        """Deregisters an AWS Batch job definition."""
        logger.debug("Deleting job definition.")
        return self.client.deregister_job_definition(**kwargs)

    @exception(logger)
    def update_job_queue(self, **kwargs: Dict) -> Dict:
        """Updates a job queue."""
        logger.debug("Updating job queue.")
        return self.client.update_job_queue(**kwargs)

    @exception(logger)
    def delete_job_queue(self, **kwargs: Dict) -> Dict:
        """Deletes a job queue."""
        logger.debug("Deleting job queue.")
        return self.client.delete_job_queue(**kwargs)

    @exception(logger)
    def update_compute_environment(self, **kwargs: Dict) -> Dict:
        """Updates a compute environment."""
        logger.debug("Updating compute environment.")
        return self.client.update_compute_environment(**kwargs)

    @exception(logger)
    def delete_compute_environment(self, **kwargs: Dict) -> Dict:
        """Deletes a compute environment."""
        logger.debug("Deleting compute environment.")
        return self.client.delete_compute_environment(**kwargs)

    @exception(logger)
    def describe_jobs(self, **kwargs: Dict) -> Dict:
        """Describes a batch job."""
        logger.debug("Describing a job.")
        return self.client.describe_jobs(**kwargs)
