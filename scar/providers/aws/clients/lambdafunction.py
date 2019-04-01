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

from scar.providers.aws.clients.boto import BotoClient
import scar.exceptions as excp
import scar.logger as logger
import scar.utils as utils

class LambdaClient(BotoClient):
    '''A low-level client representing aws LambdaClient.
    https://boto3.readthedocs.io/en/latest/reference/services/lambda.htmll'''    
    
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'lambda'
                
    def create_function(self, **kwargs):
        '''
        Creates a new Lambda function.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.create_function
        '''
        logger.debug("Creating lambda function.")
        return self.client.create_function(**kwargs)

    def get_function_info(self, function_name_or_arn):
        '''
        Returns the configuration information of the Lambda function.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.get_function_configuration
        '''
        return self.client.get_function_configuration(FunctionName=function_name_or_arn)
   
    @excp.exception(logger)    
    def update_function_configuration(self, **kwargs):
        '''
        Updates the configuration parameters for the specified Lambda function by using the values provided in the request.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.update_function_configuration
        '''
        # Retrieve the global variables already defined
        return self.client.update_function_configuration(**kwargs)
        
    @excp.exception(logger)        
    def list_functions(self):
        '''
        Returns a list of your Lambda functions.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.list_functions
        '''
        functions = []
        response = self.client.list_functions();
        if "Functions" in response:
            functions.extend(response['Functions'])
        while ('NextMarker' in response) and (response['NextMarker']):
            result = self.client.list_functions(Marker=response['NextMarker']);
            if "Functions" in result:
                functions.extend(result['Functions'])            
        return functions                      
            
    @excp.exception(logger)
    def delete_function(self, function_name):
        '''
        Deletes the specified Lambda function code and configuration.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.delete_function
        '''        
        # Delete the lambda function
        return self.client.delete_function(FunctionName=function_name)
    
    @excp.exception(logger)    
    def invoke_function(self, **kwargs):
        '''
        Invokes a specific Lambda function.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.invoke
        '''
        response = self.client.invoke(**kwargs)
        return response
    
    @excp.exception(logger)    
    def add_invocation_permission(self, **kwargs):
        '''
        Adds a permission to the resource policy associated with the specified AWS Lambda function.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.add_permission
        '''
        kwargs['StatementId'] = utils.get_random_uuid4_str()
        kwargs['Action'] = "lambda:InvokeFunction"
        return self.client.add_permission(**kwargs)
    
    def list_layers(self, **kwargs):
        '''
        Lists function layers and shows information about the latest version of each.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.list_layers
        '''
        logger.debug("Listing lambda layers.")
        return self.client.list_layers(**kwargs)     
    
    def publish_layer_version(self, **kwargs):
        '''
        Creates a function layer from a ZIP archive.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.publish_layer_version
        '''
        logger.debug("Publishing lambda layer.")
        return self.client.publish_layer_version(**kwargs)    
            
            
