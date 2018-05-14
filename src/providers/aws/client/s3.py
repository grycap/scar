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
    
    def get_bucket_files(self, bucket_name, prefix_key):
        if prefix_key is None:
            prefix_key = ''
        file_list = []
        result = self.client.list_files(bucket_name, key=prefix_key)
        if 'Contents' in result:
            for info in result['Contents']:
                file_list += [info['Key']]
        while result['IsTruncated']:
            token = result['NextContinuationToken']
            result = self.client.list_files(bucket_name, key=prefix_key, continuation_token=token)
            for info in result['Contents']:
                file_list += [info['Key']]
        return file_list        
    
    def download_bucket_files(self, bucket_name, file_prefix, output):
        file_key_list = self.get_bucket_files(bucket_name, file_prefix)
        for file_key in file_key_list:
            # Avoid download s3 'folders'
            if not file_key.endswith('/'):
                # Parse file path
                file_name = os.path.basename(file_key)
                file_dir = file_key.replace(file_name, "")
                dir_name = os.path.dirname(file_prefix)
                if dir_name != '':
                    local_path = file_dir.replace(os.path.dirname(file_prefix)+"/", "")
                else:
                    local_path = file_prefix + "/"
                # Modify file path if there is an output defined
                if output:
                    if not output.endswith('/') and len(file_key_list) == 1:
                        file_path = output
                    else:
                        local_path = output + local_path
                        file_path = local_path + file_name
                else:   
                    file_path = local_path + file_name
                # make sure the folders are created
                if os.path.dirname(local_path) != '' and not os.path.isdir(local_path):
                    os.makedirs(local_path, exist_ok=True)
                self.download_file(bucket_name, file_key, file_path)
    
    def download_file(self, bucket_name, file_key, file_path):
        logger.info("Downloading file '{0}' from bucket '{1}' in path '{2}'".format(file_key, bucket_name, file_path))
        with open(file_path, 'wb') as f:
            self.client.download_file(bucket_name, file_key, f)  

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
            
    def download_file(self, bucket_name, file_key, file):
        '''Adds an object to a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.download_fileobj'''
        try:
            self.get_client().download_fileobj(bucket_name, file_key, file)
            
        except ClientError as ce:
            error_msg = "Error downloading file '{0}' from bucket '{1}'".format(file_key, bucket_name)
            logger.error(error_msg, error_msg + "{0}: {1}".format(bucket_name, ce))
            
    def list_files(self, bucket_name, key='', continuation_token=None):
        '''Adds an object to a bucket.
        https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.download_fileobj'''
        try:
            if continuation_token:
                return self.get_client().list_objects_v2(Bucket=bucket_name, Prefix=key, ContinuationToken=continuation_token)
            else:
                return self.get_client().list_objects_v2(Bucket=bucket_name, Prefix=key)
        except ClientError as ce:
            error_msg = "Error listing files from bucket '{0}'".format(bucket_name)
            logger.error(error_msg, error_msg + "{0}: {1}".format(bucket_name, ce))            
            
