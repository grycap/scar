#! /bin/sh

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

export SCAR_HOME=`pwd`
export IMAGE_ID="ubuntu:16.04"

echo "Configuring environment for local testing of the SCAR Lambda function with emulambda"
SCAR_HOME=`pwd`
echo "Creating symbolic link to udocker in /tmp/udocker"
if [ -L /tmp/udocker ]; then
 ln -s $SCAR_HOME/lambda/udocker /tmp/udocker
fi 

cd $SCAR_HOME/lambda
emulambda scarsupervisor.lambda_handler ../test/emulambda/event.json ../test/emulambda/context.json


