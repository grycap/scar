Local Testing
=============

Testing of the Docker images via udocker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can test locally if the Docker image will be able to run in AWS Lambda by means of udocker (available in the `lambda` directory) and taking into account the following limitations:

* udocker cannot run on macOS. Use a Linux box instead.
* Images based in Alpine will not work.

Procedure for testing:

0. (Optional) Define an alias for easier usage::

    alias udocker=`pwd`/lambda/udocker

#) Pull the image from Docker Hub into udocker::

    udocker pull grycap/cowsay

#) Create the container::

    udocker create --name=ucontainer grycap/cowsay

#) Change the execution mode to Fakechroot::

    udocker setup --execmode=F1 ucontainer

#) Execute the container::

    udocker run ucontainer

#) (Optional) Get a shell into the container::

    udocker run ucontainer /bin/sh

Further information is available in the udocker documentation::

    udocker help