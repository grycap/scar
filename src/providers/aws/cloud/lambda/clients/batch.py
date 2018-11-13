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
import re
import json
# Works in lambda environment
import src.utils as utils
logger = utils.get_logger()

class Batch():
    
    @utils.lazy_property
    def client(self):
        client = boto3.client('batch')
        return client    
    
    def __init__(self, lambda_instance, scar_input_file):
        self.lambda_instance = lambda_instance
        self.scar_batch_io_image_id="grycap/scarbatchio"
        self.script = self.get_user_script()
        self.scar_input_file = scar_input_file
        self.io_job_name = "{0}-io".format(lambda_instance.function_name)
        self.scar_batch_io_bin = "scar-batch-io"
        self.container_environment_variables = []
        self.create_context()
    
    def create_context(self):
        self.context = {'function_name': self.lambda_instance.context.function_name,
                        'memory_limit_in_mb': self.lambda_instance.context.memory_limit_in_mb,
                        'aws_request_id': self.lambda_instance.context.aws_request_id,
                        'log_group_name': self.lambda_instance.context.log_group_name,
                        'log_stream_name': self.lambda_instance.context.log_stream_name}
    
    def set_container_variables(self, step):
        self.add_environment_variable("STEP", step)
        self.add_environment_variable("SCRIPT", self.script)
        self.add_environment_variable("FUNCTION_NAME", self.lambda_instance.function_name)
        self.add_environment_variable("LAMBDA_EVENT", json.dumps(self.lambda_instance.event))
        self.add_environment_variable("LAMBDA_CONTEXT", json.dumps(self.context))
        self.add_environment_variable("SCAR_INPUT_DIR", self.lambda_instance.input_folder)
        self.add_environment_variable("SCAR_OUTPUT_DIR", self.lambda_instance.output_folder)
        self.add_environment_variable("REQUEST_ID", self.lambda_instance.request_id)

        if self.scar_input_file:
            self.add_environment_variable("SCAR_INPUT_FILE", self.scar_input_file)
        if self.lambda_instance.has_input_bucket():
            self.add_environment_variable("INPUT_BUCKET", self.lambda_instance.input_bucket)
        if self.lambda_instance.has_output_bucket():
            self.add_environment_variable("OUTPUT_BUCKET", self.lambda_instance.output_bucket)
        if self.lambda_instance.has_output_bucket_folder():
            self.add_environment_variable("OUTPUT_FOLDER", self.lambda_instance.output_bucket_folder)                 
        
        for user_var, value in self.get_user_defined_variables().items():
            self.add_environment_variable(user_var, value)
    
    def add_environment_variable(self, name, value):
        return self.container_environment_variables.append({"name" : name, "value" : value})    
    
    def get_register_job_definition_args(self, job_name, step):
        self.set_container_variables(step)
        job_def_args = {
            'jobDefinitionName': job_name,
            "type": "container",
            "containerProperties": {
                "image": self.scar_batch_io_image_id,
                "vcpus": 1,
                "memory": self.lambda_instance.memory,                       
                "command": ["scar-batch-io"],
                "volumes": [
                    {"host": {
                        "sourcePath": self.lambda_instance.input_folder},
                     "name": "SCAR_INPUT_DIR"},
                    {"host":{
                        "sourcePath": self.lambda_instance.output_folder},
                     "name": "SCAR_OUTPUT_DIR"},
                ],
                "environment" : self.container_environment_variables,                             
                'mountPoints': [
                    {"sourceVolume": "SCAR_INPUT_DIR",
                     "containerPath": self.lambda_instance.input_folder},
                    {"sourceVolume": "SCAR_OUTPUT_DIR",
                     "containerPath": self.lambda_instance.output_folder},
                ],
            },
        }
        if step == "MED":
            job_def_args["containerProperties"]["command"] = []
            if self.script != "":
                job_def_args["containerProperties"]["command"] = ["{0}/script.sh".format(self.lambda_instance.input_folder)]
            job_def_args["containerProperties"]["image"] = utils.get_environment_variable("IMAGE_ID")
        
        return job_def_args
    
    def register_job_definition(self, job_name, step):
        register_job_args = self.get_register_job_definition_args(job_name, step)
        self.client.register_job_definition(**register_job_args)
        
    def invoke_batch_function(self):
        # Register lambda Job
        self.register_job_definition(self.lambda_instance.function_name, "MED")
        # Submit download input Job
        job_id = None
        if self.lambda_instance.has_input_bucket() or self.script != "":
            self.register_job_definition(self.io_job_name, "INIT")
            job_id = self.submit_init_job()
        # Submit lambda Job
        lambda_job_id = self.submit_lambda_job(job_id)
        # Submit store output Job
        if self.lambda_instance.has_output_bucket():
            self.register_job_definition(self.io_job_name, "END")
            self.submit_end_job(lambda_job_id)
        return lambda_job_id
    
    def get_user_script(self):
        script = ""
        if utils.is_variable_in_environment('INIT_SCRIPT_PATH'):
            file_content = utils.read_file(utils.get_environment_variable('INIT_SCRIPT_PATH'), 'rb')
            script = utils.utf8_to_base64_string(file_content)        
        if utils.is_value_in_dict(self.lambda_instance.event, 'script'):
            script = self.lambda_instance.event['script']
        return script
    
    def get_job_args(self, step, job_id=None):
        job_name =  self.lambda_instance.function_name if step == 'MED' else self.io_job_name
        scar_input_file = "" if not self.scar_input_file else self.scar_input_file
            
        variables= []
        self.add_environment_variable("STEP", step)
        self.add_environment_variable("SCRIPT", self.get_user_script())
        self.add_environment_variable("FUNCTION_NAME", self.lambda_instance.function_name)
        self.add_environment_variable("SCAR_INPUT_FILE", scar_input_file)
        self.add_environment_variable("SCAR_INPUT_DIR", self.lambda_instance.input_folder)
        self.add_environment_variable("SCAR_OUTPUT_DIR", self.lambda_instance.output_folder)
        self.add_environment_variable("REQUEST_ID", self.lambda_instance.request_id)

        if self.lambda_instance.has_input_bucket():
            self.add_environment_variable("INPUT_BUCKET", self.lambda_instance.input_bucket)
        if self.lambda_instance.has_output_bucket():
            self.add_environment_variable("OUTPUT_BUCKET", self.lambda_instance.output_bucket)
        
        for user_var, value in utils.get_user_defined_variables().items():
            variables.append({"name" : user_var, "value" : value})

        job_def = {"jobDefinition" : job_name,
                   "jobName" : job_name,
                   "jobQueue" : self.lambda_instance.function_name,
                   "containerOverrides" : { "environment" : variables }
                  }
        if job_id:
            job_def['dependsOn'] = [{'jobId' : job_id, 'type' : 'SEQUENTIAL'}]
        return job_def    
    
    def submit_batch_job(self, job_args):
        return self.client.submit_job(**job_args)["jobId"]
    
    def submit_init_job(self):
        return self.submit_batch_job(self.get_job_args('INIT'))
    
    def submit_lambda_job(self, job_id):
        return self.submit_batch_job(self.get_job_args('MED', job_id))
    
    def submit_end_job(self, job_id):
        return self.submit_batch_job(self.get_job_args('END', job_id))
