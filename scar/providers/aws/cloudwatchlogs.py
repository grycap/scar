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
from scar.providers.aws.botoclientfactory import GenericClient

class CloudWatchLogs(GenericClient):
    
    def __init__(self, aws_properties):
        super().__init__(aws_properties)

    def get_log_group_name(self):
        return '/aws/lambda/{0}'.format(self.aws._lambda.name)
    
    def _get_log_group_name_arg(self):
        return { 'logGroupName' : self.get_log_group_name() }    

    def create_log_group(self):
        creation_args = self._get_log_group_name_arg()
        creation_args['tags'] = self.aws.tags
        response = self.client.create_log_group(**creation_args)
        # Set retention policy into the log group
        retention_args = self._get_log_group_name_arg()
        retention_args['retentionInDays'] = self.aws.cloudwatch.log_retention_policy_in_days
        self.client.set_log_retention_policy(**retention_args)
        return response
      
    def delete_log_group(self):
        return self.client.delete_log_group(**self._get_log_group_name_arg())

    def get_aws_log(self):
        function_logs = ""
        try:
            kwargs = self._get_log_group_name_arg()
            if hasattr(self.aws.cloudwatch, "log_stream_name"):
                kwargs["logStreamNames"] = [self.aws.cloudwatch.log_stream_name]
            response = self.client.get_log_events(**kwargs)
            function_logs = self.sort_events_in_message(response)
            if hasattr(self.aws.cloudwatch, "request_id") and self.aws.cloudwatch.request_id:
                function_logs = self.parse_logs_with_requestid(function_logs)
        except ClientError as ce:
            print ("Error getting the function logs: %s" % ce)
        return function_logs
    
    def get_batch_job_log(self, jobs_info):
        batch_logs = "" 
        batch_logs += "Batch job status: {0}\n".format(jobs_info[0]["status"])
        if jobs_info[0]["status"] == "SUCCEEDED":
            kwargs = {'logGroupName': "/aws/batch/job", 'logStreamNames': [jobs_info[0]["container"]["logStreamName"],]}
            batch_events = self.client.get_log_events(**kwargs)
            batch_logs += '\n'.join([event['message'] for response in batch_events for event in response["events"]])
        return batch_logs

    def sort_events_in_message(self, response):
        sorted_msg = ""
        data = []
        for elem in response:
            for event in elem['events']:
                data.append((event['message'], event['timestamp']))
        sorted_data = sorted(data, key=lambda time: time[1])       
        for sdata in sorted_data:
            sorted_msg += sdata[0]
        return sorted_msg

    def is_end_line(self, line):
        return line.startswith('REPORT') and self.aws.cloudwatch.request_id in line

    def is_start_line(self, line):
        return line.startswith('START') and self.aws.cloudwatch.request_id in line

    def parse_logs_with_requestid(self, function_logs):
        if function_logs:
            parsed_msg = ""
            in_req_id_logs = False
            for line in function_logs.split('\n'):
                if self.is_start_line(line):
                    parsed_msg += '{0}\n'.format(line)
                    in_req_id_logs = True                
                elif self.is_end_line(line):
                    parsed_msg += line
                    break
                elif in_req_id_logs:
                    parsed_msg += '{0}\n'.format(line)
            return parsed_msg
        