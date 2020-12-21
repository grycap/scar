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
**/batch.yaml
**/lambda.yaml
**/run_helper.sh
**/README.md
**/LICENSE
```

#### Execution

Due to the fact that we included the private files in our image, we have to launch it from a private location.
For the sake of this example, we use the environment where we built the image in the previously steps.
First, we dump the docker image and compress i t with gzip.

`sudo docker save scar-architrave > /tmp/architrave-docker.img`

The image we just dumped should have less than 256MB.
Before launch, check the RAM and timeout set in the SCAR configuration file, this example requires at least 1.2GB RAM and 15 seconds.
The architrave's folder includes an example launch configuration yaml file used to init and run the application on lambda, __lambda.yaml__.
Please modify the env variables needed by the application, uncomment the export of the **INPUT_FILE_PATH** env variable, and set the correct path of the __run_helper.sh__ launch script in the launch configuration file.
This intermediate script launches __run.sh__ (that is found in the Docker image) that actually executes the application on Amazon Lambda or Batch.
With scar installed, we can now create the lambda function using the example yaml file included with this example as a base:

`scar init -f lambda.yaml`

To execute the function simply run:

`scar run -f lambda.yaml`

Depending on the output Amazon S3 bucket/folder you have selected in the __lambda.yaml__ launch configuration, you should find the output files of the application and a __time.log__ file containing the execution log of the application.

### Batch

#### Batch additional packages required on S3

Start a Docker container based on the image of the distribution you use __to run on AWS__ the legacy application (not the distribution __of__ the legacy application).

`docker run -it -v /tmp/deps:/tmp/deps debian:stretch-slim`

In the running container:

```
# determine all of the dependencies needed by the packages we want to install:
apt update && apt install -y apt-rdepends && \
apt-rdepends openssh-server openssh-client iproute2 inotify-tools locales | sed -E -e 's/^\s*Depends:\s*|^\s*PreDepends:\s*|\s*\(.*\)//g' | sort | uniq > /tmp/deps_tmp.lst &&\
apt-get --purge autoremove -y apt-rdepends && \
# filter out already installed packages (since we use the same base distro to get that packages and to run the legacy app)
apt list --installed | sed -E -e 's/\/.*//g' > /tmp/deps_installed.lst && \
grep -F -v -f  /tmp/deps_installed.lst /tmp/deps_tmp.lst > /tmp/deps.lst && \
# download the list of packages, but don't install them
cd /tmp/deps && apt-get download $(cat /tmp/deps.lst) && \
# Create the list of deps in a file; This file is used to download the required deps from an S3 bucket
ls -1 /tmp/deps > /tmp/deps/deps_batch.lst

```

Since __/tmp/deps__ is shared between the host and the container, the downloaded debs can now be added to __deps.tar.gz__ archive and uploaded to an Amazon S3 bucket (defaults to **scar-architrave/batch**).
The same S3 bucket/folder should contain a 7z archive called __private.7z__ that contains the architrave executable, the example(s), and the private/public ssh keys used for communication between the nodes.
If the 7z is protected by a password, set the password via the env variable **PRIVATE_PASSWD** in the __run_helper.sh__ script.
The ssh keys should be named __ssh_host_rsa_key.pub__ for the public key and __ssh_host_rsa_key__ for the private key.


#### Batch execution

Amazon batch execution is based on events.
In the example launch configuration file __batch.yaml__, the **input** section specifies an Amazon S3 bucket/folder that is monitorized for changes.
Please modify the env variables needed by the application and set the correct path of the __run_helper.sh__ launch script in the launch configuration file.
Set the Docker repo/image in __batch.yaml__.

There are two modes to execute on batch: single node or parallel multinode.
For the former case, be sure that **functions.aws.batch.multi_node_parallel.enabled** to false, and uncomment the export of **AWS_BATCH_JOB_NUM_NODES**, **AWS_BATCH_JOB_NODE_INDEX**, and **AWS_BATCH_JOB_MAIN_NODE_INDEX** in the __run_helper.sh__.
For the latter execution mode, enable the variable in __batch.yaml__ and leave the three env variables commented out.

Once everything is set, use SCAR to init the deployment:

`scar init -f batch.yaml`

Nest, start the execution by uploading the customized __run_helper.sh__ script to S3 (using the default S3 bucket ):

`aws s3 cp run_helper.sh s3://scar-architrave/input`

This script gets executed by __run_batch.sh__.
