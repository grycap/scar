#! /bin/sh

echo "SCRIPT: Splitting video file $SCAR_INPUT_FILE in images and storing them in $SCAR_OUTPUT_DIR. One image taken each second"
ffmpeg -loglevel info -nostats -i $SCAR_INPUT_FILE -q:v 1 -vf fps=1 $SCAR_OUTPUT_DIR/out%03d.jpg < /dev/null