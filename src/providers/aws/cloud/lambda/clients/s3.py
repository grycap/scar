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
import boto3
import os
from urllib.parse import unquote_plus
# Works in lambda environment
import src.utils as utils
logger = utils.get_logger()


class S3():
    
    @utils.lazy_property
    def client(self):
        client = boto3.client('s3')
        return client
    
    def __init__(self, lambda_instance):
        self.lambda_instance = lambda_instance
        if utils.is_value_in_dict(self.lambda_instance.event, 'Records'):
            self.record = self.get_s3_record()
            self.input_bucket = self.record['bucket']['name']
            self.file_key = unquote_plus(self.record['object']['key'])
            self.file_name = os.path.basename(self.file_key).replace(' ', '')
            self.file_download_path = '{0}/{1}'.format(self.lambda_instance.input_folder, self.file_name)

    def get_s3_record(self):
        if len(self.lambda_instance.event['Records']) > 1:
            logger.warning("Multiple records detected. Only processing the first one.")
            
        record = self.lambda_instance.event['Records'][0]
        if utils.is_value_in_dict(record, 's3'):
            return record['s3']

    def download_input(self):
        '''Downloads the file from the S3 bucket and returns the path were the download is placed'''
        logger.info("Downloading item from bucket '{0}' with key '{1}'".format(self.input_bucket, self.file_key))
        if not os.path.isdir(self.file_download_path):
            os.makedirs(os.path.dirname(self.file_download_path), exist_ok=True)
        with open(self.file_download_path, 'wb') as data:
            self.client.download_fileobj(self.input_bucket, self.file_key, data)
        logger.info("Successful download of file '{0}' from bucket '{1}' in path '{2}'".format(self.file_key, 
                                                                                               self.input_bucket,
                                                                                               self.file_download_path))
        return self.file_download_path
  
    def get_file_key(self, function_name=None, folder=None, file_name=None):
        if function_name:
            return "{0}/{1}/{2}/{3}".format(function_name, folder, self.lambda_instance.request_id, file_name)
        else:
            return "{0}/{1}/{2}".format(folder, self.lambda_instance.request_id, file_name)

    def upload_output(self, bucket_name, bucket_folder=None):
        output_files_path = utils.get_all_files_in_directory(self.lambda_instance.output_folder)
        logger.debug("UPLOADING FILES {0}".format(output_files_path))
        for file_path in output_files_path:
            file_name = file_path.replace("{0}/".format(self.lambda_instance.output_folder), "")
            if bucket_folder:
                file_key = self.get_file_key(folder=bucket_folder, file_name=file_name)
            else:
                file_key = self.get_file_key(function_name=self.lambda_instance.function_name, folder='output', file_name=file_name)
            self.upload_file(bucket_name, file_path, file_key)
            
    def upload_file(self, bucket_name, file_path, file_key):
        logger.info("Uploading file  '{0}' to bucket '{1}'".format(file_key, bucket_name))
        with open(file_path, 'rb') as data:
            self.client.upload_fileobj(data, bucket_name, file_key)
        logger.info("Changing ACLs for public-read for object in bucket {0} with key {1}".format(bucket_name, file_key))
        obj = boto3.resource('s3').Object(bucket_name, file_key)
        obj.Acl().put(ACL='public-read')
    
    def download_file_to_memory(self, bucket_name, file_key):
        obj = boto3.resource('s3').Object(bucket_name=bucket_name, key=file_key)
        print ("Reading item from bucket {0} with key {1}".format(bucket_name, file_key))
        return obj.get()["Body"].read()
    
    def delete_file(self):
        self.client.delete_object(Bucket=self.input_bucket, Key=self.file_key)
        