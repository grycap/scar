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
"""Module with the class necessary to manage the
Cloudwatch Logs creation, deletion and configuration."""

from typing import Dict, List
from botocore.exceptions import ClientError
from scar.providers.aws.clients import BotoClient
from scar.exceptions import exception, ExistentLogGroupWarning, NotExistentLogGroupWarning
import scar.logger as logger


class CloudWatchLogsClient(BotoClient):
    """A low-level client representing Amazon CloudWatch Logs.
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/services/logs.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'logs'

    @exception(logger)
    def get_log_events(self, **kwargs: Dict) -> List:
        """Lists log events from the specified log group."""
        log_events = []
        logs_info = self.client.filter_log_events(**kwargs)
        log_events.extend(logs_info.get('events', []))
        if 'nextToken' in logs_info:
            kwargs['nextToken'] = logs_info['nextToken']
            log_events.extend(self.get_log_events(**kwargs))
        return log_events

    @exception(logger)
    def create_log_group(self, **kwargs: Dict) -> Dict:
        """Creates a log group with the specified name."""
        try:
            return self.client.create_log_group(**kwargs)
        except ClientError as cerr:
            if cerr.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                raise ExistentLogGroupWarning(logGroupName=kwargs['logGroupName'])
            raise cerr

    @exception(logger)
    def set_log_retention_policy(self, **kwargs: Dict) -> Dict:
        """Sets the retention of the specified log group."""
        return self.client.put_retention_policy(**kwargs)

    @exception(logger)
    def delete_log_group(self, log_group_name: str) -> Dict:
        """Deletes the specified log group and permanently deletes
        all the archived log events associated with the log group."""
        try:
            return self.client.delete_log_group(logGroupName=log_group_name)
        except ClientError as cerr:
            if cerr.response['Error']['Code'] == 'ResourceNotFoundException':
                raise NotExistentLogGroupWarning(logGroupName=log_group_name)
            raise cerr
