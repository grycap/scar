#!/bin/bash

mkdir -p $TMP_OUTPUT_DIR/output
cd /opt/darknet
./darknet detect cfg/yolo.cfg yolo.weights $INPUT_FILE_PATH -out $TMP_OUTPUT_DIR/output/image 2>/dev/null 1>$TMP_OUTPUT_DIR/output/result
tar -zcf $TMP_OUTPUT_DIR/result.tar.gz $TMP_OUTPUT_DIR/output 2>/dev/null
cat $TMP_OUTPUT_DIR/result.tar.gz
