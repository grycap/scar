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

import src.logger as logger
from src.providers.aws.botoclientfactory import GenericClient

class APIGateway(GenericClient):

    # ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
    default_http_method = "ANY"
    # NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS
    default_authorization_type = "NONE"
    # 'HTTP'|'AWS'|'MOCK'|'HTTP_PROXY'|'AWS_PROXY'
    default_type = "AWS_PROXY"
    # Used in the lambda-proxy integration
    default_request_parameters = { 'integration.request.header.X-Amz-Invocation-Type' : 'method.request.header.X-Amz-Invocation-Type' }
    # {0}: api_region
    generic_api_gateway_uri = 'arn:aws:apigateway:{0}:lambda:path/2015-03-31/functions/'
    # {0}: lambda function region, {1}: aws account id, {1}: lambda function name
    generic_lambda_uri = 'arn:aws:lambda:{0}:{1}:function:{2}/invocations'
    # {0}: api_id, {1}: api_region
    generic_endpoint = 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'

    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.properties = aws_properties['api_gateway']
        self.set_api_lambda_uri()

    def set_api_lambda_uri(self):
        self.properties['lambda_uri'] = self.generic_lambda_uri.format(self.aws_properties['region'],
                                                                       self.aws_properties['account_id'],
                                                                       self.aws_properties['lambda']['name'])
        self.properties['uri'] = self.generic_api_gateway_uri.format(self.aws_properties['region']) + self.properties['lambda_uri']

    def get_common_args(self, resource_info):
        return {'restApiId' : self.properties['id'],
                'resourceId' : resource_info['id'],
                'httpMethod' : self.default_http_method}

    def get_method_args(self, resource_info):
        args = {'authorizationType' : self.default_authorization_type,
                'requestParameters' : {'method.request.header.X-Amz-Invocation-Type' : False}}
        method = self.get_common_args(resource_info)
        method.update(args)
        return method        

    def get_integration_args(self, resource_info):
        args = {'type' : self.default_type,
                'integrationHttpMethod' : 'POST',
                'uri' : self.properties['uri'],                                
                'requestParameters' : self.default_request_parameters
                }
        integration = self.get_common_args(resource_info)
        integration.update(args)
        return integration

    def create_api_gateway(self):
        api_info = self.client.create_rest_api(self.properties['name'])
        self.set_api_ids(api_info)
        resource_info = self.client.create_resource(self.properties['id'], self.properties['root_resource_id'], "{proxy+}")
        self.client.create_method(**self.get_method_args(resource_info))
        self.client.set_integration(**self.get_integration_args(resource_info))
        self.client.create_deployment(self.properties['id'], 'scar')
        self.endpoint = self.generic_endpoint.format(self.properties['id'], self.aws_properties['region'])
        logger.info('API Gateway endpoint: {0}'.format(self.endpoint))
    
    def delete_api_gateway(self):
        return self.client.delete_rest_api(self.properties['id'])
        
    def set_api_ids(self, api_info):
        self.properties['id'] = api_info['id']
        resources_info = self.client.get_resources(api_info['id'])
        for resource in resources_info['items']:
            if resource['path'] == '/':
                self.properties['root_resource_id'] = resource['id']
        
