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
from typing import Tuple, Dict
from scar.providers.aws import GenericClient
import scar.exceptions as excp
import scar.logger as logger
from scar.utils import FileUtils


def _get_bucket_and_folders(storage_path: str) -> Tuple:
    output_bucket = storage_path
    output_folders = ""
    output_path = storage_path.split("/", 1)
    if len(output_path) > 1:
        # There are folders defined
        output_bucket = output_path[0]
        output_folders = output_path[1]
    return (output_bucket, output_folders)


class S3(GenericClient):

    def __init__(self, function_info):
        super().__init__()
        self.aws = function_info

    @excp.exception(logger)
    def create_bucket(self, bucket_name) -> None:
        if not self.client.find_bucket(bucket_name):
            self.client.create_bucket(bucket_name)

    @excp.exception(logger)
    def add_bucket_folder(self, folders: str) -> None:
        self.upload_file(folder_name=folders)

    def create_bucket_and_folders(self, storage_path: str) -> str:
        bucket, folders = _get_bucket_and_folders(storage_path)
        self.create_bucket(bucket)
        if folders:
            self.add_bucket_folder(folders)
        return bucket

    def set_input_bucket_notification(self, bucket_name: str) -> None:
        # First check that the function doesn't have other configurations
        bucket_conf = self.client.get_notification_configuration(bucket_name)
        trigger_conf = self.get_trigger_configuration(bucket_name)
        lambda_conf = [trigger_conf]
        if "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            lambda_conf.append(trigger_conf)
        notification = {"LambdaFunctionConfigurations": lambda_conf}
        self.client.put_notification_configuration(bucket_name, notification)

    def delete_bucket_notification(self, bucket_name, function_arn):
        bucket_conf = self.client.get_notification_configuration(bucket_name)
        if bucket_conf and "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            filter_conf = [x for x in lambda_conf if x['LambdaFunctionArn'] != function_arn]
            notification = { "LambdaFunctionConfigurations": filter_conf }
            self.client.put_notification_configuration(bucket_name, notification)
            logger.info("Bucket notifications successfully deleted")

    def get_trigger_configuration(self, bucket_name: str) -> Dict:
        return  {"LambdaFunctionArn": self.aws.get('lambda').get('arn'),
                 "Events": [ "s3:ObjectCreated:*" ],
                 "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": bucket_name }]}}
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
    def upload_file(self, bucket: str, folder_name: str =None, file_path: str =None, file_key: str =None) -> None:
        kwargs = {'Bucket' : bucket}
        kwargs['Key'] = self.get_file_key(folder_name, file_path, file_key)
        if file_path:
            try:
                kwargs['Body'] = FileUtils.read_file(file_path, 'rb')
            except FileNotFoundError:
                raise excp.UploadFileNotFoundError(file_path=file_path)
        if folder_name and not file_path:
            logger.info(f"Folder '{kwargs['Key']}' created in bucket '{kwargs['Bucket']}'")
        else:
            logger.info(f"Uploading file '{file_path}' to bucket '{kwargs['Bucket']}' with key '{kwargs['Key']}'")
        self.client.upload_file(**kwargs)

    @excp.exception(logger)
    def get_bucket_file_list(self):
        bucket_name = self.aws.s3.input_bucket
        if self.client.find_bucket(bucket_name):
            kwargs = {"Bucket" : bucket_name}
            if hasattr(self.aws.s3, "input_folder") and self.aws.s3.input_folder:
                kwargs["Prefix"] = self.aws.s3.input_folder
            return self.client.list_files(**kwargs)
        else:
            raise excp.BucketNotFoundError(bucket_name=bucket_name)

    def get_s3_event(self, s3_file_key):
        return {"Records": [{"eventSource": "aws:s3",
                             "s3" : {"bucket" : {"name": self.aws.s3.input_bucket,
                                                 "arn": f'arn:aws:s3:::{self.aws.s3.input_bucket}'},
                                     "object" : {"key": s3_file_key}}}]}

    def get_s3_event_list(self, s3_file_keys):
        return [self.get_s3_event(s3_key) for s3_key in s3_file_keys]

    def download_file(self, bucket_name, file_key, file_path):
        kwargs = {'Bucket' : bucket_name, 'Key' : file_key}
        logger.info("Downloading file '{0}' from bucket '{1}' in path '{2}'".format(file_key, bucket_name, file_path))
        with open(file_path, 'wb') as file:
            kwargs['Fileobj'] = file
            self.client.download_file(**kwargs)
