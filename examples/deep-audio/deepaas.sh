#!/bin/bash

IMAGE_NAME=`basename $INPUT_FILE_PATH`
SUBPATH=`dirname "$STORAGE_OBJECT_KEY" | cut -d'/' -f3-`
OUTPUT_IMAGE="$TMP_OUTPUT_DIR/$SUBPATH/"

echo "SCRIPT: Invoked deepaas-predict command. File available in $INPUT_FILE_PATH."
deepaas-predict -i $INPUT_FILE_PATH -o $OUTPUT_IMAGE 