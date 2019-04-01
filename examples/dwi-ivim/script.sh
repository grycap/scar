#!/bin/bash

FILENAME=`basename $INPUT_FILE_PATH .tar.gz`

# Untar the package
tar -zxvf $INPUT_FILE_PATH 

# Get the parameters
PARAMS=`cat $FILENAME/valores_b.txt `
# Get the number of parameters
NPARAMS=`echo $PARAMS | awk '{print NF}'`

# Execute the binary file
/opt/dwi/modeloIVIM $FILENAME/$FILENAME.nii $NPARAMS $PARAMS > $TMP_OUTPUT_DIR/$FILENAME.out
