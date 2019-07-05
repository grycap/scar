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
"""Module with classes and methods that manage the AWS ApiGateway at high level."""

from typing import Dict
from scar.providers.aws import GenericClient
import scar.logger as logger

# 'HTTP'|'AWS'|'MOCK'|'HTTP_PROXY'|'AWS_PROXY'
_DEFAULT_TYPE = "AWS_PROXY"
_DEFAULT_INTEGRATION_METHOD = "POST"
_DEFAULT_REQUEST_PARAMETERS = {"integration.request.header.X-Amz-Invocation-Type":
                               "method.request.header.X-Amz-Invocation-Type"}
# ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
_DEFAULT_HTTP_METHOD = "ANY"
# NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS
_DEFAULT_AUTHORIZATION_TYPE = "NONE"
_DEFAULT_PATH_PART = "{proxy+}"
_DEFAULT_STAGE_NAME = "scar"


class APIGateway(GenericClient):
    """Manage the calls to the ApiGateway client."""

    def __init__(self, aws_properties) -> None:
        super().__init__(aws_properties)
        # {0}: lambda function region, {1}: aws account id, {1}: lambda function name
        self.lambda_uri = "arn:aws:lambda:{region}:{acc_id}:function:{lambdaf_name}/invocations"
        # {0}: api_region, {1}: lambda_uri
        self.uri = "arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_uri}"
        # {0}: api_id, {1}: api_region
        self.endpoint = "https://{api_id}.execute-api.{region}.amazonaws.com/scar/launch"

    def _get_uri(self) -> str:
        lambda_uri_kwargs = {'region': self.aws.region,
                             'acc_id': self.aws.account_id,
                             'lambdaf_name': self.aws.lambdaf.name}
        uri_kwargs = {'region': self.aws.region,
                      'lambda_uri': self.lambda_uri.format(**lambda_uri_kwargs)}
        return self.uri.format(**uri_kwargs)

    def _get_common_args(self, resource_info: Dict) -> Dict:
        return {'restApiId' : self.aws.api_gateway.id,
                'resourceId' : resource_info.get('id', ''),
                'httpMethod' : _DEFAULT_HTTP_METHOD}

    def _get_method_args(self, resource_info: Dict) -> Dict:
        args = {'authorizationType' : _DEFAULT_AUTHORIZATION_TYPE,
                'requestParameters' : {'method.request.header.X-Amz-Invocation-Type' : False}}
        method_args = self._get_common_args(resource_info)
        method_args.update(args)
        return method_args

    def _get_integration_args(self, resource_info: Dict) -> Dict:
        args = {'type' : _DEFAULT_TYPE,
                'integrationHttpMethod' : _DEFAULT_INTEGRATION_METHOD,
                'uri' : self._get_uri(),
                'requestParameters' : _DEFAULT_REQUEST_PARAMETERS}
        integration_args = self._get_common_args(resource_info)
        integration_args.update(args)
        return integration_args

    def _get_resource_id(self) -> str:
        res_id = ""
        resources_info = self.client.get_resources(self.aws.api_gateway.id)
        for resource in resources_info['items']:
            if resource['path'] == '/':
                res_id = resource['id']
                break
        return res_id

    def _set_api_gateway_id(self, api_info: Dict) -> None:
        self.aws.api_gateway.id = api_info.get('id', '')

    def _get_endpoint(self) -> str:
        kwargs = {'api_id': self.aws.api_gateway.id, 'region': self.aws.region}
        return self.endpoint.format(**kwargs)

    def create_api_gateway(self) -> None:
        """Creates an Api Gateway endpoint."""
        api_info = self.client.create_rest_api(self.aws.api_gateway.name)
        self._set_api_gateway_id(api_info)
        resource_info = self.client.create_resource(self.aws.api_gateway.id,
                                                    self._get_resource_id(),
                                                    _DEFAULT_PATH_PART)
        self.client.create_method(**self._get_method_args(resource_info))
        self.client.set_integration(**self._get_integration_args(resource_info))
        self.client.create_deployment(self.aws.api_gateway.id, _DEFAULT_STAGE_NAME)
        logger.info(f'API Gateway endpoint: {self._get_endpoint()}')

    def delete_api_gateway(self, api_gateway_id: str) -> None:
        """Deletes an Api Gateway endpoint."""
        return self.client.delete_rest_api(api_gateway_id)
