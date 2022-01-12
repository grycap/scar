#! /usr/bin/python

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
import unittest
import sys
from mock import MagicMock
from mock import patch

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.cloudwatchlogs import CloudWatchLogs


class TestCloudWatchLogs(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        cwl = CloudWatchLogs({})
        self.assertEqual(type(cwl.client.client).__name__, "CloudWatchLogs")

    def test_get_log_group_name(self):
        cwl = CloudWatchLogs({'lambda': {'name': 'fname'}})
        self.assertEqual(cwl.get_log_group_name(), '/aws/lambda/fname')

    @patch('boto3.Session')
    def test_create_log_group(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['create_log_group', 'put_retention_policy'])
        session.client.return_value = client
        boto_session.return_value = session
        cwl = CloudWatchLogs({'lambda': {'name': 'fname', 'tags': {'createdby': 'scar'}},
                              'cloudwatch': {'log_retention_policy_in_days': 1}})
        cwl.client.client.create_log_group.return_value = "resp"
        self.assertEqual(cwl.create_log_group(), "resp")
        res = {'logGroupName': '/aws/lambda/fname', 'tags': {'createdby': 'scar'}}
        self.assertEqual(cwl.client.client.create_log_group.call_args_list[0][1], res)

    @patch('boto3.Session')
    def test_get_aws_logs(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['filter_log_events', 'describe_jobs'])
        session.client.return_value = client
        boto_session.return_value = session
        cwl = CloudWatchLogs({'lambda': {'name': 'fname'},
                              'cloudwatch': {'log_stream_name': 'stream',
                                             'request_id': 'reqid'}})
        cwl.client.client.filter_log_events.return_value = {'events': [{'message': 'mess', 'timestamp': 'times'}]}
        cwl.client.client.describe_jobs.return_value = {'jobs': [{'status': 'SUCCEEDED'}]}
        self.assertEqual(cwl.get_aws_logs(), "Batch job status: SUCCEEDED\nmess")
