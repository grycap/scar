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
"""Module with classes and methods to manage the
CloudWatch Log functionalities at high level."""

from typing import List
from botocore.exceptions import ClientError
from scar.providers.aws import GenericClient
import scar.logger as logger


def _parse_events_in_message(log_events: List) -> str:
    data = [(event.get('message', ''), event.get('timestamp', '')) for event in log_events]
    sorted_data = sorted(data, key=lambda time: time[1])
    return "".join([sdata[0] for sdata in sorted_data])


class CloudWatchLogs(GenericClient):
    """Manages the AWS CloudWatch Logs functionality"""

    def get_log_group_name(self):
        """Returns the log group matching the
        current lambda function being parsed."""
        return f'/aws/lambda/{self.aws.lambdaf.name}'

    def _get_log_group_name_arg(self):
        return {'logGroupName' : self.get_log_group_name()}

    def create_log_group(self):
        """Creates a CloudWatch Log Group."""
        creation_args = self._get_log_group_name_arg()
        creation_args['tags'] = self.aws.tags
        response = self.client.create_log_group(**creation_args)
        # Set retention policy into the log group
        retention_args = self._get_log_group_name_arg()
        retention_args['retentionInDays'] = self.aws.cloudwatch.log_retention_policy_in_days
        self.client.set_log_retention_policy(**retention_args)
        return response

    def delete_log_group(self):
        """Deletes a CloudWatch Log Group."""
        return self.client.delete_log_group(**self._get_log_group_name_arg())

    def get_aws_log(self):
        """Returns Lambda logs for an specific lambda function."""
        function_logs = ""
        try:
            kwargs = self._get_log_group_name_arg()
            if hasattr(self.aws.cloudwatch, "log_stream_name"):
                kwargs["logStreamNames"] = [self.aws.cloudwatch.log_stream_name]
            function_logs = _parse_events_in_message(self.client.get_log_events(**kwargs))
            if hasattr(self.aws.cloudwatch, "request_id") and self.aws.cloudwatch.request_id:
                function_logs = self._parse_logs_with_requestid(function_logs)
        except ClientError as cerr:
            logger.warning("Error getting the function logs: %s" % cerr)
        return function_logs

    def get_batch_job_log(self, jobs_info):
        """Returns Batch logs for an specific job."""
        batch_logs = ""
        if jobs_info:
            job = jobs_info[0]
            batch_logs += f"Batch job status: {job.get('status', '')}\n"
            kwargs = {'logGroupName': "/aws/batch/job"}
            if job.get("status", "") == "SUCCEEDED":
                kwargs['logStreamNames'] = [job.get("container", {}).get("logStreamName", "")]
                batch_events = self.client.get_log_events(**kwargs)
                msgs = [event.get('message', '')
                        for response in batch_events
                        for event in response.get("events", {})]
                batch_logs += '\n'.join(msgs)
        return batch_logs

    def _is_end_line(self, line):
        return line.startswith('REPORT') and self.aws.cloudwatch.request_id in line

    def _is_start_line(self, line):
        return line.startswith('START') and self.aws.cloudwatch.request_id in line

    def _parse_logs_with_requestid(self, function_logs):
        parsed_msg = ""
        if function_logs:
            in_req_id_logs = False
            for line in function_logs.split('\n'):
                if self._is_start_line(line):
                    parsed_msg += f'{line}\n'
                    in_req_id_logs = True
                elif self._is_end_line(line):
                    parsed_msg += line
                    break
                elif in_req_id_logs:
                    parsed_msg += f'{line}\n'
        return parsed_msg
