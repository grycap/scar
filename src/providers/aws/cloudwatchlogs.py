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

    def get_log_group_name(self):
        return '/aws/lambda/{0}'.format(self.aws_properties['lambda']['name'])
    
    def get_log_group_name_arg(self):
        return { 'logGroupName' : self.get_log_group_name() }    

    def create_log_group(self):
        creation_args = self.get_log_group_name_arg()
        creation_args['tags'] = self.aws_properties['tags']
        response = self.client.create_log_group(**creation_args)
        # Set retention policy into the log group
        retention_args = self.get_log_group_name_arg()
        retention_args['retentionInDays'] = self.properties['log_retention_policy_in_days']
        self.client.set_log_retention_policy(**retention_args)
        return response
      
    def delete_log_group(self):
        return self.client.delete_log_group(**self.get_log_group_name_arg())
    ###
    def get_aws_log(self):
        function_logs = ""
        try:
            kwargs = self.get_log_group_name_arg()
            if 'log_stream_name' in self.properties:
                kwargs["logStreamNames"] = [self.properties['log_stream_name']]            
            response = self.client.get_log_events(**kwargs)
            function_logs = self.sort_events_in_message(response)
            if 'request_id' in self.properties and self.properties['request_id']:
                function_logs = self.parse_logs_with_requestid(function_logs)
        except ClientError as ce:
            print ("Error getting the function logs: %s" % ce)
        return function_logs
    ###    
    def get_logs_batch(self,group,streamName):
        kwargs = {'logGroupName':group,'logStreamName':streamName}
        response = self.client.get_log_events_batch(**kwargs)
        return response
    ###

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
        return line.startswith('REPORT') and self.properties['request_id'] in line

    def is_start_line(self, line):
        return line.startswith('START') and self.properties['request_id'] in line

    def parse_logs_with_requestid(self, function_logs):
        if function_logs:
            parsed_msg = ""
            in_reqid_logs = False
            for line in function_logs.split('\n'):
                if self.is_start_line(line):
                    parsed_msg += line + '\n'
                    in_reqid_logs = True                
                elif self.is_end_line(line):
                    parsed_msg += line
                    break
                elif in_reqid_logs:
                    parsed_msg += line + '\n'
            return parsed_msg
        