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
"""Module with the class necessary to manage the
S3 buckets and folders creation, deletion and configuration."""

from typing import Dict, List
from botocore.exceptions import ClientError
from scar.providers.aws.clients import BotoClient
from scar.exceptions import exception
import scar.logger as logger


class S3Client(BotoClient):
    """A low-level client representing Amazon Simple Storage Service (S3Client).
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/services/s3.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 's3'
    _DEFAULT_ACL = 'private'

    @exception(logger)
    def create_bucket(self, bucket_name: str) -> Dict:
        """Creates a new S3 bucket."""
        return self.client.create_bucket(ACL=self._DEFAULT_ACL, Bucket=bucket_name)

    @exception(logger)
    def find_bucket(self, bucket_name: str) -> bool:
        """Checks bucket existence."""
        try:
            # If this call works the bucket exists
            self.client.get_bucket_location(Bucket=bucket_name)
            return True
        except ClientError as cerr:
            # Function not found
            if cerr.response['Error']['Code'] == 'NoSuchBucket':
                return False
            raise cerr

    @exception(logger)
    def put_notification_configuration(self, bucket_name: str, notification: Dict) -> Dict:
        """Enables notifications of specified events for a bucket."""
        kwargs = {"Bucket": bucket_name,
                  "NotificationConfiguration": notification}
        return self.client.put_bucket_notification_configuration(**kwargs)

    @exception(logger)
    def get_notification_configuration(self, bucket_name: str) -> Dict:
        """Returns the notification configuration of a bucket."""
        return self.client.get_bucket_notification_configuration(Bucket=bucket_name)

    @exception(logger)
    def upload_file(self, **kwargs: Dict) -> Dict:
        """Adds an object to a bucket."""
        return self.client.put_object(**kwargs)

    @exception(logger)
    def download_file(self, **kwargs: Dict) -> Dict:
        """Download an object from S3 to a file-like object."""
        return self.client.download_fileobj(**kwargs)

    @exception(logger)
    def is_folder(self, bucket: str, folder: str) -> bool:
        """Checks if a file with the key specified exists."""
        try:
            kwargs = {'Bucket' : bucket,
                      'Key' : folder if folder.endswith('/') else folder + '/'}
            # If this call works the folder exist
            self.client.get_object(**kwargs)
            return True
        except ClientError as cerr:
            # Folder not found
            if cerr.response['Error']['Code'] == 'NoSuchKey':
                return False
            raise cerr

    @exception(logger)
    def list_files(self, **kwargs: Dict) -> List:
        """Returns the keys of all the objects in a bucket.
        Excludes the S3 'folders', i.e. files with key ending in '/'."""
        file_list = []
        response = self.client.list_objects_v2(**kwargs)
        if 'Contents' in response:
            # Don't append S3 'folders'
            file_list.extend([file['Key'] for file in response['Contents']
                              if not file['Key'].endswith('/')])
        # Retrieve all the remaining file keys recursively
        if response['IsTruncated']:
            kwargs['ContinuationToken'] = response['NextContinuationToken']
            file_list.extend(self.list_files(**kwargs))
        return file_list
