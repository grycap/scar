# SCAR - Serverless Container-aware ARchitectures
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

import urllib
import json
import os
import re
from subprocess import call, check_output, STDOUT

print('Loading function')

udocker_bin="/tmp/udocker/udocker"
lambda_output="/tmp/lambda-stdout.txt"
script = "/tmp/udocker/script.sh"
name = 'lambda_cont'

def prepare_environment(file_retriever):
    # Install udocker in /tmp
    call(["mkdir", "-p", "/tmp/udocker"])
    call(["cp", "/var/task/udocker", udocker_bin])
    call(["chmod", "u+rx", udocker_bin])
    call(["mkdir", "-p", "/tmp/home/.udocker"])

def prepare_container(container_image):
    # Check if the container is already downloaded
    cmd_out = check_output([udocker_bin, "images"])
    if container_image not in cmd_out:
        print("SCAR: Pulling container '" + container_image + "' from dockerhub")
        # If the container doesn't exist
        call([udocker_bin, "pull", container_image])
    else:
        print("SCAR: Container image '" + container_image + "' already available")
    # Download and create container
    cmd_out = check_output([udocker_bin, "ps"])
    if name not in cmd_out:
        print("SCAR: Creating container with name '" + name + "' based on image '" + container_image + "'.")
        call([udocker_bin, "create", "--name="+name, container_image])
        # Set container execution engine to Fakechroot
        call([udocker_bin, "setup", "--execmode=F1", name])
    else:
        print("SCAR: Container '" + name + "' already available")

def create_script(content):
    with open(script,"w") as f:
        f.write(content)

def get_global_variables():
    cont_variables = []
    for key in os.environ.keys():
        # Find global variables with the specified prefix
        if re.match("CONT_VAR_.*", key):
            cont_variables.append('--env')
            # Remove global variable prefix
            cont_variables.append(key.replace("CONT_VAR_", "")+'='+os.environ[key])
    return cont_variables

def lambda_handler(event, context):
    print("SCAR: Received event: " + json.dumps(event, indent=2))
    print("SCAR: Log stream name:", context.log_stream_name)
    print("SCAR: Log group name:",  context.log_group_name)
    file_retriever = urllib.URLopener()
    prepare_environment(file_retriever)
    prepare_container(os.environ['IMAGE_ID'])
    create_script(event['script'])
    
    # Create container execution command
    command = [udocker_bin, "--quiet", "run", "-v", "/tmp", "--nosysdirs"]
    # Add global variables (if any)
    global_variables = get_global_variables()
    if global_variables:
        command.extend(global_variables)
    command.extend((name, "/bin/sh", script))
    
    # Execute script
    call(command, stderr = STDOUT, stdout = open(lambda_output,"w"))

    stdout = check_output(["cat", lambda_output])
    stdout = "SCAR: Log stream name:" + context.log_stream_name + "\nSCAR: Log group name: " + context.log_group_name + "\n" + stdout
    print stdout    
    return stdout
