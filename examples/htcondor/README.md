HTCondor Docker Image
=============================

This Docker image is based on the [dscnaf/htcondor-centos](https://hub.docker.com/r/dscnaf/htcondor-centos/), which provides a multi-role HTCondor Docker image.

It has been modified to be able to run it on AWS Lambda using [SCAR](https://github.com/grycap/scar). The modifications are:

* Using `/tmp` as the directory for log, locks and pid files HTCondor
* Removing security configuration in `condor_config`
* Removing the use of `tini`, since it raises an `EBAD` error when attempting to execute the `tcsetpgrp` operation while running on AWS Lambda.

For further information on how to use this Docker image, please refer to the original instructions in [dscnaf/htcondor-centos](https://hub.docker.com/r/dscnaf/htcondor-centos/) and the corresponding GitHub repository: [DS-CNAF/htcondor-docker-centos](https://github.com/DS-CNAF/htcondor-docker-centos).

NOTE: THIS IS STILL UNDER TESTING. USE IT AT YOUR OWN RISK.
