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
import traceback

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

def get_global_variables():
    cont_variables = []
    for key in os.environ.keys():
        # Find global variables with the specified prefix
        if re.match("CONT_VAR_.*", key):
            cont_variables.append('--env')
            # Remove global variable prefix
            cont_variables.append(key.replace("CONT_VAR_", "")+'='+os.environ[key])
    return cont_variables

def prepare_output(context):
    stdout = "SCAR: Log group name: " + context.log_group_name + "\n"
    stdout += "SCAR: Log stream name: " + context.log_stream_name + "\n"
    stdout += "---------------------------------------------------------------------------\n"
    return stdout

def create_file(content, path):
    with open(path,"w") as f:
        f.write(content)

def create_event_file(event, context):
    event_file_path = "/tmp/" + context.aws_request_id + "/"
    call(["mkdir", "-p", event_file_path])
    create_file(event, event_file_path+"/event.json")

def lambda_handler(event, context):
    try:
        print("SCAR: Received event: " + json.dumps(event))
        create_event_file(json.dumps(event), context)
        file_retriever = urllib.URLopener()
        prepare_environment(file_retriever)
        prepare_container(os.environ['IMAGE_ID'])
    
        # Create container execution command
        command = [udocker_bin, "--quiet", "run", "-v", "/tmp", "-v", "/dev", "--nosysdirs"]
        # Add global variables (if any)
        global_variables = get_global_variables()
        if global_variables:
            command.extend(global_variables)
    
        # Container running script
        if ('script' in event) and event['script']:
            create_file(event['script'], script)  
            command.extend((name, "/bin/sh", script))
        # Container with args
        elif ('cmd_args' in event) and event['cmd_args']:
            args = map(lambda x: x.encode('ascii'), event['cmd_args'])
            command.append(name)
            command.extend(args)    
        # Only container        
        else:
            command.append(name)
        # Execute script
        call(command, stderr = STDOUT, stdout = open(lambda_output,"w"))
        
        stdout = prepare_output(context)
        stdout += check_output(["cat", lambda_output])
    except Exception:
        stdout = prepare_output(context)
        stdout += "ERROR: Exception launched:\n %s" % traceback.format_exc()
    print stdout    
    return stdout
