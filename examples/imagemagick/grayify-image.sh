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
# 1. Images uploaded to the input folder of the S3 bucket will be made available 
# for the container in /tmp/$REQUEST_ID/input 
# 2. Images will be converted using ImageMagick
# 3. Images generated in /tmp/$REQUEST_ID/output will be automatically uploaded to the output 
# folder of the S3 bucket.
#

INPUT_DIR="/tmp/$REQUEST_ID/input"
OUTPUT_DIR="/tmp/$REQUEST_ID/output"

echo "SCRIPT: Creating output directory: $OUTPUT_DIR"
mkdir -p $OUTPUT_DIR
echo "SCRIPT: Invoked Image Grayifier. Files(s) available in $INPUT_DIR"
for INPUT_FILE in $INPUT_DIR/*; do
   FILENAME=`basename $INPUT_FILE`
   OUTPUT_FILE=$OUTPUT_DIR/$FILENAME
  echo "SCRIPT: Converting input image file $INPUT_FILE to grayscale to output file $OUTPUT_FILE"
  convert $INPUT_FILE -type Grayscale $OUTPUT_FILE
done