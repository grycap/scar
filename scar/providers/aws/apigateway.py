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

class APIGateway(GenericClient):

    def __init__(self, aws_properties):
        super().__init__(aws_properties)
        self._initialize_properties()
        self._set_api_lambda_uri()

    def _initialize_properties(self):
        # {0}: api_region
        self.aws.api_gateway.generic_uri = 'arn:aws:apigateway:{0}:lambda:path/2015-03-31/functions/{1}'
        # {0}: lambda function region, {1}: aws account id, {1}: lambda function name
        self.aws.api_gateway.generic_lambda_uri = 'arn:aws:lambda:{0}:{1}:function:{2}/invocations'
        # ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
        self.aws.api_gateway.default_http_method = "ANY"
        # NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS
        self.aws.api_gateway.default_authorization_type = "NONE"
        # 'HTTP'|'AWS'|'MOCK'|'HTTP_PROXY'|'AWS_PROXY'
        self.aws.api_gateway.default_type = "AWS_PROXY"
        # Used in the lambda-proxy integration
        self.aws.api_gateway.default_request_parameters = {'integration.request.header.X-Amz-Invocation-Type' :
                                                           'method.request.header.X-Amz-Invocation-Type' }
        # {0}: api_id, {1}: api_region
        self.aws.api_gateway.generic_endpoint = 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'
        

    def _set_api_lambda_uri(self):
        self.aws.api_gateway.lambda_uri = self.aws.api_gateway.generic_lambda_uri.format(self.aws.region,
                                                                                         self.aws.account_id,
                                                                                         self.aws._lambda.name)
        self.aws.api_gateway.uri = self.aws.api_gateway.generic_uri.format(self.aws.region, self.aws.api_gateway.lambda_uri)

    def _get_common_args(self, resource_info):
        return {'restApiId' : self.aws.api_gateway.id,
                'resourceId' : resource_info['id'],
                'httpMethod' : self.aws.api_gateway.default_http_method}

    def _get_method_args(self, resource_info):
        args = {'authorizationType' : self.aws.api_gateway.default_authorization_type,
                'requestParameters' : {'method.request.header.X-Amz-Invocation-Type' : False} }
        method = self._get_common_args(resource_info)
        method.update(args)
        return method        

    def _get_integration_args(self, resource_info):
        args = {'type' : self.aws.api_gateway.default_type,
                'integrationHttpMethod' : 'POST',
                'uri' : self.aws.api_gateway.uri,
                'requestParameters' : self.aws.api_gateway.default_request_parameters }
        integration = self._get_common_args(resource_info)
        integration.update(args)
        return integration

    def _set_api_ids(self, api_info):
        self.aws.api_gateway.id = api_info['id']
        resources_info = self.client.get_resources(api_info['id'])
        for resource in resources_info['items']:
            if resource['path'] == '/':
                self.aws.api_gateway.root_resource_id = resource['id']
                break
                
    def create_api_gateway(self):
        api_info = self.client.create_rest_api(self.aws.api_gateway.name)
        self._set_api_ids(api_info)
        resource_info = self.client.create_resource(self.aws.api_gateway.id, self.aws.api_gateway.root_resource_id, "{proxy+}")
        self.client.create_method(**self._get_method_args(resource_info))
        self.client.set_integration(**self._get_integration_args(resource_info))
        self.client.create_deployment(self.aws.api_gateway.id, 'scar')
        self.endpoint = self.aws.api_gateway.generic_endpoint.format(self.aws.api_gateway.id, self.aws.region)
        logger.info('API Gateway endpoint: {0}'.format(self.endpoint))
    
    def delete_api_gateway(self):
        return self.client.delete_rest_api(self.aws.api_gateway.id)
