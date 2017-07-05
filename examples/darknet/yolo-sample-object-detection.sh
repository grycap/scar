#!/bin/bash

OUTPUT_DIR="/tmp/$REQUEST_ID/output"
FILENAME=`basename $SCAR_INPUT_FILE`
OUTPUT_FILE="$OUTPUT_DIR/${FILENAME%.*}.out"
echo "SCRIPT: Analyzing image file $SCAR_INPUT_FILE and saving the output in file $OUTPUT_FILE"

cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $SCAR_INPUT_FILE > $OUTPUT_FILE

