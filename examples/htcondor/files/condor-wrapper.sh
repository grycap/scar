#!/bin/bash

# Clean up after ourselves
trap "{ /usr/sbin/condor_off -master; exit 0; }" TERM

# Boot up HTCondor and wait for it
/usr/sbin/condor_master -f &

PID=$!
wait $PID
