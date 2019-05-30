#!/bin/bash

OUT_FOLDER="/tmp/output"
mkdir -p $OUT_FOLDER

cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $INPUT_FILE_PATH -out $OUT_FOLDER/image 2>/dev/null 1>$OUT_FOLDER/result

tar -zcf $TMP_OUTPUT_DIR/result.tar.gz $OUT_FOLDER 2>/dev/null
cat $TMP_OUTPUT_DIR/result.tar.gz
