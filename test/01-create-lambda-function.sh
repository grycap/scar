#! /bin/bash

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

LAMBDA_ROLE_ARN="arn:aws:iam::974349055189:role/lambda-s3-execution-role"
PROFILE="alucloud00"
TIMEOUT=200
MEMORY=256

aws lambda create-function \
--region us-east-1 \
--function-name scarsupervisor  \
--zip-file fileb://`pwd`/scarsupervisor.zip \
--role ${LAMBDA_ROLE_ARN}  \
--handler scarsupervisor.lambda_handler \
--runtime python2.7 \
--profile ${PROFILE} \
--timeout ${TIMEOUT} \
--description 'SCAR supervisor' \
--memory-size ${MEMORY}