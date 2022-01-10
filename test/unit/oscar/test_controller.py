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
import tempfile
from mock import MagicMock
from mock import patch

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.oscar.controller import OSCAR

class TestOSCARController(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    @patch('scar.providers.oscar.controller.OSCARClient')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_init(self, load_tmp_config_file, oscar_client):
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        tmpfile.write(b'Hello world!')
        tmpfile.close()
        load_tmp_config_file.return_value = {"functions": {"oscar": [{"my_oscar": {"name": "oname",
                                                                                   "script": tmpfile.name}}]}}
        ocli = MagicMock(['create_service'])
        oscar_client.return_value = ocli

        OSCAR('init')
    
        os.unlink(tmpfile.name)
        res = {'name': 'oname', 'script': 'Hello world!',
               'cluster_id': 'my_oscar', 'storage_providers': {}}
        self.assertEqual(ocli.create_service.call_args_list[0][1], res)

    @patch('scar.providers.oscar.controller.OSCARClient')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_rm(self, load_tmp_config_file, oscar_client):
        load_tmp_config_file.return_value = {"functions": {"oscar": [{"my_oscar": {"name": "oname",
                                                                                   "script": "some.sh"}}]}}
        ocli = MagicMock(['delete_service'])
        oscar_client.return_value = ocli

        OSCAR('rm')

        self.assertEqual(ocli.delete_service.call_args_list[0][0][0], 'oname')

    @patch('scar.providers.oscar.controller.OSCARClient')
    @patch('scar.providers.aws.controller.FileUtils.load_tmp_config_file')
    def test_ls(self, load_tmp_config_file, oscar_client):
        load_tmp_config_file.return_value = {"functions": {"oscar": [{"my_oscar": {"name": "oname",
                                                                                   "script": "some.sh",
                                                                                   "endpoint": "http://some.es",
                                                                                   "auth_user": "user",
                                                                                   "auth_password": "pass",
                                                                                   "ssl_verify": False}}]}}
        ocli = MagicMock(['list_services'])
        ocli.list_services.return_value = [{'name': 'fname', 'memory': '256Mi',
                                            'cpu': '1.0', 'image': 'some/image:tag'}]
        oscar_client.return_value = ocli

        OSCAR('ls')

        self.assertEqual(ocli.list_services.call_count, 1)