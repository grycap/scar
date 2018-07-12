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

from botocore.exceptions import ClientError
import src.providers.aws.response as response_parser
from src.providers.aws.clientfactory import GenericClient

class CloudWatchLogs(GenericClient):
    
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
            result = self.client.get_log_events(self.log_group_name, self.log_stream_name)
            data = []
            for response in result:
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

    def is_end_line(self, line):
        return line.startswith('REPORT') and self.request_id in line

    def is_start_line(self, line):
        return line.startswith('START') and self.request_id in line

    def parse_aws_logs(self, logs):
        if logs and self.request_id:
            full_msg = ""
            logging = False
            for line in logs.split('\n'):
                if self.is_start_line(line):
                    full_msg += line + '\n'
                    logging = True                
                elif self.is_end_line(line):
                    full_msg += line + '\n'
                    return full_msg
                elif logging:
                    full_msg += line + '\n'

        