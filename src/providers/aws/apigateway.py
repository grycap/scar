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
import src.utils as utils
from src.providers.aws.botoclientfactory import GenericClient

class APIGateway(GenericClient):

    # ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
    default_http_method = "ANY"
    # NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS
    default_authorization_type = "NONE"
    # 'HTTP'|'AWS'|'MOCK'|'HTTP_PROXY'|'AWS_PROXY'
    default_type = "AWS_PROXY"

    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.properties = aws_properties['api_gateway']
        # Get all the log related attributes
        self.function_name = aws_properties['lambda']['name']
        self.lambda_role = aws_properties['iam']['role']

    def get_api_lambda_uri(self):
        self.aws_account_id = utils.find_expression(self.lambda_role, '\d{12}')
        api_gateway_uri = 'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/'
        lambda_uri = 'arn:aws:lambda:us-east-1:{0}:function:{1}/invocations'.format(self.aws_account_id, self.function_name)
        return api_gateway_uri + lambda_uri

    def get_common_args(self, resource_info):
        return {'restApiId' : self.api_id,
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
                'uri' : self.get_api_lambda_uri(),                                
                'requestParameters' : 
                    { 'integration.request.header.X-Amz-Invocation-Type' : 'method.request.header.X-Amz-Invocation-Type' }
                }
        integration = self.get_common_args(resource_info)
        integration.update(args)
        return integration

    def create_api_gateway(self):
        api_info = self.client.create_rest_api(self.properties['name'])
        self.set_api_resources(api_info)
        resource_info = self.client.create_resource(self.api_id, self.root_resource_id, "{proxy+}")
        self.client.create_method(**self.get_method_args(resource_info))
        self.client.set_integration(**self.get_integration_args(resource_info))
        self.client.create_deployment(self.api_id, 'scar')
        self.endpoint = 'https://{0}.execute-api.{1}.amazonaws.com/scar/launch'.format(self.api_id, 'us-east-1')
        logger.info('API Gateway endpoint: {0}'.format(self.endpoint))
        return self.api_id, self.aws_account_id
    
    def delete_api_gateway(self):
        return self.client.delete_rest_api(self.properties['id'])
        
    def set_api_resources(self, api_info):
        self.api_id = api_info['id']
        resources_info = self.client.get_resources(api_info['id'])
        for resource in resources_info['items']:
            if resource['path'] == '/':
                self.root_resource_id = resource['id']
        
