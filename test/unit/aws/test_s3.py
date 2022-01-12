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
import tempfile
import os
import os.path
from mock import MagicMock
from mock import patch, call
from botocore.exceptions import ClientError

sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.s3 import S3


class TestS3(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def test_init(self):
        s3 = S3({})
        self.assertEqual(type(s3.client.client).__name__, "S3")

    def _init_mocks(self, call_list):
        session = MagicMock(['client'])
        client = MagicMock(call_list)
        session.client.return_value = client
        return session   

    @patch('boto3.Session')
    def test_create_bucket(self, boto_session):
        boto_session.return_value = self._init_mocks(['get_bucket_location', 'create_bucket'])
        s3 = S3({})
        s3.client.client.get_bucket_location.side_effect = ClientError({'Error': {'Code': 'NoSuchBucket'}}, 'op')
        s3.client.client.create_bucket.return_value = {}
        s3.create_bucket('bname')
        self.assertEqual(s3.client.client.create_bucket.call_args_list[0], call(ACL='private', Bucket='bname'))

    @patch('boto3.Session')
    def test_upload_file(self, boto_session):
        boto_session.return_value = self._init_mocks(['put_object'])
        s3 = S3({})
        s3.client.client.put_object.return_value = {}
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        tmpfile.write(b'Hello world!')
        tmpfile.close()
        s3.upload_file('bname', file_path=tmpfile.name)
        os.unlink(tmpfile.name)
        self.assertEqual(s3.client.client.put_object.call_args_list[0],
                         call(Bucket='bname', Key=os.path.basename(tmpfile.name), Body=b'Hello world!'))

    @patch('boto3.Session')
    def test_get_bucket_file_list(self, boto_session):
        boto_session.return_value = self._init_mocks(['get_bucket_location', 'list_objects_v2'])
        s3 = S3({})
        s3.client.client.list_objects_v2.return_value = {'IsTruncated': False, 'Contents': [{'Key': 'key1'}]}
        self.assertEqual(s3.get_bucket_file_list({'path': '/'}), ['key1'])

    @patch('boto3.Session')
    def test_set_input_bucket_notification(self, boto_session):
        boto_session.return_value = self._init_mocks(['put_bucket_notification_configuration',
                                                      'get_bucket_notification_configuration'])
        s3 = S3({'lambda': {'arn': 'arn'}})
        s3.client.client.get_bucket_notification_configuration.return_value = {'LambdaFunctionConfigurations': []}
        s3.client.client.put_bucket_notification_configuration.return_value = {}
        s3.set_input_bucket_notification('bucket','folders')
        expected_res = call(Bucket='bucket',
                            NotificationConfiguration={'LambdaFunctionConfigurations': [{'LambdaFunctionArn': 'arn',
                                                                                         'Events': ['s3:ObjectCreated:*'],
                                                                                         'Filter': {'Key': {'FilterRules': [{'Name': 'prefix',
                                                                                                                             'Value': 'folders/'}]}}}]})
        self.assertEqual(s3.client.client.put_bucket_notification_configuration.call_args_list[0], expected_res)

    @patch('boto3.Session')
    def test_delete_bucket_notification(self, boto_session):
        boto_session.return_value = self._init_mocks(['put_bucket_notification_configuration',
                                                      'get_bucket_notification_configuration'])
        s3 = S3({'lambda': {'arn': 'arn'}})
        s3.client.client.get_bucket_notification_configuration.return_value = {'LambdaFunctionConfigurations': []}
        s3.client.client.put_bucket_notification_configuration.return_value = {}
        s3.delete_bucket_notification('bucket')
        expected_res = call(Bucket='bucket', NotificationConfiguration={'LambdaFunctionConfigurations': []})
        self.assertEqual(s3.client.client.put_bucket_notification_configuration.call_args_list[0], expected_res)

    @patch('boto3.Session')
    def test_create_bucket_and_folders(self, boto_session):
        boto_session.return_value = self._init_mocks(['get_bucket_location', 'create_bucket', 'put_object', 'get_object'])
        s3 = S3({})
        s3.client.client.get_bucket_location.side_effect = ClientError({'Error': {'Code': 'NoSuchBucket'}}, 'op')
        s3.client.client.create_bucket.return_value = {}
        s3.client.client.put_object.return_value = {}
        s3.client.client.get_object.return_value = {}
        self.assertEqual(s3.create_bucket_and_folders('storage/path'), ('storage', 'path'))

    @patch('boto3.Session')
    def test_download_file(self, boto_session):
        boto_session.return_value = self._init_mocks(['download_fileobj'])
        s3 = S3({})
        s3.client.client.download_fileobj.return_value = {}
        s3.download_file('bucket', 'key', 'path')
        self.assertEqual(s3.client.client.download_fileobj.call_args_list[0][1]['Bucket'], 'bucket')
        self.assertEqual(s3.client.client.download_fileobj.call_args_list[0][1]['Key'], 'key')
        self.assertIn('Fileobj', s3.client.client.download_fileobj.call_args_list[0][1])
        os.unlink('path')
