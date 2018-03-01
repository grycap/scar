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
from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ReadTimeout
import logging
import utils.functionutils as utils
import uuid
from boto.awslambda.exceptions import ResourceNotFoundException


class LambdaClient(BotoClient):
    '''A low-level client representing aws LambdaClient.
    https://boto3.readthedocs.io/en/latest/reference/services/lambda.htmll'''    
    
    def __init__(self, region=None):
        super().__init__('lambda', region)
    
    def create_function_name(self, image_id_or_path):
        parsed_id_or_path = image_id_or_path.replace('/', ',,,').replace(':', ',,,').replace('.', ',,,').split(',,,')
        name = 'scar-%s' % '-'.join(parsed_id_or_path)
        i = 1
        while self.find_function_name(name):
            name = 'scar-%s-%s' % ('-'.join(parsed_id_or_path), str(i))
            i += 1
        return name    
    
    def find_function_name(self, function_name):
        try:
            # If this call works the function exists
            self.get_client().get_function(FunctionName=function_name)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:   
                print("Error listing the lambda functions")
                logging.error("Error listing the lambda functions: %s" % ce)
                utils.finish_failed_execution()
    
    def check_function_name_not_exists(self, function_name):
        if not self.find_function_name(function_name):
            print("Function '%s' doesn't exist." % function_name)
            logging.error("Function '%s' doesn't exist." % function_name)
            utils.finish_failed_execution()
    
    def check_function_name_exists(self, function_name):
        if self.find_function_name(function_name):
            print("Function name '%s' already used." % function_name)
            logging.error ("Function name '%s' already used." % function_name)
            utils.finish_failed_execution()
    
    def update_function_timeout(self, function_name, timeout):
        try:
            self.get_client().update_function_configuration(FunctionName=function_name,
                                                                   Timeout=self.check_time(timeout))
        except ClientError as ce:
            print("Error updating lambda function timeout")
            logging.error("Error updating lambda function timeout: %s" % ce)
    
    def update_function_memory(self, function_name, memory):
        try:
            self.get_client().update_function_configuration(FunctionName=function_name,
                                                                   MemorySize=memory)
        except ClientError as ce:
            print("Error updating lambda function memory")
            logging.error("Error updating lambda function memory: %s" % ce)
            
    def create_function(self, aws_lambda): 
        try:
            logging.info("Creating lambda function.")
            response = self.get_client().create_function(FunctionName=aws_lambda.name,
                                                         Runtime=aws_lambda.runtime,
                                                         Role=aws_lambda.role,
                                                         Handler=aws_lambda.handler,
                                                         Code=aws_lambda.code,
                                                         Environment=aws_lambda.environment,
                                                         Description=aws_lambda.description,
                                                         Timeout=aws_lambda.time,
                                                         MemorySize=aws_lambda.memory,
                                                         Tags=aws_lambda.tags)
            aws_lambda.function_arn = response['FunctionArn']
            return response
        except ClientError as ce:
            print("Error creating lambda function")
            logging.error("Error creating lambda function: %s" % ce)        
        
    def get_function_environment_variables(self, function_name):
        return self.get_client().get_function(FunctionName=function_name)['Configuration']['Environment']
    
    def update_function_env_variables(self, function_name, env_vars):
        try:
            # Retrieve the global variables already defined
            lambda_env_variables = self.get_function_environment_variables(function_name)
            self.parse_environment_variables(lambda_env_variables, env_vars)
            self.get_client().update_function_configuration(FunctionName=function_name,
                                                                    Environment=lambda_env_variables)
        except ClientError as ce:
            print("Error updating the environment variables of the lambda function")
            logging.error("Error updating the environment variables of the lambda function: %s" % ce)
    
    def add_lambda_permissions(self, lambda_name, bucket_name):
        try:
            self.get_client().add_permission(FunctionName=lambda_name,
                                             StatementId=str(uuid.uuid4()),
                                             Action="lambda:InvokeFunction",
                                             Principal="s3.amazonaws.com",
                                             SourceArn='arn:aws:s3:::%s' % bucket_name
                                            )
        except ClientError as ce:
            print("Error setting lambda permissions")
            logging.error("Error setting lambda permissions: %s" % ce)
    
    def get_function_info_by_arn(self, function_arn):
        try:
            return self.get_client().get_function(FunctionName=function_arn)
        except ClientError as ce:
            print("Error getting function info by arn")
            logging.error("Error getting function info by arn: %s" % ce)
            
    def delete_lambda_function(self, function_name):
        try:
            # Delete the lambda function
            return self.get_client().delete_function(FunctionName=function_name)
        except ClientError as ce:
            print("Error deleting the lambda function")
            logging.error("Error deleting the lambda function: %s" % ce)
    
    def invoke_lambda_function(self, aws_lambda):
        response = {}
        try:
            response = self.get_client().invoke(FunctionName=aws_lambda.name,
                                                InvocationType=aws_lambda.invocation_type,
                                                LogType=aws_lambda.log_type,
                                                Payload=aws_lambda.payload)
        except ClientError as ce:
            print("Error invoking lambda function")
            logging.error("Error invoking lambda function: %s" % ce)
            utils.finish_failed_execution()
    
        except ReadTimeout as rt:
            print("Timeout reading connection pool")
            logging.error("Timeout reading connection pool: %s" % rt)
            utils.finish_failed_execution()
        return response                                        
        
