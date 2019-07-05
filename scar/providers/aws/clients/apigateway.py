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
API Gateway creation, deletion and configuration."""

import time
from typing import Dict
from botocore.exceptions import ClientError
from scar.providers.aws.clients import BotoClient
from scar.exceptions import exception, NotExistentApiGatewayWarning
import scar.logger as logger


class APIGatewayClient(BotoClient):
    """A low-level client representing Amazon API Gateway.
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html
    """

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'apigateway'
    _ENDPOINT_CONFIGURATION = {'types': ['REGIONAL']}
    _API_DESCRIPTION = "API created automatically with SCAR"
    _MAX_NUMBER_OF_RETRIES = 5
    _WAIT_BETWEEN_RETIRES = 5

    @exception(logger)
    def create_rest_api(self, api_name: str, count: int = _MAX_NUMBER_OF_RETRIES) -> Dict:
        """Creates a new RestApi resource."""
        try:
            api_args = {'name': api_name,
                        'description': self._API_DESCRIPTION,
                        'endpointConfiguration': self._ENDPOINT_CONFIGURATION}
            return self.client.create_rest_api(**api_args)
        except ClientError as cerr:
            if (cerr.response['Error']['Code'] == 'TooManyRequestsException') \
                and (self._MAX_NUMBER_OF_RETRIES > 0):
                time.sleep(self._WAIT_BETWEEN_RETIRES)
                return self.create_rest_api(api_name, count - 1)
            raise cerr

    @exception(logger)
    def get_resources(self, api_id: str) -> Dict:
        """Lists information about a collection of Resource resources."""
        return self.client.get_resources(restApiId=api_id)

    @exception(logger)
    def create_resource(self, api_id: str, parent_id: str, path_part: str) -> Dict:
        """Creates a new RestApi resource."""
        api_args = {'restApiId': api_id,
                    'parentId': parent_id,
                    'pathPart': path_part}
        return self.client.create_resource(**api_args)

    @exception(logger)
    def create_method(self, **kwargs: Dict) -> Dict:
        """Add a method to an existing Resource resource."""
        return self.client.put_method(**kwargs)

    @exception(logger)
    def set_integration(self, **kwargs: Dict) -> Dict:
        """Sets up a method's integration.
        See https://docs.aws.amazon.com/apigateway/latest/
            developerguide/set-up-lambda-proxy-integrations.html"""
        return self.client.put_integration(**kwargs)

    @exception(logger)
    def create_deployment(self, api_id: str, stage_name: str) -> Dict:
        """Creates a Deployment resource, which makes a
        specified RestApi callable over the internet."""
        api_args = {'restApiId': api_id,
                    'stageName': stage_name}
        return self.client.create_deployment(**api_args)

    @exception(logger)
    def delete_rest_api(self, api_id: str, count: int = _MAX_NUMBER_OF_RETRIES) -> Dict:
        """Deletes the specified API."""
        try:
            return self.client.delete_rest_api(restApiId=api_id)
        except ClientError as cerr:
            if (cerr.response['Error']['Code'] == 'TooManyRequestsException') \
                and (self._MAX_NUMBER_OF_RETRIES > 0):
                time.sleep(self._WAIT_BETWEEN_RETIRES)
                return self.delete_rest_api(api_id, count - 1)
            elif cerr.response['Error']['Code'] == 'NotFoundException':
                raise NotExistentApiGatewayWarning(restApiId=api_id)
            raise cerr
