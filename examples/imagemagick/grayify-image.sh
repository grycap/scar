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
# 1. An image uploaded to the input folder of the S3 bucket will be made available 
# for the container in /tmp/$REQUEST_ID/input. The path to the file is in $INPUT_FILE_PATH
# 2. The image will be converted to grayscale using ImageMagick
# 3. The output image will be stored /tmp/$REQUEST_ID/output, and will be
#    automatically uploaded by the Lambda function to the output folder of the S3 bucket.
#    

echo "SCRIPT: Invoked Image Grayifier. File available in $INPUT_FILE_PATH"
FILE_NAME=`basename $INPUT_FILE_PATH`
OUTPUT_FILE=$TMP_OUTPUT_DIR/$FILE_NAME

echo "SCRIPT: Converting input image file $INPUT_FILE_PATH to grayscale to output file $OUTPUT_FILE"
convert $INPUT_FILE_PATH -type Grayscale $OUTPUT_FILE
