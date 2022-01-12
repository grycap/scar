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

from scar.providers.aws.resourcegroups import ResourceGroups


class TestResourceGroups(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        rg = ResourceGroups({})
        self.assertEqual(type(rg.client.client).__name__, "ResourceGroupsTaggingAPI")

    @patch('boto3.Session')
    def test_get_resource_arn_list(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['get_resources'])
        session.client.return_value = client
        boto_session.return_value = session
        rg = ResourceGroups({})
        rg.client.client.get_resources.return_value = {'ResourceTagMappingList': [{'ResourceARN': 'rarn'}]}
        self.assertEqual(rg.get_resource_arn_list('userid'), ['rarn'])
