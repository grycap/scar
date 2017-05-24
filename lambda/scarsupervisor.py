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
from subprocess import call, check_output, STDOUT

print('Loading function')

udocker_bin="/tmp/udocker/udocker"
lambda_output="/tmp/lambda-stdout.txt"
script = "/tmp/udocker/script.sh"
name="c7"

def prepare_environment(file_retriever):
    # Install udocker in /tmp
    print check_output(["ls", "-l", "/var/task/"])
    call(["mkdir", "-p", "/tmp/udocker"])
    call(["cp", "/var/task/udocker", udocker_bin])
    call(["chmod", "u+rx", udocker_bin])
    call(["mkdir", "-p", "/tmp/home/.udocker"])

def prepare_container(container_image):
    # Download and create container
    call([udocker_bin, "pull", container_image])
    call([udocker_bin, "create", "--name="+name, container_image])
    # Set container execution engine to Fakechroot
    call([udocker_bin, "setup", "--execmode=F1", name])

def create_script(content):
    with open(script,"w") as f:
        f.write(content)

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    file_retriever = urllib.URLopener()
    prepare_environment(file_retriever)
    prepare_container(os.environ['IMAGE_ID'])
    create_script(event['script'])
    
    # Execute script
    call([udocker_bin, "run", "--rm", "-v", "/tmp", "--nosysdirs", name, "/bin/sh", script], 
          stderr = STDOUT,
          stdout = open(lambda_output,"w"))

    stdout = check_output(["cat", lambda_output])
    print stdout    
    return stdout
