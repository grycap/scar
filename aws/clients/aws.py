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

import boto3
import botocore
import logging
import utils.outputtype as outputType

# Default values
botocore_client_read_timeout = 360
default_aws_region = "us-east-1"

class AWS(object):
    
    def __init__(self, client_name, region=None):
        if region is None:
            region = default_aws_region
        boto_config = botocore.config.Config(read_timeout=botocore_client_read_timeout)            
        self.client = boto3.client(client_name, region_name=region, config=boto_config)        
    
    def get_access_key(self):
        session = boto3.Session()
        credentials = session.get_credentials()
        return credentials.access_key
      
    def parse_delete_function_response(self, function_name, reponse, output_type):
        if output_type == outputType.VERBOSE:
            logging.info('LambdaOutput', reponse)
        elif output_type == outputType.JSON:            
            logging.info('LambdaOutput', { 'RequestId' : reponse['ResponseMetadata']['RequestId'],
                                         'HTTPStatusCode' : reponse['ResponseMetadata']['HTTPStatusCode'] })
        else:
            logging.info("Function '%s' successfully deleted." % function_name)
        print("Function '%s' successfully deleted." % function_name)                 
    
    def parse_delete_log_response(self, function_name, response, output_type):
        if response:
            log_group_name = '/aws/lambda/%s' % function_name
            if output_type == outputType.VERBOSE:
                logging.info('CloudWatchOutput', response)
            elif output_type == outputType.JSON:            
                logging.info('CloudWatchOutput', { 'RequestId' : response['ResponseMetadata']['RequestId'],
                                                                   'HTTPStatusCode' : response['ResponseMetadata']['HTTPStatusCode'] })
            else:
                logging.info("Log group '%s' successfully deleted." % log_group_name)
            print("Log group '%s' successfully deleted." % log_group_name)
    
    def delete_resources(self, function_name, output_type):
        self.check_function_name_not_exists(function_name)
        
        delete_function_response = self.delete_lambda_function(function_name)
        
        self.parse_delete_function_response(function_name, delete_function_response, output_type)
        
        delete_log_response = self.delete_cloudwatch_log_group(function_name)
        
        self.parse_delete_log_response(function_name, delete_log_response, output_type)
    
    def launch_async_event(self, aws_lambda, s3_file):
        aws_lambda.set_asynchronous_call_parameters()
        return self.launch_s3_event(aws_lambda, s3_file)        
   
    def launch_request_response_event(self, aws_lambda, s3_file):
        aws_lambda.set_request_response_call_parameters()
        return self.launch_s3_event(aws_lambda, s3_file)            

    def preheat_function(self, aws_lambda):
        aws_lambda.set_request_response_call_parameters()
        return self.invoke_lambda_function(aws_lambda)
                
    def launch_s3_event(self, aws_lambda, s3_file):
        aws_lambda.set_event_source_file_name(s3_file)
        aws_lambda.set_payload(aws_lambda.event)
        logging.info("Sending event for file '%s'" % s3_file)
        self.invoke_lambda_function(aws_lambda)   
        