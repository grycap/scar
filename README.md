SCAR - Serverless Container-aware ARchitectures
===============================================

SCAR is a framework to transparently execute containers (e.g. Docker) in serverless platforms (e.g. AWS Lambda) to create ultra-elastic application architectures in the Cloud.

## Approach

SCAR provides a command-line interface to create a Lambda function to execute Docker container out of an image stored in [Docker Hub](https://hub.docker.com/). Each invocation of the Lambda function will result in the execution of such a container (optionally executing a shell-script inside the container for further versatility).

 The following underlying technologies are employed:

* [udocker](https://github.com/indigo-dc/udocker/): A tool to execute Docker containers in user space.
  * The [Fakechroot](https://github.com/dex4er/fakechroot/wiki) execution mode of udocker is employed.
* [AWS Lambda](https://aws.amazon.com/lambda): A serverless compute service that runs Lambda functions in response to events.


## Limitations

* The Docker container must fit within the current [AWS Lambda limits](http://docs.aws.amazon.com/lambda/latest/dg/limits.html):
  * Uncompressed Docker image under 512 MB.
  * Maximum execution time of 300 seconds (5 minutes)
* The following Docker images cannot be currently used:
  * alpine/*
* Installation of packages in the user-defined script is currently not possible.
  

## Configuration

You need:
 * Valid AWS [IAM](https://aws.amazon.com/iam/) user credentials (Access Key and Secret Key ID) with permissions to deploy Lambda functions.
   
* An IAM Role for the Lambda function be be authorized to access other AWS services during its execution.

### IAM User Credentials

 The credentials have to be configured in your ```$HOME/.aws/credentials``` file (as when using [AWS CLI](https://aws.amazon.com/cli/). Check the AWS CLI documentation, specially section ["Configuration and Credential Files"](http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html).

### IAM Role

The Lambda functions require a role in order to acquire the required permissions to access the different AWS services during its execution.

There is a sample policy in the [lambda-execute-role.json](docs/aws/lambda-execute-role.json) file. This role should be created beforehand. There is further documentation on this topic in the ["Creating IAM roles"](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html) section of the AWS documentation. 

## Installation

1. Clone the GitHub repository:
```
git clone https://github.com/grycap/scar.git
```
2. Install the required dependencies:

* [AWS SDK for Python (Boto 3)](https://github.com/boto/boto3) (v1.4.4+ is required)
* [Tabulate](https://pypi.python.org/pypi/tabulate)

  You can automatically install them issuing the following command:
```
sudo pip install -r requirements.txt
```

3. (Optional) Define an alias for increased usability
```
cd scar 
alias scar=`pwd`/scar.py
```

## Usage

1. Create a Lambda function to execute a Docker container (whose image is stored in Docker Hub)
```
scar init -n lambda-docker-cowsay -m 128 -t 300 chuanwen/cowsay
```
Notice that the memory and time limits for the Lambda function can be specified. Further information is available querying the help:
```
scar --help
```

2. Execute the Lambda function (to trigger the execution of the Docker container) and pass a script to be executed within the container.
```
scar run -p test/test-cowsay.sh lambda-docker-cowsay
```
Note that the first invocation to the Lambda function will trigger the pulling of the Docker image from Docker Hub so it will take considerably longer than the subsequent invocations, which will most certainly reuse the existing Docker image, stored in ```/tmp```.

The shell-script can be changed in each different execution of the Lambda function.

### Passing Environment Variables

You can pass environment variables to the Lambda function which will be in turn passed to the executed Docker container and made available to your shell-script:
```
scar run -e TEST1=45 -e TEST2=69 -p test/test-global-vars.sh lambda-docker-cowsay
```

## Licensing
SCAR is licensed under the Apache License, Version 2.0. See
[LICENSE](https://github.com/grycap/scar/blob/master/LICENSE) for the full
license text.