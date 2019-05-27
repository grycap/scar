#!/bin/bash

RESULT="$TMP_OUTPUT_DIR/result.out"
OUTPUT_IMAGE="$TMP_OUTPUT_DIR/image-result"

echo "SCRIPT: Analyzing file '$INPUT_FILE_PATH', saving the result in '$RESULT' and the output image in '$OUTPUT_IMAGE.png'"

cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $INPUT_FILE_PATH -out $OUTPUT_IMAGE > $RESULT