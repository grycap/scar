#!/bin/bash

OUTPUT_DIR="/tmp/$REQUEST_ID/output"
FILENAME=`basename $SCAR_INPUT_FILE`
FILENAME_NO_EXTENSION=${FILENAME%.*}

RESULT="$OUTPUT_DIR/$FILENAME_NO_EXTENSION.out"
OUTPUT_IMAGE=$FILENAME_NO_EXTENSION-detected

echo "SCRIPT: Analyzing image file $SCAR_INPUT_FILE and saving the output in file $RESULT and image $OUTPUT_IMAGE"

cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $SCAR_INPUT_FILE -out $OUTPUT_IMAGE > $RESULT

mv $OUTPUT_IMAGE.png $OUTPUT_DIR/$OUTPUT_IMAGE.png
