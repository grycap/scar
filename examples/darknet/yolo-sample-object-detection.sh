#!/bin/bash

OUTPUT_DIR="/tmp/$REQUEST_ID/output"
FILENAME=`basename $SCAR_INPUT_FILE .jpg`
RESULT="$OUTPUT_DIR/$FILENAME.out"
OUTPUT_IMAGE=$FILENAME-out

echo "SCRIPT: Analyzing file '$SCAR_INPUT_FILE', saving the result in '$RESULT' and the output image in '$OUTPUT_IMAGE.png'"

cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $SCAR_INPUT_FILE -out $OUTPUT_IMAGE > $RESULT

mv $OUTPUT_IMAGE.png $OUTPUT_DIR/
