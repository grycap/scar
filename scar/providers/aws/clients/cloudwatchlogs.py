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

from botocore.exceptions import ClientError
from scar.providers.aws.clients.boto import BotoClient
import scar.exceptions as excp
import scar.logger as logger

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
