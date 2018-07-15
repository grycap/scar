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
from src.providers.aws.botoclientfactory import GenericClient

class CloudWatchLogs(GenericClient):
    
    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.properties = self.aws_properties['cloudwatch']
        self.properties['log_group_name'] = '/aws/lambda/{0}'.format(aws_properties['lambda']['name'])

    def update_log_group_name(self):
        self.properties['log_group_name'] = '/aws/lambda/{0}'.format(self.aws_properties['lambda']['name'])

    def get_basic_args(self):
        return { 'logGroupName' : self.properties['log_group_name'] }

    def create_log_group(self):
        creation_args = self.get_basic_args()
        creation_args['tags'] = self.aws_properties['tags']
        response = self.client.create_log_group(**creation_args)
        # Set retention policy into the log group
        retention_args = self.get_basic_args()
        retention_args['retentionInDays'] = self.aws_properties['cloudwatch']['log_retention_policy_in_days']
        self.client.set_log_retention_policy(**retention_args)
        return response
      
    def delete_log_group(self):
        self.update_log_group_name()
        return self.client.delete_log_group(self.properties['log_group_name'])
      
    def get_aws_log(self):
        function_log = ""
        try:
            full_msg = ""
            kwargs = {"logGroupName" : self.properties['log_group_name']}
            if 'log_stream_name' in self.properties:
                kwargs["logStreamNames"] = [self.properties['log_stream_name']]            
            result = self.client.get_log_events(**kwargs)
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

        