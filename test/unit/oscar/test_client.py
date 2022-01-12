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

from scar.providers.oscar.client import OSCARClient
from scar.exceptions import ServiceCreationError, ServiceDeletionError, ServiceNotFoundError, ListServicesError

class TestOSCARClient(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    @patch('requests.post')
    def test_create_serviced(self, post):
        response = MagicMock(["status_code", "text"])
        response.status_code = 201
        post.return_value = response
        oscar = OSCARClient({"endpoint": "url", "auth_user": "user", "auth_password": "pass", "ssl_verify": False}, "cid")
        oscar.create_service(key="value")
        self.assertEqual(post.call_args_list[0][0][0], "url/system/services")
        self.assertEqual(post.call_args_list[0][1], {'auth': ('user', 'pass'), 'verify': False, 'json': {'key': 'value'}})

        response.status_code = 401
        response.text = "Some error"
        with self.assertRaises(ServiceCreationError) as ex:
            oscar.create_service(name="sname")
        self.assertEqual(
            "Unable to create the service 'sname': Some error",
            str(ex.exception)
        )

    @patch('requests.delete')
    def test_delete_service(self, delete):
        response = MagicMock(["status_code", "text"])
        response.status_code = 204
        delete.return_value = response
        oscar = OSCARClient({"endpoint": "url", "auth_user": "user", "auth_password": "pass", "ssl_verify": False}, "cid")
        oscar.delete_service("sname")
        self.assertEqual(delete.call_args_list[0][0][0], "url/system/services/sname")
        self.assertEqual(delete.call_args_list[0][1], {'auth': ('user', 'pass'), 'verify': False})

        response.status_code = 401
        response.text = "Some error"
        with self.assertRaises(ServiceDeletionError) as ex:
            oscar.delete_service("sname")
        self.assertEqual(
            "Unable to delete the service 'sname': Some error",
            str(ex.exception)
        )

    @patch('requests.get')
    def test_get_service(self, get):
        response = MagicMock(["status_code", "json"])
        response.status_code = 200
        response.json.return_value = {"key": "value"}
        get.return_value = response
        oscar = OSCARClient({"endpoint": "url", "auth_user": "user", "auth_password": "pass", "ssl_verify": False}, "cid")
        self.assertEqual(oscar.get_service("sname"), {"key": "value"})
        self.assertEqual(get.call_args_list[0][0][0], "url/system/services/sname")
        self.assertEqual(get.call_args_list[0][1], {'auth': ('user', 'pass'), 'verify': False})

        response.status_code = 401
        response.text = "Some error"
        with self.assertRaises(ServiceNotFoundError) as ex:
            oscar.get_service("sname"), {"key": "value"}
        self.assertEqual(
            "The service 'sname' does not exist: Some error",
            str(ex.exception)
        )

    @patch('requests.get')
    def test_list_services(self, get):
        response = MagicMock(["status_code", "json"])
        response.status_code = 200
        response.json.return_value = {"key": "value"}
        get.return_value = response
        oscar = OSCARClient({"endpoint": "url", "auth_user": "user", "auth_password": "pass", "ssl_verify": False}, "cid")
        self.assertEqual(oscar.list_services(), {"key": "value"})
        self.assertEqual(get.call_args_list[0][0][0], "url/system/services")
        self.assertEqual(get.call_args_list[0][1], {'auth': ('user', 'pass'), 'verify': False})

        response.status_code = 401
        response.text = "Some error"
        with self.assertRaises(ListServicesError) as ex:
            oscar.list_services(), {"key": "value"}
        self.assertEqual(
            "Unable to list services from OSCAR cluster 'cid': Some error",
            str(ex.exception)
        )
