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

from .boto import BotoClient
import src.logger as logger
from botocore.exceptions import ClientError
import src.utils as utils

API_DESCRIPTION="API created automatically with SCAR"

class APIGateway():
    
    @utils.lazy_property
    def client(self):
        client = APIGatewayClient()
        return client

    def __init__(self, aws_lambda):
        # Get all the log related attributes
        self.lambda_function = aws_lambda
        self.function_name = aws_lambda.get_property("name")
        self.api_gateway_name = aws_lambda.get_property("api_gateway_name")
        self.lambda_role = aws_lambda.get_property("iam","role")
        # ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
        self.default_http_method = "ANY"
        # NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS
        self.default_authorization_type = "NONE"
        # 'HTTP'|'AWS'|'MOCK'|'HTTP_PROXY'|'AWS_PROXY'
        self.default_type = "AWS_PROXY"

    def get_api_lambda_uri(self):
        self.aws_acc_id = utils.find_expression('\d{12}', self.lambda_role)
        api_gateway_uri = 'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/'
        lambda_uri = 'arn:aws:lambda:us-east-1:{0}:function:{1}/invocations'.format(self.aws_acc_id, self.function_name)
        return api_gateway_uri + lambda_uri

    def create_api_gateway(self):
        api_info = self.client.create_rest_api(self.api_gateway_name)
        self.set_api_resources(api_info)
        resource_info = self.client.create_resource(self.api_id, self.root_resource_id, "{proxy+}")
        self.client.create_method(self.api_id,
                                  resource_info['id'],
                                  self.default_http_method,
                                  self.default_authorization_type)
        self.client.set_integration(self.api_id,
                                    resource_info['id'],
                                    self.default_http_method,
                                    self.default_type,
                                    self.get_api_lambda_uri())
        self.client.create_deployment(self.api_id, 'scar')
        self.lambda_function.add_invocation_permission_from_api_gateway(self.api_id, self.aws_acc_id)    
        
    def set_api_resources(self, api_info):
        self.api_id = api_info['id']
        resources_info = self.client.get_resources(api_info['id'])
        for resource in resources_info['items']:
            if resource['path'] == '/':
                self.root_resource_id = resource['id']
        
class APIGatewayClient(BotoClient):
    '''A low-level client representing Amazon API Gateway.
    https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html'''
    
    def __init__(self, region=None):
        super().__init__('apigateway', region)
    
    def create_rest_api(self, api_name):
        ''' Default type REGIONAL, other possible type EDGE. 
            More info in https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.create_rest_api
        '''
        try:        
            return self.get_client().create_rest_api(name=api_name,
                                                     description=API_DESCRIPTION,
                                                     endpointConfiguration={'types': ['REGIONAL']})
        except ClientError as ce:
            error_msg = "Error creating the '{0}' REST API".format(api_name)
            logger.error(error_msg, error_msg + ": {0}".format(ce))
       
    def get_resources(self, api_id):
        ''' Default type REGIONAL, other possible type EDGE. 
            More info in https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.get_resources
        '''
        try:        
            return self.get_client().get_resources(restApiId=api_id)
        except ClientError as ce:
            error_msg = "Error getting resources for the API ID '{0}'".format(api_id)
            logger.error(error_msg, error_msg + ": {0}".format(ce))       
            
    def create_resource(self, api_id, parent_id, path_part):
        ''' Default type REGIONAL, other possible type EDGE. 
            More info in https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.create_rest_api
        '''
        try:        
            return self.get_client().create_resource(restApiId=api_id,
                                                     parentId=parent_id,
                                                     pathPart=path_part)
        except ClientError as ce:
            error_msg = "Error creating the resource '{0}' in the API '{1}'".format(path_part, api_id)
            logger.error(error_msg, error_msg + ": {0}".format(ce))
            
    def create_method(self, api_id, resource_id, http_method, authorization_type):
        ''' Add a method to an existing Resource resource.
            More info in https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.put_method
        '''
        try:        
            return self.get_client().put_method(restApiId=api_id,
                                                resourceId=resource_id,
                                                httpMethod=http_method,
                                                authorizationType=authorization_type)
        except ClientError as ce:
            error_msg = "Error creating the method '{0}' in the API '{1}'".format(http_method, api_id)
            logger.error(error_msg, error_msg + ": {0}".format(ce))
            
    def set_integration(self, api_id, resource_id, http_method, aws_type, api_uri):
        ''' Sets up a method's integration.
            More info in https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.put_integration
            Also https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
        '''
        try:
            return self.get_client().put_integration(restApiId=api_id,
                                                     resourceId=resource_id,
                                                     httpMethod=http_method,
                                                     type=aws_type,
                                                     integrationHttpMethod='POST',
                                                     uri=api_uri)
            '''
            arn:aws:apigateway:{region}:{subdomain.service|service}:path|action/{service_api}
            arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:HelloWorld/invocations
            arn:aws:iam::974349055189:role/lambda-s3-recursive-role
            '''
        except ClientError as ce:
            error_msg = "Error integrating the Lambda function with the API Gateway"
            logger.error(error_msg, error_msg + ": {0}".format(ce))
            
    def create_deployment(self, api_id, stage_name):
        ''' Creates a Deployment resource, which makes a specified RestApi callable over the internet.
            More info in https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.create_deployment
        '''
        try:
            return self.get_client().create_deployment(restApiId=api_id, stageName=stage_name)
        except ClientError as ce:
            error_msg = "Error creating the deployment of the API '{0}'".format(api_id)
            logger.error(error_msg, error_msg + ": {0}".format(ce))                                           
        