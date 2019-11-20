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

import os
from scar.providers.aws import GenericClient
import scar.exceptions as excp
import scar.logger as logger
from scar.utils import FileUtils
from scar.providers.aws.properties import S3Properties


class S3(GenericClient):

    def __init__(self, aws_properties):
        super().__init__(aws_properties.get('lambda'))
        
        if hasattr(self._aws, 's3'):
            if type(self._aws.s3) is dict:
                self._aws.s3 = S3Properties(self._aws.s3)
            self._initialize_properties()

    def _initialize_properties(self):
        if not hasattr(self._aws.s3, "input_folder"):
            self._aws.s3.input_folder = ''
            if hasattr(self._aws.lambdaf, "name"):
                self._aws.s3.input_folder = "{0}/input/".format(self._aws.lambdaf.name)
        elif not self._aws.s3.input_folder.endswith("/"):
            self._aws.s3.input_folder = "{0}/".format(self._aws.s3.input_folder)

    @excp.exception(logger)
    def create_bucket(self, bucket_name):
        if not self.client.find_bucket(bucket_name):
            self.client.create_bucket(bucket_name)

    def create_output_bucket(self):
        self.create_bucket(self._aws.s3.output_bucket)

    @excp.exception(logger)
    def add_bucket_folder(self):
        if self._aws.s3.input_folder:
            self.upload_file(folder_name=self._aws.s3.input_folder)

    def create_input_bucket(self, create_input_folder=False):
        self.create_bucket(self._aws.s3.input_bucket)
        if create_input_folder:
            self.add_bucket_folder()

    def set_input_bucket_notification(self):
        # First check that the function doesn't have other configurations
        bucket_conf = self.client.get_notification_configuration(self._aws.s3.input_bucket)
        trigger_conf = self.get_trigger_configuration()
        lambda_conf = [trigger_conf]
        if "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            lambda_conf.append(trigger_conf)
        notification = { "LambdaFunctionConfigurations": lambda_conf }
        self.client.put_notification_configuration(self._aws.s3.input_bucket, notification)

    def delete_bucket_notification(self, bucket_name, function_arn):
        bucket_conf = self.client.get_notification_configuration(bucket_name)
        if bucket_conf and "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            filter_conf = [x for x in lambda_conf if x['LambdaFunctionArn'] != function_arn]
            notification = { "LambdaFunctionConfigurations": filter_conf }
            self.client.put_notification_configuration(bucket_name, notification)
            logger.info("Bucket notifications successfully deleted")

    def get_trigger_configuration(self):
        return  {"LambdaFunctionArn": self._aws.lambdaf.arn,
                 "Events": [ "s3:ObjectCreated:*" ],
                 "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": self._aws.s3.input_folder }]}}
                 }

    def get_file_key(self, folder_name=None, file_path=None, file_key=None):
        if file_key:
            return file_key
        file_key = ''
        if file_path:
            file_key = os.path.basename(file_path)
            if folder_name:
                file_key = FileUtils.join_paths(folder_name, file_key)
        elif folder_name:
            file_key = folder_name if folder_name.endswith('/') else '{0}/'.format(folder_name)
        return file_key

    @excp.exception(logger)
    def upload_file(self, folder_name=None, file_path=None, file_key=None):
        kwargs = {'Bucket' : self._aws.s3.input_bucket}
        kwargs['Key'] = self.get_file_key(folder_name, file_path, file_key)
        if file_path:
            try:
                kwargs['Body'] = FileUtils.read_file(file_path, 'rb')
            except FileNotFoundError:
                raise excp.UploadFileNotFoundError(file_path=file_path)
        if folder_name and not file_path:
            logger.info("Folder '{0}' created in bucket '{1}'".format(kwargs['Key'], kwargs['Bucket']))
        else:
            logger.info("Uploading file '{0}' to bucket '{1}' with key '{2}'".format(file_path, kwargs['Bucket'], kwargs['Key']))
        self.client.upload_file(**kwargs)

    @excp.exception(logger)
    def get_bucket_file_list(self):
        bucket_name = self._aws.s3.input_bucket
        if self.client.find_bucket(bucket_name):
            kwargs = {"Bucket" : bucket_name}
            if hasattr(self._aws.s3, "input_folder") and self._aws.s3.input_folder:
                kwargs["Prefix"] = self._aws.s3.input_folder
            return self.client.list_files(**kwargs)
        else:
            raise excp.BucketNotFoundError(bucket_name=bucket_name)

    def get_s3_event(self, s3_file_key):
        return {"Records": [{"eventSource": "_aws:s3",
                             "s3" : {"bucket" : {"name": self._aws.s3.input_bucket,
                                                 "arn": f'arn:_aws:s3:::{self._aws.s3.input_bucket}'},
                                     "object" : {"key": s3_file_key}}}]}

    def get_s3_event_list(self, s3_file_keys):
        return [self.get_s3_event(s3_key) for s3_key in s3_file_keys]

    def download_file(self, bucket_name, file_key, file_path):
        kwargs = {'Bucket' : bucket_name, 'Key' : file_key}
        logger.info("Downloading file '{0}' from bucket '{1}' in path '{2}'".format(file_key, bucket_name, file_path))
        with open(file_path, 'wb') as file:
            kwargs['Fileobj'] = file
            self.client.download_file(**kwargs)
