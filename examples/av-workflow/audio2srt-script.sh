#!/bin/bash

echo "SCRIPT: Invoked audio2srt. File available in $INPUT_FILE_PATH"
FILE_NAME=`basename "$INPUT_FILE_PATH"`
FILE_NAME="${FILE_NAME%.*}"
OUTPUT_FILE="$TMP_OUTPUT_DIR/$FILE_NAME"
echo "SCRIPT: Generating subtitles from audio file $INPUT_FILE_PATH to $OUTPUT_FILE"
./audio2srt.py -i "$INPUT_FILE_PATH" -o "$OUTPUT_FILE.srt" -- -lm en-us.lm.bin -hmm en-us
