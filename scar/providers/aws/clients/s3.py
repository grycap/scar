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

from botocore.exceptions import ClientError
from scar.providers.aws.clients.boto import BotoClient
import scar.exceptions as excp
import scar.logger as logger

class S3Client(BotoClient):
    '''A low-level client representing Amazon Simple Storage Service (S3Client).
    https://boto3.readthedocs.io/en/latest/reference/services/s3.html'''
    
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 's3'    
    
    @excp.exception(logger)    
    def create_bucket(self, bucket_name):
        '''Creates a new S3 bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.ServiceResource.create_bucket'''        
        self.client.create_bucket(ACL='private', Bucket=bucket_name)
    
    @excp.exception(logger)
    def find_bucket(self, bucket_name):
        '''Checks bucket existence.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.get_bucket_location'''         
        try:
            # If this call works the bucket exists
            self.client.get_bucket_location(Bucket=bucket_name)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'NoSuchBucket':
                return False
            else:
                raise
      
    @excp.exception(logger)      
    def put_bucket_notification_configuration(self, bucket_name, notification):
        '''Enables notifications of specified events for a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.put_bucket_notification_configuration'''
        return self.client.put_bucket_notification_configuration(Bucket=bucket_name, 
                                                                 NotificationConfiguration=notification)  
    
    @excp.exception(logger)    
    def get_bucket_notification_configuration(self, bucket_name):
        '''Returns the notification configuration of a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.get_bucket_notification_configuration'''
        return self.client.get_bucket_notification_configuration(Bucket=bucket_name)
            
    @excp.exception(logger)
    def upload_file(self, **kwargs):
        '''Adds an object to a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.put_object'''
        return self.client.put_object(**kwargs)          
            
    @excp.exception(logger)            
    def download_file(self, **kwargs):
        '''Download an object from S3 to a file-like object.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.download_fileobj'''
        return self.client.download_fileobj(**kwargs)
           
    @excp.exception(logger)            
    def list_files(self, **kwargs):
        '''Returns all of the objects in a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.list_objects_v2'''
        file_list = []
        response = self.client.list_objects_v2(**kwargs)
        file_list.append(response)
        while ('IsTruncated' in response) and (response['IsTruncated']):
            kwargs['ContinuationToken'] = response['NextContinuationToken']
            response = self.client.list_objects_v2(**kwargs)
            file_list.append(response)
        return file_list
    
    