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
from typing import Tuple, Dict, List
from scar.providers.aws import GenericClient
import scar.exceptions as excp
import scar.logger as logger
from scar.utils import FileUtils


def get_bucket_and_folders(storage_path: str) -> Tuple:
    output_bucket = storage_path
    output_folders = ""
    output_path = storage_path.split("/", 1)
    if len(output_path) > 1:
        # There are folders defined
        output_bucket = output_path[0]
        output_folders = output_path[1]
    return (output_bucket, output_folders)


class S3(GenericClient):

    def __init__(self, resources_info):
        super().__init__(resources_info.get('s3'))
        self.resources_info = resources_info

    @excp.exception(logger)
    def create_bucket(self, bucket_name) -> None:
        if not self.client.find_bucket(bucket_name):
            self.client.create_bucket(bucket_name)

    @excp.exception(logger)
    def add_bucket_folder(self, bucket: str, folders: str) -> None:
        if not self.client.is_folder(bucket, folders):
            self.upload_file(bucket, folder_name=folders)

    def create_bucket_and_folders(self, storage_path: str) -> Tuple:
        bucket, folders = get_bucket_and_folders(storage_path)
        self.create_bucket(bucket)
        if folders:
            self.add_bucket_folder(bucket, folders)
        return bucket, folders

    def set_input_bucket_notification(self, bucket_name: str, folders: str) -> None:
        # First check that the function doesn't have other configurations
        bucket_conf = self.client.get_notification_configuration(bucket_name)
        trigger_conf = self.get_trigger_configuration(folders)
        lambda_conf = [trigger_conf]
        if "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            lambda_conf.append(trigger_conf)
        notification = {"LambdaFunctionConfigurations": lambda_conf}
        self.client.put_notification_configuration(bucket_name, notification)

    def delete_bucket_notification(self, bucket_name):
        bucket_conf = self.client.get_notification_configuration(bucket_name)
        if bucket_conf and "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            filter_conf = [x for x in lambda_conf if x['LambdaFunctionArn'] != self.resources_info.get('lambda').get('arn')]
            notification = {"LambdaFunctionConfigurations": filter_conf}
            self.client.put_notification_configuration(bucket_name, notification)
            logger.info("Bucket notifications successfully deleted.")

    def get_trigger_configuration(self, folders: str) -> Dict:
        conf = {"LambdaFunctionArn": self.resources_info.get('lambda').get('arn'),
                "Events": ["s3:ObjectCreated:*"]}
        if folders != '':
            conf['Filter'] = {"Key": {"FilterRules": [{"Name": "prefix", "Value": f'{folders}/'}]}}
        return conf

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
    def upload_file(self, bucket: str, folder_name: str=None, file_path: str=None, file_key: str=None) -> None:
        kwargs = {'Bucket': bucket}
        kwargs['Key'] = self.get_file_key(folder_name, file_path, file_key)
        if file_path:
            try:
                kwargs['Body'] = FileUtils.read_file(file_path, 'rb')
            except FileNotFoundError:
                raise excp.UploadFileNotFoundError(file_path=file_path)
        if folder_name and not file_path:
            kwargs['ContentType'] = 'application/x-directory'
            logger.info(f"Folder '{kwargs['Key']}' created in bucket '{kwargs['Bucket']}'.")
        else:
            logger.info(f"Uploading file '{file_path}' to bucket '{kwargs['Bucket']}' with key '{kwargs['Key']}'.")
        self.client.upload_file(**kwargs)

    @excp.exception(logger)
    def get_bucket_file_list(self, storage: Dict=None):
        files = []
        if storage:
            files = self._list_storage_files(storage)
        else:
            for storage_info in self.resources_info.get('lambda').get('input'):
                if storage_info.get('storage_provider') == 's3':
                    files.extend(self._list_storage_files(storage_info))
        return files

    def _list_storage_files(self, storage: Dict) -> List:
        files = []
        bucket_name, folder_path = get_bucket_and_folders(storage.get('path'))
        if self.client.find_bucket(bucket_name):
            kwargs = {"Bucket" : bucket_name}
            if folder_path:
                kwargs["Prefix"] = folder_path
            files = (self.client.list_files(**kwargs))
        else:
            raise excp.BucketNotFoundError(bucket_name=bucket_name)
        return files

    def get_s3_event(self, bucket_name, file_key):
        event = self.resources_info.get("s3").get("event")
        event['Records'][0]['s3']['bucket']['name'] = bucket_name
        event['Records'][0]['s3']['bucket']['arn'] = event['Records'][0]['s3']['bucket']['arn'].format(bucket_name=bucket_name)
        event['Records'][0]['s3']['object']['key'] = file_key
        return event

    def get_s3_event_list(self, bucket_name, file_keys):
        return [self.get_s3_event(bucket_name, file_key) for file_key in file_keys]

    def download_file(self, bucket_name, file_key, file_path):
        kwargs = {'Bucket' : bucket_name, 'Key' : file_key}
        logger.info(f"Downloading file '{file_key}' from bucket '{bucket_name}' in path '{file_path}'.")
        with open(file_path, 'wb') as file:
            kwargs['Fileobj'] = file
            self.client.download_file(**kwargs)
