# architrave
Running a commercial app in a Docker container on Lambda and Batch

## Building the containers

Due to the differences between Amazon Batch and Lambda and our choice to have one Dockerfile for both, there are some things one has to take into account when running the containers with SCAR.

### Lambda

We included all necessary operations in the Dockerfile, therefore leaving the runtime execution populated only with the application execution itself.
The Docker image doesn't have to be public, we can build it locally.

```
# The base dir is the root context for Docker
# We assume that you cloned this repo in the BASE_DIR
export BASE_DIR=/tmp
# The base dir with the private bits; It must be a child of BASE_DIR
export ADD_PRIVATE_BASE_DIR=architrave

docker build --build-arg ADD_BASE_DIR_ARCHITRAVE=scar/examples/architrave --build-arg ADD_PRIVATE_BASE_DIR="$ADD_PRIVATE_BASE_DIR" -f "$BASE_DIR/scar/examples/architrave/Dockerfile" --label architrave -t architrave "$BASE_DIR"
```

Take into account that the input files  must be located in the __ADD_PRIVATE_BASE_DIR__ directory.
e.g. if you have something like `$BASE_DIR/$ADD_PRIVATE_BASE_DIR/examples/example_input.file`, then you the example input ends up on the following path: `/opt/examples/example_input.file`

If you want to run the container locally before launching it on Amazon Lambda, you can use the following:

```
# This is the path inside the container where the binary can be found
# it is the relative path of ADD_PRIVATE_BASE_DIR without the root
# e.g. for architrave/path/path2/execute_me (where ADD_PRIVATE_BASE_DIR=architrave) <exec> is  path/path2/execute_me
export APP_BIN=/opt/<exec>
# The full list of params needed for the app, don't forget the (double) quotes when there are spaces
export APP_PARAMS=<app params>

# Mount the results dir you specify in the APP_PARAMS env variable to <path out dir container>
docker run -d -e EXEC_TYPE=lambda -e APP_BIN="$APP_BIN" -e APP_PARAMS="$APP_PARAMS" --name architrave_local -v /tmp/architrave-result:/<path out dir container> architrave:latest
```

#### Build context

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

### Batch

#### Batch additional required packages on S3

Start a Docker container based on the image of the distribution you use __to run on AWS__ the legacy application (not the distribution __of__ the legacy application).

`docker run -it -v /tmp/deps:/tmp/deps debian:stretch-slim`

In the running container:

```
# determine all of the dependencies needed by the packages we want to install:
apt update && apt install -y apt-rdepends && \
apt-rdepends openssh-server openssh-client iproute2 inotify-tools | sed -E -e 's/^\s*Depends:\s*|^\s*PreDepends:\s*|\s*\(.*\)//g' | sort | uniq > /tmp/deps_tmp.lst &&\
apt-get --purge autoremove -y apt-rdepends && \
# filter out already installed packages (since we use the same base distro to get that packages and to run the legacy app)
apt list --installed | sed -E -e 's/\/.*//g' > /tmp/deps_installed.lst && \
grep -F -v -f  /tmp/deps_installed.lst /tmp/deps_tmp.lst > /tmp/deps.lst && \
# download the list of packages, but don't install them
cd /tmp/deps && apt-get download $(cat /tmp/deps.lst) && \
# Create the list of deps in a file; This file is used to download the required deps from an S3 bucket
ls -1 /tmp/deps > /tmp/deps/deps_batch.lst
```
