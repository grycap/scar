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
import json
import subprocess
import traceback
import sys

sys.path.append("..")
sys.path.append(".")
# Works in lambda environment
import src.utils as utils
from src.clients.lambdafunction import Lambda
from src.clients.batch import Batch
from src.clients.apigateway import ApiGateway
from src.clients.s3 import S3
from src.clients.udocker import Udocker

logger = utils.get_logger()
logger.info('SCAR: Loading lambda function')

class Supervisor():
    
    @utils.lazy_property
    def s3(self):
        s3 = S3(self.lambda_instance)
        return s3

    @utils.lazy_property
    def batch(self):
        batch = Batch(self.lambda_instance, self.scar_input_file)
        return batch
    
    @utils.lazy_property
    def apigateway(self):
        apigateway = ApiGateway(self.lambda_instance)
        return apigateway
    
    @utils.lazy_property
    def udocker(self):
        udocker = Udocker(self.lambda_instance, self.scar_input_file)
        return udocker
    
    def __init__(self, event, context):
        self.lambda_instance = Lambda(event, context)
        self.create_temporal_folders()
        self.create_event_file()
        self.status_code = 200
        self.body = {}

    def is_s3_event(self):
        if utils.is_value_in_dict(self.lambda_instance.event, 'Records'):
            return self.lambda_instance.event['Records'][0]['eventSource'] == "aws:s3"
        return False
           
    def is_apigateway_event(self):
        return 'httpMethod' in self.lambda_instance.event           
           
    def parse_input(self):
        self.scar_input_file = None
        if self.is_s3_event():
            self.input_bucket = self.s3.input_bucket
            logger.debug("INPUT BUCKET SET TO {0}".format(self.input_bucket))
            self.scar_input_file = self.s3.download_input()
            logger.debug("INPUT FILE SET TO {0}".format(self.scar_input_file))
        elif self.is_apigateway_event():
            self.scar_input_file = self.apigateway.save_post_body()
            logger.debug("INPUT FILE SET TO {0}".format(self.scar_input_file))
        
    def prepare_udocker(self):
        self.udocker.create_image()
        self.udocker.create_container()
        self.udocker.create_command()
        
    def execute_udocker(self):
        try:
            udocker_output = self.udocker.launch_udocker_container()
            logger.info("CONTAINER OUTPUT:\n " + udocker_output)
            self.body["udocker_output"] = udocker_output            
        except subprocess.TimeoutExpired:
            logger.warning("Container execution timed out")
            if(utils.get_environment_variable("EXECUTION_MODE") == "lambda-batch"):
                self.execute_batch()
                
    def has_input_bucket(self):
        return hasattr(self, "input_bucket") and self.input_bucket and self.input_bucket != "" 

    def upload_to_bucket(self):
        bucket_name = None
        bucket_folder = None
        
        if self.lambda_instance.has_output_bucket():
            bucket_name = self.lambda_instance.output_bucket
            logger.debug("OUTPUT BUCKET SET TO {0}".format(bucket_name))
            if self.lambda_instance.has_output_bucket_folder():
                bucket_folder = self.lambda_instance.output_bucket_folder
                logger.debug("OUTPUT FOLDER SET TO {0}".format(bucket_folder))
                
        elif self.lambda_instance.has_input_bucket():
            bucket_name = self.lambda_instance.input_bucket
            logger.debug("OUTPUT BUCKET SET TO {0}".format(bucket_name))
            
        if bucket_name:
            self.s3.upload_output(bucket_name, bucket_folder)

    def parse_output(self):
        self.upload_to_bucket()
        self.clean_instance_files()
        
    def create_response(self):
        return {"statusCode" : self.status_code, 
                "headers" : { 
                    "amz-lambda-request-id": self.lambda_instance.request_id, 
                    "amz-log-group-name": self.lambda_instance.log_group_name, 
                    "amz-log-stream-name": self.lambda_instance.log_stream_name },
                "body" : json.dumps(self.body),
                "isBase64Encoded" : False                
                }
        
    def clean_instance_files(self):
        utils.delete_folder(self.lambda_instance.temporal_folder)
        
    def create_temporal_folders(self):
        utils.create_folder(self.lambda_instance.temporal_folder)
        utils.create_folder(self.lambda_instance.input_folder)
        utils.create_folder(self.lambda_instance.output_folder)
    
    def create_event_file(self):
        utils.create_file_with_content("{0}/event.json".format(self.lambda_instance.temporal_folder), json.dumps(self.lambda_instance.event))        

    def execute_batch(self):
        batch_ri = self.batch.invoke_batch_function()
        batch_logs = "Check batch logs with: \n  scar log -n {0} -ri {1}".format(self.lambda_instance.function_name, batch_ri)
        self.body["udocker_output"] = "Job delegated to batch.\n{0}".format(batch_logs)         

    def is_batch_execution(self):
        return utils.get_environment_variable("EXECUTION_MODE") == "batch"
    
    def execute_function(self):
        if self.is_batch_execution():
            self.execute_batch()
        else:
            self.prepare_udocker()
            self.execute_udocker()

def lambda_handler(event, context):
    logger.debug("Received event: " + json.dumps(event))
    supervisor = Supervisor(event, context)
    try:
        supervisor.parse_input()
        supervisor.execute_function()                                      
        supervisor.parse_output()

    except Exception:
        logger.error("Exception launched:\n {0}".format(traceback.format_exc()))
        supervisor.body["exception"] = traceback.format_exc()
        supervisor.status_code = 500
    
    return supervisor.create_response()
