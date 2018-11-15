#!/bin/bash

RESULT="$SCAR_OUTPUT_DIR/result.out"
OUTPUT_IMAGE="$SCAR_OUTPUT_DIR/image-result"

echo "SCRIPT: Analyzing file '$SCAR_INPUT_FILE', saving the result in '$RESULT' and the output image in '$OUTPUT_IMAGE.png'"

cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $SCAR_INPUT_FILE -out $OUTPUT_IMAGE > $RESULT
