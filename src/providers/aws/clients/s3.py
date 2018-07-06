# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from src.providers.aws.clients.boto import BotoClient
from botocore.exceptions import ClientError
import src.logger as logger
import src.utils as utils

class S3Client(BotoClient):
    '''A low-level client representing Amazon Simple Storage Service (S3Client).
    https://boto3.readthedocs.io/en/latest/reference/services/s3.html'''
    
    boto_client_name = 's3'    
    
    @utils.exception(logger)    
    def create_bucket(self, bucket_name):
        '''Creates a new S3 bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.ServiceResource.create_bucket'''        
        self.client.create_bucket(ACL='private', Bucket=bucket_name)
    
    @utils.exception(logger)
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
      
    @utils.exception(logger)      
    def put_bucket_notification_configuration(self, bucket_name, notification):
        '''Enables notifications of specified events for a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.put_bucket_notification_configuration'''
        return self.client.put_bucket_notification_configuration(Bucket=bucket_name, 
                                                                 NotificationConfiguration=notification)  
    
    @utils.exception(logger)    
    def get_bucket_notification_configuration(self, bucket_name):
        '''Returns the notification configuration of a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.get_bucket_notification_configuration'''
        return self.client.get_bucket_notification_configuration(Bucket=bucket_name)
            
    @utils.exception(logger)
    def upload_file(self, bucket_name, file_key, file_data=None):
        '''Adds an object to a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.put_object'''
        kwargs = {'Bucket' : bucket_name, 'Key' : file_key}
        if file_data:
            kwargs['Body'] = file_data
        return self.client.put_object(**kwargs)          
            
    @utils.exception(logger)            
    def download_file(self, bucket_name, file_key, file):
        '''Download an object from S3 to a file-like object.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.download_fileobj'''
        return self.client.download_fileobj(Bucket=bucket_name, Key=file_key, Fileobj=file)
           
    @utils.exception(logger)            
    def list_files(self, bucket_name, key=''):
        '''Returns all of the objects in a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.list_objects_v2'''
        file_list = []
        kwargs = {"Bucket" : bucket_name, "Prefix" : key}
        response = self.client.list_objects_v2(**kwargs)
        file_list.append(response)
        while ('IsTruncated' in response) and (response['IsTruncated']):
            kwargs['ContinuationToken'] = response['NextContinuationToken']
            response = self.client.list_objects_v2(**kwargs)
            file_list.append(response)
        return response
    
    