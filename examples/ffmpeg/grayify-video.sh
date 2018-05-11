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
# 1. The video uploaded to the "input" folder of the S3 bucket will be made available 
# for the container in /tmp/$REQUEST_ID/input (path indicated in the $SCAR_INPUT_FILE variable)
# 2. The video will be converted using ffmpeg
# 3. The output video generated in /tmp/$REQUEST_ID/output will be automatically uploaded to the output 
# folder of the S3 bucket.
#

OUTPUT_DIR="/tmp/$REQUEST_ID/output"

echo "SCRIPT: Invoked Video Grayifier. File available in $SCAR_INPUT_FILE"
FILENAME=`basename $SCAR_INPUT_FILE .avi`
OUTPUT_FILE=$OUTPUT_DIR/$FILENAME
echo "SCRIPT: Converting input video file $SCAR_INPUT_FILE to grayscale to output file $OUTPUT_FILE.avi"
ffmpeg -loglevel panic -nostats -i $SCAR_INPUT_FILE -vf format=gray $OUTPUT_FILE.avi < /dev/null
