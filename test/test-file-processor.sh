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

#
# A simple script to illustrate the SCAR programming model:
#
# Files uploaded to the input folder of the S3 bucket will be made available 
# for the container in /tmp/$REQUEST_ID/input 
# Files generated in /tmp/$REQUEST_ID/output will be automatically uploaded to the output 
# folder of the S3 bucket.
#
# In this simple example, the file is just copied to the output folder.

INPUT_DIR="/tmp/$REQUEST_ID/input"
OUTPUT_DIR="/tmp/$REQUEST_ID/output"

echo "SCRIPT: Invoked File Processor. Files available in $INPUT_DIR"
echo "SCRIPT: Creating output directory: $OUTPUT_DIR"
mkdir -p $OUTPUT_DIR
for FILE in $INPUT_DIR/*; do
  echo "SCRIPT: Processing file: $FILE"
  cp $FILE $OUTPUT_DIR
done
echo "SCRIPT: File generated in $OUTPUT_DIR"