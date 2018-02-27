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

from .aws import AWS
from botocore.exceptions import ClientError
import logging
import utils.functionutils as utils

class CloudWatchLogs(AWS):
    '''A low-level client representing Amazon CloudWatch Logs.
    https://boto3.readthedocs.io/en/latest/reference/services/logs.html'''
    
    def __init__(self, region=None):
        super().__init__('logs', region)
    
    def get_cloudwatch_log_events_by_group_name(self, log_group_name, next_token=None):
        try:
            if next_token: 
                return self.client.filter_log_events(logGroupName=log_group_name,
                                                        nextToken=next_token)
            else:
                return self.client.filter_log_events(logGroupName=log_group_name)                
        except ClientError as ce:
            print("Error getting log events")
            logging.error("Error getting log events for log group '%s': %s" % (log_group_name, ce))
            utils.finish_failed_execution()    
    
    def get_cloudwatch_log_events_by_group_name_and_stream_name(self, log_group_name, log_stream_name):
        try:        
            return self.client.get_log_events(logGroupName=log_group_name,
                                                        logStreamName=log_stream_name,
                                                        startFromHead=True)
        except ClientError as ce:
            print("Error getting log events")
            logging.error("Error getting log events for log group '%s' and log stream name '%s': %s"
                           % (log_group_name, log_stream_name, ce))
            utils.finish_failed_execution()
            
    def create_cloudwatch_log_group(self, aws_lambda):
        try:
            logging.info("Creating cloudwatch log group.")
            return self.client.create_cloudwatch_log_group(logGroupName=aws_lambda.log_group_name,
                                                   tags=aws_lambda.tags)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print("Using existent log group '%s'" % aws_lambda.log_group_name)
                logging.warning("Using existent log group '%s'" % aws_lambda.log_group_name)
                pass
            else:
                logging.error("Error creating log groups: %s" % ce)   
                utils.finish_failed_execution() 
    
    def set_cloudwatch_log_retention_policy(self, aws_lambda):
        try:
            logging.info("Setting log group policy.")
            self.client.put_retention_policy(logGroupName=aws_lambda.log_group_name,
                                           retentionInDays=aws_lambda.log_retention_policy_in_days)
        except ClientError as ce:
            print("Error setting log retention policy")
            logging.error("Error setting log retention policy: %s" % ce)
            
    def delete_cloudwatch_log_group(self, function_name):
        try:
            # Delete the cloudwatch log group
            log_group_name = '/aws/lambda/%s' % function_name
            return self.client.delete_log_group(logGroupName=log_group_name)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                print("Cannot delete log group '%s'. Group not found." % log_group_name)
                logging.warning("Cannot delete log group '%s'. Group not found." % log_group_name)
            else:
                print("Error deleting the cloudwatch log")
                logging.error("Error deleting the cloudwatch log: %s" % ce) 
        