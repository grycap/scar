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

import src.logger as logger
import os
from src.providers.aws.botoclientfactory import GenericClient
import src.exceptions as excp 
import src.utils as utils

class S3(GenericClient):
    
    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.properties = aws_properties['s3']
        self.parse_input_folder()

    def parse_input_folder(self):
        if not 'input_folder' in self.properties:
            if 'name' in self.aws_properties['lambda']:
                self.properties['input_folder'] = "{0}/input/".format(self.aws_properties['lambda']['name'])
            else:
                self.properties['input_folder'] = ''
        elif not self.properties['input_folder'].endswith("/"):
            self.properties['input_folder'] = "{0}/".format(self.properties['input_folder'])
        
    @excp.exception(logger)
    def create_bucket(self, bucket_name):
        if not self.client.find_bucket(bucket_name):
#             raise excp.ExistentBucketWarning(bucket_name=bucket_name)
#         else:
            self.client.create_bucket(bucket_name)

    def create_output_bucket(self):
        self.create_bucket(self.properties['output_bucket'])

    @excp.exception(logger)
    def add_bucket_folder(self):
        if self.properties['input_folder']:
            self.upload_file(folder_name=self.properties['input_folder'])

    def create_input_bucket(self, create_input_folder=False):
        self.create_bucket(self.properties['input_bucket'])
        if create_input_folder:
            self.add_bucket_folder()

    def set_input_bucket_notification(self):
        # First check that the function doesn't have other configurations
        input_bucket = self.properties['input_bucket']
        bucket_conf = self.client.get_bucket_notification_configuration(input_bucket)
        trigger_conf = self.get_trigger_configuration()
        lambda_conf = [trigger_conf]
        if "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            lambda_conf.append(trigger_conf)
        notification = { "LambdaFunctionConfigurations": lambda_conf }
        self.client.put_bucket_notification_configuration(input_bucket, notification)
        
    def delete_bucket_notification(self):
        bucket_conf = self.client.get_bucket_notification_configuration(self.properties['input_bucket'])
        if bucket_conf and "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            filter_conf = [x for x in lambda_conf if x['LambdaFunctionArn'] != self.aws_properties['lambda']['arn']]
            notification = { "LambdaFunctionConfigurations": filter_conf }
            self.client.put_bucket_notification_configuration(self.properties['input_bucket'], notification)        
        
    def get_trigger_configuration(self):
        return  {"LambdaFunctionArn": self.aws_properties['lambda']['function_arn'],
                 "Events": [ "s3:ObjectCreated:*" ],
                 "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": self.properties['input_folder'] }]}}
                 }        
    
    def get_file_key(self, folder_name=None, file_path=None, file_key=None):
        if file_key:
            return file_key
        file_key = ''
        if file_path:
            file_key = os.path.basename(file_path)        
            if folder_name:
                file_key = utils.join_paths(folder_name, file_key)
        elif folder_name:
            file_key = folder_name if folder_name.endswith('/') else '{0}/'.format(folder_name)
        return file_key
    
    @excp.exception(logger)        
    def upload_file(self, folder_name=None, file_path=None, file_key=None):
        kwargs = {'Bucket' : self.properties['input_bucket']}
        kwargs['Key'] = self.get_file_key(folder_name, file_path, file_key)
        if file_path:
            try:
                kwargs['Body'] = utils.read_file(file_path, 'rb')
            except FileNotFoundError:
                raise excp.UploadFileNotFoundError(file_path=file_path)
        if folder_name and not file_path:
            logger.info("Folder '{0}' created in bucket '{1}'".format(kwargs['Key'], kwargs['Bucket']))
        else:
            logger.info("Uploading file '{0}' to bucket '{1}' from '{2}'".format(kwargs['Key'], kwargs['Bucket'], file_path))
        self.client.upload_file(**kwargs)
    
    @excp.exception(logger)
    def get_bucket_file_list(self):
        bucket_name = self.properties['input_bucket']
        if self.client.find_bucket(bucket_name):
            kwargs = {"Bucket" : bucket_name}
            if ('input_folder' in self.properties) and self.properties['input_folder']:
                kwargs["Prefix"] = self.properties['input_folder']
            response = self.client.list_files(**kwargs)
            return self.parse_file_keys(response)
        else:
            raise excp.BucketNotFoundError(bucket_name=bucket_name)
    
    def parse_file_keys(self, response):
        return [info['Key'] for elem in response if 'Contents' in elem for info in elem['Contents'] if not info['Key'].endswith('/')]       

    def get_s3_event(self, s3_file_key):
        return { "Records" : [ {"eventSource" : "aws:s3",
                 "s3" : {"bucket" : { "name" : self.properties['input_bucket'] },
                         "object" : { "key" : s3_file_key  } }
                }]}
        
    def get_s3_event_list(self, s3_file_keys):
        s3_events = []
        for s3_key in s3_file_keys:
            s3_events.append(self.get_s3_event(s3_key))
    
    def download_file(self, bucket_name, file_key, file_path):
        kwargs = {'Bucket' : bucket_name, 'Key' : file_key}
        logger.info("Downloading file '{0}' from bucket '{1}' in path '{2}'".format(file_key, bucket_name, file_path))
        with open(file_path, 'wb') as file:
            kwargs['Fileobj'] = file
            self.client.download_file(**kwargs)  
