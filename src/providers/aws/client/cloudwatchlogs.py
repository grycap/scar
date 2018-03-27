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
import src.providers.aws.response as response_parser
import src.utils as utils

class CloudWatchLogs():
    
    @utils.lazy_property
    def client(self):
        client = CloudWatchLogsClient()
        return client

    def __init__(self, aws_lambda):
        # Get all the log related attributes
        self.log_group_name = aws_lambda.get_property("log_group_name")
        self.tags = aws_lambda.get_property("tags")
        self.output_type = aws_lambda.get_property("output")
        self.log_retention_policy_in_days = aws_lambda.get_property("cloudwatch", "log_retention_policy_in_days")
        self.log_stream_name = aws_lambda.get_property("log_stream_name")
        self.request_id = aws_lambda.get_property("request_id")

    def create_log_group(self):
        # lambda_validator.validate_log_creation_values(self.aws_lambda)
        response = self.client.create_log_group(self.log_group_name, self.tags)
        response_parser.parse_log_group_creation_response(response,
                                                          self.log_group_name,
                                                          self.output_type)
        # Set retention policy into the log group
        self.client.set_log_retention_policy(self.log_group_name,
                                             self.log_retention_policy_in_days)
      
    def set_log_group_name(self, function_name=None):
        self.log_group_name = '/aws/lambda/' + function_name
      
    def delete_log_group(self, func_name=None):
        if func_name:
            self.set_log_group_name(func_name)
        cw_response = self.client.delete_log_group(self.log_group_name)
        response_parser.parse_delete_log_response(cw_response, self.log_group_name, self.output_type)      
      
    def get_aws_log(self):
        function_log = ""
        try:
            full_msg = ""
            if self.log_stream_name:
                response = self.client.get_log_events_by_group_name_and_stream_name(self.log_group_name,
                                                                                    self.log_stream_name)
                for event in response['events']:
                    full_msg += event['message']
            else:
                response = self.client.get_log_events_by_group_name(self.log_group_name)
                data = []
                for event in response['events']:
                    data.append((event['message'], event['timestamp']))
                while(('nextToken' in response) and response['nextToken']):
                    response = self.client.get_log_events_by_group_name(self.log_group_name, response['nextToken'])
                    for event in response['events']:
                        data.append((event['message'], event['timestamp']))
                sorted_data = sorted(data, key=lambda time: time[1])
                for sdata in sorted_data:
                    full_msg += sdata[0]
            response['completeMessage'] = full_msg
            if self.request_id:
                function_log = self.parse_aws_logs(full_msg)
            else:
                function_log = full_msg
        except ClientError as ce:
            print ("Error getting the function logs: %s" % ce)
              
        return function_log

    def parse_aws_logs(self, logs):
        if (logs is None) or (self.request_id is None):
            return None
        full_msg = ""
        logging = False
        lines = logs.split('\n')
        for line in lines:
            if line.startswith('REPORT') and self.request_id in line:
                full_msg += line + '\n'
                return full_msg
            if logging:
                full_msg += line + '\n'
            if line.startswith('START') and self.request_id in line:
                full_msg += line + '\n'
                logging = True

class CloudWatchLogsClient(BotoClient):
    '''A low-level client representing Amazon CloudWatch Logs.
    https://boto3.readthedocs.io/en/latest/reference/services/logs.html'''
    
    def __init__(self, region=None):
        super().__init__('logs', region)
    
    def get_log_events_by_group_name(self, log_group_name, next_token=None):
        try:
            if next_token: 
                return self.get_client().filter_log_events(logGroupName=log_group_name,
                                                        nextToken=next_token)
            else:
                return self.get_client().filter_log_events(logGroupName=log_group_name)                
        except ClientError as ce:
            logger.error("Error getting log events for log group '%s': %s" % (log_group_name, ce))
            utils.finish_failed_execution()    
    
    def get_log_events_by_group_name_and_stream_name(self, log_group_name, log_stream_name):
        try:        
            return self.get_client().get_log_events(logGroupName=log_group_name,
                                                        logStreamName=log_stream_name,
                                                        startFromHead=True)
        except ClientError as ce:
            logger.error("Error getting log events for log group '%s' and log stream name '%s': %s"
                           % (log_group_name, log_stream_name, ce))
            utils.finish_failed_execution()
            
    def create_log_group(self, log_group_name, tags):
        try:
            logger.info("Creating cloudwatch log group.")
            return self.get_client().create_log_group(logGroupName=log_group_name, tags=tags)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                logger.warning("Using existent log group '%s'" % log_group_name)
                pass
            else:
                logger.error("Error creating log groups.",
                             "Error creating log groups: %s" % ce)   
                utils.finish_failed_execution() 
    
    def set_log_retention_policy(self, log_group_name, log_retention_policy_in_days):
        try:
            logger.info("Setting log group policy.")
            self.get_client().put_retention_policy(logGroupName=log_group_name,
                                                   retentionInDays=log_retention_policy_in_days)
        except ClientError as ce:
            logger.error("Error setting log retention policy", 
                         "Error setting log retention policy: %s" % ce)
            
    def delete_log_group(self, log_group_name):
        try:
            # Delete the cloudwatch log group
            return self.get_client().delete_log_group(logGroupName=log_group_name)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning("Cannot delete log group '%s'. Group not found." % log_group_name)
            else:
                logger.error("Error deleting the cloudwatch log",
                             "Error deleting the cloudwatch log: %s" % ce)
                
        