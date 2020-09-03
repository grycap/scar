# architrave
Running a commercial app in a Docker container on Lambda and Batch

## Building the containers

Due to the differences between Amazon Batch and Lambda and our choice to have one Dockerfile for both, there are some things one has to take into account when running the containers with SCAR.

### Lambda

We included all necessary operations in the Dockerfile, therefore leaving the runtime execution populated only with the application execution itself.
The Docker image doesn't have to be public, thus we can build it locally by calling:

`docker build --build-arg ADD_BASE_DIR_ARCHITRAVE=scar/examples/architrave --build-arg  --build-arg ADD_PRIVATE_BASE_DIR=architrave -f /tmp/scar/examples/architrave/Dockerfile --label architrave -t architrave /tmp`

This command implies that __/tmp__ is the base directory for the context.
Herein, there's a folder __architrave__ that contains the private bits of the distribution, in our case the binary of the application and examples.
The same base directory contains the cloned scar repository with the architrave example (the public bits).



You can ignore everything but the private files and those from ##scar/examples/architrave## by creating a `.dockerignore` file in the root of the context with the following content:

```
# Ignore everything
**

# Allow files and directories
!/architrave/**
!/scar/examples/architrave/**

# Ignore unnecessary files inside allowed directories
# This should go after the allowed directories
**/scar-architrave-batch.yaml
**/scar-architrave-lambda.yaml
**/README.md
**/LICENSE
```

### Batch additional required packages on S3

Start a Docker container based on the image of the distribution you use __to run on AWS__ the legacy application (not the distribution __of__ the legacy application).

`docker run -it -v /tmp/deps:/tmp/deps debian:stretch-slim`

In the running container:

```
# determine all of the dependencies needed by the packages we want to install:
apt update && apt install -y apt-rdepends && \
apt-rdepends openssh-server openssh-client iproute2 | sed -E -e 's/^\s*Depends:\s*|^\s*PreDepends:\s*|\s*\(.*\)//g' | sort | uniq > /tmp/deps_tmp.lst &&\
apt-get --purge autoremove -y apt-rdepends && \
# filter out already installed packages (since we use the same base distro to get that packages and to run the legacy app)
apt list --installed | sed -E -e 's/\/.*//g' > /tmp/deps_installed.lst && \
grep -F -v -f  /tmp/deps_installed.lst /tmp/deps_tmp.lst > /tmp/deps.lst && \
# download the list of packages, but don't install them
cd /tmp/deps && apt-get download $(cat /tmp/deps.lst) && \
# Create the list of deps in a file; This file is used to download the required deps from an S3 bucket
ls -1 /tmp/deps > /tmp/deps/deps_batch.lst
```
