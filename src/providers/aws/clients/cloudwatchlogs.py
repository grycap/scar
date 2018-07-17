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
import src.exceptions as excp

class CloudWatchLogsClient(BotoClient):
    '''A low-level client representing Amazon CloudWatch Logs.
    https://boto3.readthedocs.io/en/latest/reference/services/logs.html'''
    
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'logs'    
    
    @excp.exception(logger)    
    def get_log_events(self, **kwargs):
        '''
        Lists log events from the specified log group.
        https://boto3.readthedocs.io/en/latest/reference/services/logs.html#CloudWatchLogs.Client.filter_log_events
        '''
        logs = []
        response = self.client.filter_log_events(**kwargs)
        logs.append(response)
        while ('nextToken' in response) and (response['nextToken']):
            kwargs['nextToken'] = response['nextToken']
            response = self.client.filter_log_events(**kwargs)
            logs.append(response)
        return logs
            
    @excp.exception(logger)            
    def create_log_group(self, **kwargs):
        '''
        Creates a log group with the specified name.
        https://boto3.readthedocs.io/en/latest/reference/services/logs.html#CloudWatchLogs.Client.create_log_group
        '''         
        try:
            return self.client.create_log_group(**kwargs)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                raise excp.ExistentLogGroupWarning(logGroupName=kwargs['logGroupName'])
            else:
                raise
    
    @excp.exception(logger)
    def set_log_retention_policy(self, **kwargs):
        '''
        Sets the retention of the specified log group.
        https://boto3.readthedocs.io/en/latest/reference/services/logs.html#CloudWatchLogs.Client.put_retention_policy
        '''         
        return self.client.put_retention_policy(**kwargs)
            
    @excp.exception(logger)
    def delete_log_group(self, **kwargs):
        '''
        Deletes the specified log group and permanently deletes all the archived log events associated with the log group.
        https://boto3.readthedocs.io/en/latest/reference/services/logs.html#CloudWatchLogs.Client.delete_log_group
        '''         
        try:
            return self.client.delete_log_group(**kwargs)
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                raise excp.NotExistentLogGroupWarning(**kwargs)
            else:
                raise
