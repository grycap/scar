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
import os
from mock import MagicMock
from mock import patch

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.iam import IAM


class TestIAM(unittest.TestCase):

    def __init__(self, *args):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        ecr = IAM({})
        self.assertEqual(type(ecr.client.client).__name__, "IAM")

    @patch('boto3.Session')
    def test_get_user_name_or_id(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['get_user'])
        session.client.return_value = client
        boto_session.return_value = session
        iam = IAM({})
        iam.client.client.get_user.return_value = {'UserName': 'name', 'User': {'UserId': 'id'}}
        self.assertEqual(iam.get_user_name_or_id(), 'name')
