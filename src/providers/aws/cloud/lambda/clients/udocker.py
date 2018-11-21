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
import os
import shutil
import subprocess
import socket
# Works in lambda environment
import src.utils as utils
logger = utils.get_logger()

class Udocker():

    udocker_exec = "/var/task/udockerb"
    container_name = "udocker_container"
    script_exec = "/bin/sh"

    def __init__(self, lambda_instance, scar_input_file):
        self.lambda_instance = lambda_instance
        self.container_output_file = "{0}/container-stdout.txt".format(self.lambda_instance.temporal_folder)
        self.scar_input_file = scar_input_file
        
        if utils.is_variable_in_environment("IMAGE_ID"):
            self.container_image_id = utils.get_environment_variable("IMAGE_ID")
            self.set_udocker_commands()
        else:
            raise Exception("Container image id not specified.")
    
    def set_udocker_commands(self):
        self.cmd_udocker = [self.udocker_exec]
        self.cmd_get_images = self.cmd_udocker + ["images"]
        self.cmd_load_image = self.cmd_udocker + ["load", "-i", self.container_image_id]
        self.cmd_download_image = self.cmd_udocker + ["pull", self.container_image_id]
        self.cmd_list_containers = self.cmd_udocker + ["ps"]
        self.cmd_create_container = self.cmd_udocker + ["create", "--name={0}".format(self.container_name), self.container_image_id]
        self.cmd_set_execution_mode = self.cmd_udocker + ["setup", "--execmode=F1", self.container_name]
        self.cmd_container_execution = self.cmd_udocker + ["--quiet", "run"]
        
    def is_container_image_downloaded(self):
        cmd_out = utils.execute_command_and_return_output(self.cmd_get_images)
        return self.container_image_id in cmd_out              

    def create_image(self):
        if self.is_container_image_downloaded():
            logger.info("Container image '{0}' already available".format(self.container_image_id))
        else:                     
            if utils.is_variable_in_environment("IMAGE_FILE"):
                self.load_local_container_image()
            else:
                self.download_container_image()        

    def load_local_container_image(self):
        logger.info("Loading container image '{0}'".format(self.container_image_id))
        utils.execute_command(self.cmd_load_image)
        
    def download_container_image(self):
        logger.info("Pulling container '{0}' from Docker Hub".format(self.container_image_id))
        utils.execute_command(self.cmd_download_image)

    def is_container_available(self):
        cmd_out = utils.execute_command_and_return_output(self.cmd_list_containers)
        return self.container_name in cmd_out      

    def create_container(self):
        if self.is_container_available():
            logger.info("Container already available")
        else:
            logger.info("Creating container based on image '{0}'.".format(self.container_image_id))
            utils.execute_command(self.cmd_create_container)
        utils.execute_command(self.cmd_set_execution_mode)

    def create_command(self):
        self.add_container_volumes()
        self.add_container_environment_variables()
        # Container running script
        if utils.is_value_in_dict(self.lambda_instance.event, 'script'): 
            # Add script in memory as entrypoint
            script_path = "{0}/script.sh".format(self.lambda_instance.temporal_folder)
            script_content = utils.base64_to_utf8_string(self.lambda_instance.event['script'])
            utils.create_file_with_content(script_path, script_content)
            self.cmd_container_execution += ["--entrypoint={0} {1}".format(self.script_exec, script_path), self.container_name]
        # Container with args
        elif utils.is_value_in_dict(self.lambda_instance.event,'cmd_args'):
            # Add args
            self.cmd_container_execution += [self.container_name]
            self.cmd_container_execution += json.loads(self.lambda_instance.event['cmd_args'])
        # Script to be executed every time (if defined)
        elif utils.is_variable_in_environment('INIT_SCRIPT_PATH'):
            # Add init script
            init_script_path = "{0}/init_script.sh".format(self.lambda_instance.temporal_folder)
            shutil.copyfile(utils.get_environment_variable("INIT_SCRIPT_PATH"), init_script_path)    
            self.cmd_container_execution += ["--entrypoint={0} {1}".format(self.script_exec, init_script_path), self.container_name]
        # Only container
        else:
            self.cmd_container_execution += [self.container_name]
    
    def add_container_volumes(self):
        self.cmd_container_execution += ["-v", self.lambda_instance.temporal_folder]
        self.cmd_container_execution += ["-v", "/dev", "-v", "/proc", "-v", "/etc/hosts", "--nosysdirs"]
        if utils.is_variable_in_environment('EXTRA_PAYLOAD'):
            self.cmd_container_execution += ["-v", self.lambda_instance.permanent_folder]

    def add_container_environment_variable(self, key, value):
        self.cmd_container_execution += self.parse_container_environment_variable(key, value)
            
    def add_container_environment_variables(self):
        self.cmd_container_execution += self.parse_container_environment_variable("REQUEST_ID", self.lambda_instance.request_id)
        self.cmd_container_execution += self.parse_container_environment_variable("INSTANCE_IP", 
                                                                                  socket.gethostbyname(socket.gethostname()))        
        self.cmd_container_execution += self.get_user_defined_variables()
        self.cmd_container_execution += self.get_iam_credentials()        
        self.cmd_container_execution += self.get_input_file()
        self.cmd_container_execution += self.get_output_dir()
        self.cmd_container_execution += self.get_extra_payload_path()
        self.cmd_container_execution += self.get_lambda_output_variable()
       
    def parse_container_environment_variable(self, key, value):
        var = []
        if key and value and key != "" and value != "":
            var += ["--env", str(key) + '=' + str(value)]
        return var
        
    def get_user_defined_variables(self):
        result = []
        for key,value in utils.get_user_defined_variables().items():
            result += self.parse_container_environment_variable(key, value)
        if hasattr(self.lambda_instance, "http_params") and self.lambda_instance.http_params:
            for key,value in self.lambda_instance.http_params.items():
                result += self.parse_container_environment_variable(key, value)
        return result

    def get_iam_credentials(self):
        credentials = []
        iam_creds = {'CONT_VAR_AWS_ACCESS_KEY_ID':'AWS_ACCESS_KEY_ID',
                     'CONT_VAR_AWS_SECRET_ACCESS_KEY':'AWS_SECRET_ACCESS_KEY',
                     'CONT_VAR_AWS_SESSION_TOKEN':'AWS_SESSION_TOKEN'}
        # Add IAM credentials
        for key,value in iam_creds.items():
            if not utils.is_variable_in_environment(key):
                credentials += self.parse_container_environment_variable(value, utils.get_environment_variable(value))
        return credentials
    
    def get_input_file(self):
        file = []
        if self.scar_input_file and self.scar_input_file != "":
            file += self.parse_container_environment_variable("SCAR_INPUT_FILE", self.scar_input_file)
        return file
    
    def get_output_dir(self):
        return self.parse_container_environment_variable("SCAR_OUTPUT_DIR", 
                                                         "/tmp/{0}/output".format(self.lambda_instance.request_id))
            
    def get_extra_payload_path(self):
        ppath = []
        if utils.is_variable_in_environment('EXTRA_PAYLOAD'):
            ppath += self.parse_container_environment_variable("EXTRA_PAYLOAD", 
                                                               utils.get_environment_variable("EXTRA_PAYLOAD"))
        return ppath
          
    def get_lambda_output_variable(self):
        out_lambda = []
        if utils.is_variable_in_environment('OUTPUT_LAMBDA'):
            utils.set_environment_variable("OUTPUT_LAMBDA_FILE", "/tmp/{0}/lambda_output".format(self.lambda_instance.request_id))
            out_lambda += self.parse_container_environment_variable("OUTPUT_LAMBDA_FILE", 
                                                                    utils.get_environment_variable("EXTRA_PAYLOAD"))
        return out_lambda      
            
    def launch_udocker_container(self):
        remaining_seconds = self.lambda_instance.get_invocation_remaining_seconds()
        logger.info("Executing udocker container. Timeout set to {0} seconds".format(remaining_seconds))
        logger.debug("Udocker command: {0}".format(self.cmd_container_execution))
        with subprocess.Popen(self.cmd_container_execution, 
                              stderr=subprocess.STDOUT, 
                              stdout=open(self.container_output_file, "w"), 
                              preexec_fn=os.setsid) as process:
            try:
                process.wait(timeout=remaining_seconds)
            except subprocess.TimeoutExpired:
                logger.info("Stopping process '{0}'".format(process))
                process.kill()
                logger.warning("Container timeout")
                raise
        
        if os.path.isfile(self.container_output_file):
            return utils.read_file(self.container_output_file)
