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

from .boto import BotoClient
from botocore.exceptions import ClientError
import logging

class S3Client(BotoClient):
    '''A low-level client representing Amazon Simple Storage Service (S3Client).
    https://boto3.readthedocs.io/en/latest/reference/services/s3.html'''
    
    def __init__(self, region=None):
        super().__init__('s3', region)
         
    def get_s3_file_list(self, bucket_name):
        file_list = []
        result = self.get_client().list_objects_v2(Bucket=bucket_name, Prefix='input/')
        if 'Contents' in result:
            for content in result['Contents']:
                if content['Key'] and content['Key'] != "input/":
                    file_list.append(content['Key'])
        return file_list
    
    def put_bucket_notification_configuration(self, bucket_name, notification):
        try:
            self.get_client().put_bucket_notification_configuration(Bucket=bucket_name,
                                                                NotificationConfiguration=notification)
        except ClientError as ce:
            print("Error configuring S3Client bucket")
            logging.error("Error configuring S3Client bucket: %s" % ce)
    
    def check_and_create_s3_bucket(self, bucket_name):
        try:
            buckets = self.get_client().list_buckets()
            # Search for the bucket
            found_bucket = [bucket for bucket in buckets['Buckets'] if bucket['Name'] == bucket_name]
            if not found_bucket:
                # Create the bucket if not found
                self.create_s3_bucket(bucket_name)
            # Add folder structure
            self.add_s3_bucket_folder(bucket_name, "input/")
            self.add_s3_bucket_folder(bucket_name, "output/")
        except ClientError as ce:
            print("Error getting the S3Client buckets list")
            logging.error("Error getting the S3Client buckets list: %s" % ce)
    
    def create_s3_bucket(self, bucket_name):
        try:
            self.get_client().create_bucket(ACL='private', Bucket=bucket_name)
        except ClientError as ce:
            print("Error creating the S3Client bucket '%s'" % bucket_name)
            logging.error("Error creating the S3Client bucket '%s': %s" % (bucket_name, ce))
    
    def add_s3_bucket_folder(self, bucket_name, folder_name):
        try:
            self.get_client().put_object(Bucket=bucket_name, Key=folder_name)
        except ClientError as ce:
            print("Error creating the S3Client bucket '%s' folder '%s'" % (bucket_name, folder_name))
            logging.error("Error creating the S3Client bucket '%s' folder '%s': %s" % (bucket_name, folder_name, ce))    
    
    def get_trigger_configuration(self, function_arn, folder_name):
        return { "LambdaFunctionArn": function_arn,
                 "Events": [ "s3:ObjectCreated:*" ],
                 "Filter": { 
                     "Key": { 
                         "FilterRules": [
                             { "Name": "prefix",
                               "Value": folder_name }
                         ]
                     }
                 }}
           
    def create_trigger_from_bucket(self, bucket_name, function_arn):
        notification = { "LambdaFunctionConfigurations": [self.get_trigger_configuration(function_arn, "input/")] }
        self.put_bucket_notification_configuration(bucket_name, notification)
            
    def create_recursive_trigger_from_bucket(self, bucket_name, function_arn):
        notification = { "LambdaFunctionConfigurations": [
                            self.get_trigger_configuration(function_arn, "input/"),
                            self.get_trigger_configuration(function_arn, "recursive/")] }
        self.put_bucket_notification_configuration(bucket_name, notification) 
        