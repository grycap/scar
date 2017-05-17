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
from subprocess import call, check_output, Popen, PIPE, STDOUT

print('Loading function')

udocker_bin="/tmp/udocker/udocker"
lambda_output="/tmp/lambda_output"
script = "/tmp/udocker/script"
name="c7"

def prepare_environment(file_retriever):
    # Download Udocker
    url = "https://raw.githubusercontent.com/indigo-dc/udocker/udocker-fr/udocker.py"
    call(["mkdir", "-p", "/tmp/udocker"])
    file_retriever.retrieve(url, udocker_bin)
    # Install udocker in /tmp
    call(["chmod", "u+rx", udocker_bin])
    call(["mkdir", "-p", "/tmp/home/.udocker"])
    os.environ["UDOCKER_DIR"] = "/tmp/home/.udocker"

def prepare_container(container_image):
    # Download and create container
    call([udocker_bin, "pull", container_image])
    call([udocker_bin, "create", "--name="+name, container_image])
    # Set container execution engine to Fakechroot
    call([udocker_bin, "setup", "--execmode=F1", name])

def retrieve_script(script_url, file_retriever):
    file_retriever.retrieve(script_url, script)

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    file_retriever = urllib.URLopener()
    prepare_environment(file_retriever)
    prepare_container(event['image'])
    retrieve_script(event['script'], file_retriever)
    # Execute script
    call([udocker_bin, "run", "-v", "/tmp", "--nosysdirs", name, "/bin/bash", script])
    return check_output(["cat", lambda_output])
