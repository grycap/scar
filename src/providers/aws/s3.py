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

from botocore.exceptions import ClientError
import src.logger as logger
import os
from src.providers.aws.clientfactory import GenericClient

class S3(GenericClient):

    def __init__(self, aws_lambda=None):
        if aws_lambda:
            self.input_bucket = aws_lambda.get_property("input_bucket")
            self.input_folder = aws_lambda.get_property("input_folder")
            if self.input_folder and not self.input_folder.endswith("/"):
                self.input_folder = self.input_folder + "/"
            if self.input_folder is None:
                self.input_folder = "{0}/input/".format(aws_lambda.get_function_name())
            self.function_arn = aws_lambda.get_property("function_arn")
            self.region = aws_lambda.get_property("region")
            self.trigger_configuration =  {  "LambdaFunctionArn": "",
                  "Events": [ "s3:ObjectCreated:*" ],
                  "Filter": {
                      "Key": {
                        "FilterRules": [{ "Name": "prefix",
                                            "Value": "" }]
                    }
                  }
                }
    
    def create_bucket(self, bucket_name):
        try:
            if not self.client.find_bucket(bucket_name):
                # Create the bucket if not found
                self.client.create_bucket(bucket_name)
        except ClientError as ce:
            error_msg = "Error creating the bucket '{0}'".format(self.input_bucket)
            logger.log_exception(error_msg, ce)

    def add_bucket_folder(self):
        try:
            self.client.upload_file(self.input_bucket, self.input_folder)
        except ClientError as ce:
            error_msg = "Error creating the folder '{0}' in the bucket '{1}'".format(self.input_bucket, self.input_folder)
            logger.log_exception(error_msg, ce)

    def create_input_bucket(self):
        self.create_bucket(self.input_bucket)
        self.add_bucket_folder()

    def set_input_bucket_notification(self):
        # First check that the function doesn't have other configurations
        bucket_conf = self.client.get_bucket_notification_configuration(self.input_bucket)
        trigger_conf = self.get_trigger_configuration(self.function_arn, self.input_folder)
        lambda_conf = [trigger_conf]
        if "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            lambda_conf.append(trigger_conf)
        notification = { "LambdaFunctionConfigurations": lambda_conf }
        self.client.put_bucket_notification_configuration(self.input_bucket, notification)
        
    def delete_bucket_notification(self, bucket_name, function_arn):
        bucket_conf = self.client.get_bucket_notification_configuration(bucket_name)
        if bucket_conf and "LambdaFunctionConfigurations" in bucket_conf:
            lambda_conf = bucket_conf["LambdaFunctionConfigurations"]
            filter_conf = [x for x in lambda_conf if x['LambdaFunctionArn'] != function_arn]
            notification = { "LambdaFunctionConfigurations": filter_conf }
            self.client.put_bucket_notification_configuration(bucket_name, notification)        
        
    def get_trigger_configuration(self, function_arn, folder_name):
        self.trigger_configuration["LambdaFunctionArn"] = function_arn
        self.trigger_configuration["Filter"]["Key"]["FilterRules"][0]["Value"] = folder_name
        return self.trigger_configuration
        
    def get_processed_bucket_file_list(self):
        file_list = []
        result = self.client.list_files(self.input_bucket, self.input_folder)
        if 'Contents' in result:
            for content in result['Contents']:
                if content['Key'] and content['Key'] != self.input_folder:
                    file_list.append(content['Key'])
        return file_list         

    def upload_file(self, bucket_name, file_key, file_data):
        try:
            self.client.upload_file(bucket_name, file_key, file_data)
        except ClientError as ce:
            error_msg = "Error uploading the file '{0}' to the S3 bucket '{1}'".format(file_key, bucket_name)
            logger.log_exception(error_msg, ce)
    
    def get_bucket_files(self, bucket_name, prefix_key):
        file_list = []
        if self.client.find_bucket(bucket_name):
            if prefix_key is None:
                prefix_key = ''
            result = self.client.list_files(bucket_name, key=prefix_key)
            if 'Contents' in result:
                for info in result['Contents']:
                    file_list += [info['Key']]
        else:
            logger.warning("Bucket '{0}' not found".format(bucket_name))
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
