#!/bin/bash

# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) GRyCAP - I3M - UPV 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

INPUT_DIR="/tmp/$REQUEST_ID/input"
OUTPUT_DIR="/tmp/$REQUEST_ID/output"

mkdir -p ~/mrbayes
cd ~/mrbayes

# Sample configuration file	
cat << EOF > batch1.txt
set autoclose=yes nowarn=yes
execute $OUTPUT_DIR/cynmix.nex
lset nst=6 rates=gamma
mcmc ngen=25000 savebrlens=yes file=$OUTPUT_DIR/cynmix.nex1
quit
EOF


# Sample configuration file with checkpointing
cat << EOF > batch2.txt
set autoclose=yes nowarn=yes
execute $OUTPUT_DIR/cynmix.nex
lset nst=6 rates=gamma
mcmc ngen=25000 savebrlens=yes file=$OUTPUT_DIR/cynmix.nex1 append=yes
quit
EOF

if [ -f "$INPUT_DIR/cynmix.nex1.ckp" ]; then
	echo "RECURSIVE INPUT FOUND"
	mv $INPUT_DIR/* $OUTPUT_DIR/
	/opt/mrbayes/mb < batch2.txt
else
	mv $INPUT_DIR/* $OUTPUT_DIR/
	/opt/mrbayes/mb < batch1.txt
fi
