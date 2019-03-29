#!/bin/sh

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

# Sample configuration file
cat << EOF > batch.txt
set autoclose=yes nowarn=yes
execute $INPUT_FILE_PATH
lset nst=6 rates=gamma
mcmc ngen=${ITERATIONS:=200} savebrlens=yes file=${INPUT_FILE_PATH}1
mcmc file=${INPUT_FILE_PATH}2
mcmc file=${INPUT_FILE_PATH}3
quit
EOF

mb < batch.txt 
