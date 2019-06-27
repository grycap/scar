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
Lambda function and layers creation, deletion and configuration."""

from typing import Dict, List, Optional
from scar.providers.aws.clients import BotoClient
import scar.exceptions as excp
import scar.logger as logger
from scar.utils import StrUtils


class LambdaClient(BotoClient):
    """A low-level client representing aws LambdaClient.
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/services/lambda.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'lambda'

    def create_function(self, **kwargs: Dict) -> Dict:
        """Creates a new Lambda function."""
        logger.debug("Creating lambda function.")
        return self.client.create_function(**kwargs)

    def get_function_info(self, function_name_or_arn: str) -> Dict:
        """Returns the configuration information
        of the Lambda function."""
        return self.client.get_function_configuration(FunctionName=function_name_or_arn)

    @excp.exception(logger)
    def update_function_configuration(self, **kwargs: Dict) -> Dict:
        """Updates the configuration parameters for the specified
        Lambda function by using the values provided in the request."""
        # Retrieve the global variables already defined
        return self.client.update_function_configuration(**kwargs)

    @excp.exception(logger)
    def list_functions(self, next_token: Optional[str]=None) -> List:
        """Returns a list of your Lambda functions."""
        logger.debug("Listing lambda functions.")
        functions = []
        kwargs = {}
        if next_token:
            kwargs['Marker'] = next_token
        functions_info = self.client.list_functions(**kwargs)
        if 'Functions' in functions_info and functions_info['Functions']:
            functions.extend(functions_info['Functions'])
        if 'NextMarker' in functions:
            functions.extend(self.list_layers(next_token=functions_info['NextMarker']))
        return functions

    @excp.exception(logger)
    def list_layers(self, next_token: Optional[str]=None) -> List:
        """Lists function layers and shows information
        about the latest version of each."""
        logger.debug("Listing lambda layers.")
        layers = []
        kwargs = {}
        if next_token:
            kwargs['Marker'] = next_token
        layers_info = self.client.list_layers(**kwargs)
        if 'Layers' in layers_info and layers_info['Layers']:
            layers.extend(layers_info['Layers'])
        if 'NextMarker' in layers_info:
            layers.extend(self.list_layers(next_token=layers_info['NextMarker']))
        return layers

    @excp.exception(logger)
    def delete_function(self, function_name: str) -> Dict:
        """Deletes the specified Lambda
        function code and configuration."""
        # Delete the lambda function
        return self.client.delete_function(FunctionName=function_name)

    @excp.exception(logger)
    def invoke_function(self, **kwargs: Dict) -> Dict:
        """Invokes a specific Lambda function."""
        return self.client.invoke(**kwargs)

    @excp.exception(logger)
    def add_invocation_permission(self, **kwargs: Dict) -> Dict:
        """Adds a permission to the resource policy associated
        with the specified AWS Lambda function."""
        kwargs['StatementId'] = StrUtils.get_random_uuid4_str()
        kwargs['Action'] = "lambda:InvokeFunction"
        return self.client.add_permission(**kwargs)

    def publish_layer_version(self, **kwargs: Dict) -> Dict:
        """Creates a function layer from a ZIP archive."""
        logger.debug("Publishing lambda layer.")
        return self.client.publish_layer_version(**kwargs)
