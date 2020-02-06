#!/bin/bash

echo "SCRIPT: Invoked ffmpeg. File available in $INPUT_FILE_PATH"
FILE_NAME=`basename "$INPUT_FILE_PATH"`
FILE_NAME="${FILE_NAME%.*}"
OUTPUT_FILE="$TMP_OUTPUT_DIR/$FILE_NAME"
echo "SCRIPT: Generating subtitles from audio file $INPUT_FILE_PATH to $OUTPUT_FILE"
ffmpeg -i "$INPUT_FILE_PATH" -vn -ar 16000 -ac 1 -acodec pcm_s16le "$OUTPUT_FILE.wav"
if [[ $INPUT_FILE_PATH == *.avi ]]
then
    cp "$INPUT_FILE_PATH" "$OUTPUT_FILE.avi"
else
    ffmpeg -i "$INPUT_FILE_PATH" -f avi -c:v mpeg4 -b:v 4000k -c:a libmp3lame -b:a 320k "$OUTPUT_FILE.avi"
fi
