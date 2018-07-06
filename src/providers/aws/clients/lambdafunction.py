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
from botocore.exceptions import ClientError
import src.logger as logger
import src.utils as utils

class LambdaClient(BotoClient):
    '''A low-level client representing aws LambdaClient.
    https://boto3.readthedocs.io/en/latest/reference/services/lambda.htmll'''    
    
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
        try:
            return self.client.get_function_configuration(FunctionName=function_name_or_arn)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                raise ce
            else:            
                error_msg = "Error getting function data"
                logger.error(error_msg, error_msg + ": %s" % ce)
   
    def get_function_environment_variables(self, function_name):
        return self.get_function_info(function_name)['Environment']
    
    @utils.exception(logger)    
    def update_function(self, **kwargs):
        '''
        Updates the configuration parameters for the specified Lambda function by using the values provided in the request.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.update_function_configuration
        '''
        # Retrieve the global variables already defined
        return self.client.update_function_configuration(**kwargs)
        
    @utils.exception(logger)        
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
            
    @utils.exception(logger)
    def delete_function(self, function_name):
        '''
        Deletes the specified Lambda function code and configuration.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.delete_function
        '''        
        # Delete the lambda function
        return self.client.delete_function(FunctionName=function_name)
    
    @utils.exception(logger)    
    def invoke_function(self, **kwargs):
        '''
        Invokes a specific Lambda function.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.invoke
        '''
        response = self.client.invoke(**kwargs)
        return response
    
    @utils.exception(logger)    
    def add_invocation_permission(self, **kwargs):
        '''
        Adds a permission to the resource policy associated with the specified AWS Lambda function.
        http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.add_permission
        '''
        kwargs['StatementId'] = utils.get_random_uuid4_str()
        kwargs['Action'] = "lambda:InvokeFunction"
        return self.client.add_permission(**kwargs)
            
            