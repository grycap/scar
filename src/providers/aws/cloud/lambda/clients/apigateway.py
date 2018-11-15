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
import uuid
import base64
# Works in lambda environment
import src.utils as utils
logger = utils.get_logger()

class ApiGateway():

    def __init__(self, lambda_instance):
        self.lambda_instance = lambda_instance

    def is_post_request_with_body(self):
        return self.lambda_instance.event['httpMethod'] == 'POST' and self.lambda_instance.event['body'] is not None

    def is_post_request_with_body_json(self):
        return self.lambda_instance.event['httpMethod'] == 'POST' and self.lambda_instance.event['headers']['Content-Type'].strip() == 'application/json'

    def save_post_body_json(self):
        body = self.lambda_instance.event['body']
        file_path = "/tmp/{0}/api_event.json".format(self.lambda_instance.request_id)
        logger.info("Received JSON from POST request and saved it in path '{0}'".format(file_path))
        self.save_file(file_path, 'w', body)            
        return file_path

    def save_post_body_file(self):
        body = base64.b64decode(self.lambda_instance.event['body'])
        body_file_name = uuid.uuid4().hex
        file_path = "/tmp/{0}/{1}".format(self.lambda_instance.request_id, body_file_name)
        logger.info("Received file from POST request and saved it in path '{0}'".format(file_path))
        self.save_file(file_path, 'wb', body)
        return file_path
    
    def save_file(self, file_path, write_mode, content):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  
        with open(file_path, write_mode) as data:
            data.write(content)

    def save_post_body(self):
        if self.is_post_request_with_body_json():
            return self.save_post_body_json()
        elif self.is_post_request_with_body:
            return self.save_post_body_file()
        