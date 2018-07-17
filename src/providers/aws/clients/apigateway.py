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

from src.providers.aws.clients.boto import BotoClient
import src.logger as logger
from botocore.exceptions import ClientError
import time
import src.exceptions as excp



class APIGatewayClient(BotoClient):
    '''A low-level client representing Amazon API Gateway.
    https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html'''
    
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'apigateway'
    endpoint_configuration = {'types': ['REGIONAL']}
    API_DESCRIPTION="API created automatically with SCAR"
    MAX_NUMBER_OF_RETRIES = 5
    WAIT_BETWEEN_RETIRES = 5
        
    @excp.exception(logger)        
    def create_rest_api(self, name, count=MAX_NUMBER_OF_RETRIES):
        """ 
        Creates a new RestApi resource.
        https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.create_rest_api
        
        :param str name: The name of the RestApi.
        :param int count: (Optional) The maximum number of retries to create the API
        """
        try:        
            return self.client.create_rest_api(name=name,
                                               description=self.API_DESCRIPTION,
                                               endpointConfiguration=self.endpoint_configuration)
        except ClientError as ce:
            if (ce.response['Error']['Code'] == 'TooManyRequestsException') and (self.MAX_NUMBER_OF_RETRIES > 0):
                time.sleep(self.WAIT_BETWEEN_RETIRES)
                return self.create_rest_api(name, count-1)
        except:
            raise excp.ApiCreationError(api_name=name)
       
    @excp.exception(logger)       
    def get_resources(self, api_id):
        ''' Lists information about a collection of Resource resources.
            https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.get_resources
        '''
        return self.client.get_resources(restApiId=api_id)      
            
    @excp.exception(logger)             
    def create_resource(self, api_id, parent_id, path_part):
        ''' Creates a new RestApi resource.
            https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.create_rest_api
        '''
        return self.client.create_resource(restApiId=api_id, parentId=parent_id, pathPart=path_part)
           
    @excp.exception(logger)            
    def create_method(self, **kwargs):
        ''' Add a method to an existing Resource resource.
           https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.put_method
        '''
        return self.client.put_method(**kwargs)
            
    @excp.exception(logger)            
    def set_integration(self, **kwargs):
        ''' Sets up a method's integration.
            https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.put_integration
            Also https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
        '''
        return self.client.put_integration(**kwargs)
            
    @excp.exception(logger)            
    def create_deployment(self, api_id, stage_name):
        ''' Creates a Deployment resource, which makes a specified RestApi callable over the internet.
            https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.create_deployment
        '''
        return self.client.create_deployment(restApiId=api_id, stageName=stage_name)
            
    @excp.exception(logger)            
    def delete_rest_api(self, api_id, count=MAX_NUMBER_OF_RETRIES):
        ''' Deletes the specified API.
            https://boto3.readthedocs.io/en/latest/reference/services/apigateway.html#APIGateway.Client.delete_rest_api
        '''
        try:
            return self.client.delete_rest_api(restApiId=api_id)
        except ClientError as ce:
            if (ce.response['Error']['Code'] == 'TooManyRequestsException') and (self.MAX_NUMBER_OF_RETRIES > 0):
                time.sleep(self.WAIT_BETWEEN_RETIRES)
                return self.delete_rest_api(api_id, count-1)
            else:
                raise            
