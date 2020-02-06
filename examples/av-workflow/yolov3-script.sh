#!/bin/bash

echo "SCRIPT: Invoked darknet. File available in $INPUT_FILE_PATH."
FILE_NAME=`basename "$INPUT_FILE_PATH"`
OUTPUT_FILE=$TMP_OUTPUT_DIR/$FILE_NAME
echo "OUTPUT FILE: $OUTPUT_FILE"
cd /opt/darknet
./darknet detector demo cfg/coco.data cfg/yolov3.cfg yolov3.weights "$INPUT_FILE_PATH" -out_filename "$OUTPUT_FILE" -dont_show

