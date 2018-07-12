#!/bin/bash

FILENAME=`basename $SCAR_INPUT_FILE .tar.gz`

# Untar the package
tar -zxvf $SCAR_INPUT_FILE 

# Get the parameters
PARAMS=`cat $FILENAME/valores_b.txt `
# Get the number of parameters
NPARAMS=`echo $PARAMS | awk '{print NF}'`

# Execute the binary file
/opt/dwi/modeloIVIM $FILENAME/$FILENAME.nii $NPARAMS $PARAMS > $SCAR_OUTPUT_DIR/$FILENAME.out
