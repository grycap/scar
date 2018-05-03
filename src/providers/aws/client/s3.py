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
import src.logger as logger
import src.utils as utils
import os

class S3():

    @utils.lazy_property
    def client(self):
        if hasattr(self, 'region'):
            client = S3Client(self.region)
        else:
            client = S3Client()
        return client
    
    @utils.lazy_property
    def trigger_configuration(self):
        file_path = os.path.dirname(os.path.realpath(__file__)) + "/s3_trigger_conf.json"     
        trigger_configuration = utils.load_json_file(file_path)
        return trigger_configuration
    
    def __init__(self, aws_lambda=None):
        if aws_lambda:
            self.input_bucket = aws_lambda.get_property("input_bucket")
            self.input_folder = aws_lambda.get_property("input_folder")
            if self.input_folder is None:
                self.input_folder = "{0}/input/".format(aws_lambda.get_function_name())
            
            self.function_arn = aws_lambda.get_property("function_arn")
            self.region = aws_lambda.get_property("region")

    def create_bucket(self, bucket_name):
        try:
            if not self.client.find_bucket_by_name(bucket_name):
                # Create the bucket if not found
                self.client.create_bucket(bucket_name)
        except ClientError as ce:
            error_msg = "Error creating the bucket '%s'" % self.input_bucket
            logger.error(error_msg, error_msg + ": %s" % ce)

    def create_input_bucket(self):
        self.create_bucket(self.input_bucket)
        self.add_bucket_folder(self.input_bucket, self.input_folder)

    def add_bucket_folder(self, bucket_name, folder_name):
        try:
            self.client.put_object(bucket_name, folder_name)
        except ClientError as ce:
            error_msg = "Error creating the folder '%s' in the bucket '%s'" % (folder_name, bucket_name)
            logger.error(error_msg, error_msg + ": %s" % (folder_name, bucket_name, ce))

    def set_input_bucket_notification(self):           
        notification = { "LambdaFunctionConfigurations": [self.get_trigger_configuration(self.function_arn, self.input_folder)] }
        self.client.put_bucket_notification_configuration(self.input_bucket, notification)
            
    def get_trigger_configuration(self, function_arn, folder_name):
        self.trigger_configuration["LambdaFunctionArn"] = function_arn
        self.trigger_configuration["Filter"]["Key"]["FilterRules"][0]["Value"] = folder_name
        return self.trigger_configuration
        
    def get_processed_bucket_file_list(self):
        file_list = []
        result = self.client.get_bucket_file_list(self.input_bucket, self.input_folder)
        if 'Contents' in result:
            for content in result['Contents']:
                if content['Key'] and content['Key'] != self.input_folder:
                    file_list.append(content['Key'])
        return file_list         

    def upload_file(self, bucket_name, file_key, file_data):
        try:
            self.client.put_object(bucket_name, file_key, file_data)
        except ClientError as ce:
            error_msg = "Error uploading the file '%s' to the S3 bucket '%s'" % (file_key, bucket_name)
            logger.error(error_msg, error_msg + ": %s" % ce)          

class S3Client(BotoClient):
    '''A low-level client representing Amazon Simple Storage Service (S3Client).
    https://boto3.readthedocs.io/en/latest/reference/services/s3.html'''
    
    def __init__(self, region=None):
        super().__init__('s3', region)
         
    def create_bucket(self, bucket_name):
        try:
            self.get_client().create_bucket(ACL='private', Bucket=bucket_name)
        except ClientError as ce:
            error_msg = "Error creating the S3Client bucket '%s'" % bucket_name
            logger.error(error_msg, error_msg + ": %s" % (bucket_name, ce))
    
    def find_bucket_by_name(self, bucket_name):
        try:
            # If this call works the bucket exists
            self.get_client().get_bucket_location(Bucket=bucket_name)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'NoSuchBucket':
                return False
            else:
                error_msg = "Error, bucket '{0}' not found".format(bucket_name)
                logger.error(error_msg, error_msg + ": {0}".format(ce))        
    
    def get_bucket_file_list(self, bucket_name, prefix):
        try:
            return  self.get_client().list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        except ClientError as ce:
            error_msg = "Error listing files from bucket '%s'" % bucket_name
            logger.error(error_msg, error_msg + ": %s" % (bucket_name, ce))
    
    def put_bucket_notification_configuration(self, bucket_name, notification):
        '''Enables notifications of specified events for a bucket.'''
        try:
            self.get_client().put_bucket_notification_configuration(Bucket=bucket_name,
                                                                    NotificationConfiguration=notification)
        except ClientError as ce:
            error_msg = "Error configuring S3Client bucket"
            logger.error(error_msg, error_msg + ": %s" % ce)          
            
    def put_object(self, bucket_name, file_key, file_data=None):
        '''Adds an object to a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.put_object'''
        if file_data:
            self.get_client().put_object(Bucket=bucket_name, Key=file_key, Body=file_data)
        else:
            self.get_client().put_object(Bucket=bucket_name, Key=file_key)
              
    
