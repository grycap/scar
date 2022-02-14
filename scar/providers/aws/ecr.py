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
"""Module with classes and methods to manage the
CloudWatch Log functionalities at high level."""

from typing import Dict
from scar.providers.aws import GenericClient


class ECR(GenericClient):
    """Manages the AWS ElasticContainerRegistry functionality"""
    
    def __init__(self, resources_info: Dict):
        super().__init__()
        self.resources_info = resources_info

    def get_authorization_token(self) -> str:
        """Retrieves an authorization token."""
        return self.client.get_authorization_token()

    def get_registry_url(self) -> str:
        """Retrieves the registry URL."""
        registry_id = self.client.get_registry_id()
        return "%s.dkr.ecr.us-east-1.amazonaws.com" % registry_id

    def get_repository_uri(self, repository_name: str) -> str:
        """Check if a repository exists."""
        response = self.client.describe_repositories(repositoryNames=[repository_name])
        if response:
            return response["repositories"][0]["repositoryUri"]
        else:
            return None

    def create_repository(self, repository_name: str) -> str:
        """Creates a repository."""
        response = self.client.create_repository(repository_name)
        return response["repository"]["repositoryUri"]

    def delete_repository(self, repository_name: str):
        self.client.delete_repository(repository_name)