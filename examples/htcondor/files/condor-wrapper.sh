#!/bin/bash

# Clean up after ourselves
trap "{ /usr/sbin/condor_off -master; exit 0; }" TERM

# SCAR-dependent. Define location of condor_config file
export CONDOR_CONFIG=/tmp/condor_config 

# Boot up HTCondor and wait for it
/usr/sbin/condor_master -f &

PID=$!
wait $PID
