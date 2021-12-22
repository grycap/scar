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
Cloudwatch Logs creation, deletion and configuration."""

from datetime import datetime
from typing import Dict
from scar.exceptions import exception
from scar.providers.aws.clients import BotoClient
import scar.logger as logger


class ElasticContainerRegistryClient(BotoClient):
    """A low-level client representing Amazon Elastic Container Registry.
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/services/ecr.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'ecr'

    def __init__(self, client_args: Dict):
        super().__init__(client_args)
        self.token = None

    @exception(logger)
    def get_authorization_token(self) -> str:
        """Retrieves an authorization token."""
        if self.token:
            now = datetime.now()
            if self.token['expiresAt'] > (now + 60):
                return self.token["authorizationToken"]

        response = self.client.get_authorization_token()
        self.token = response["authorizationData"][0]
        return self.token["authorizationToken"]
