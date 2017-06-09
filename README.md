SCAR - Serverless Container-aware ARchitectures
===============================================

SCAR is a framework to transparently execute containers (e.g. Docker) in serverless platforms (e.g. AWS Lambda) to create ultra-elastic application architectures in the Cloud.

## Approach

SCAR provides a command-line interface to create a Lambda function to execute a container out of a Docker image stored in [Docker Hub](https://hub.docker.com/). Each invocation of the Lambda function will result in the execution of such a container (optionally executing a shell-script inside the container for further versatility).

 The following underlying technologies are employed:

* [udocker](https://github.com/indigo-dc/udocker/): A tool to execute Docker containers in user space.
  * The [Fakechroot](https://github.com/dex4er/fakechroot/wiki) execution mode of udocker is employed, since Docker containers cannot be natively run on AWS Lambda. Isolation is provided by the boundary of the Lambda function itself.
* [AWS Lambda](https://aws.amazon.com/lambda): A serverless compute service that runs Lambda functions in response to events.


## Limitations

* The Docker container must fit within the current [AWS Lambda limits](http://docs.aws.amazon.com/lambda/latest/dg/limits.html):
  * Uncompressed Docker image under 512 MB.
  * Maximum execution time of 300 seconds (5 minutes).
* The following Docker images cannot be currently used:
  * Those based on Alpine Linux (due to the use of MUSL instead of GLIBC, which is not supported by Fakechroot).
* Installation of packages in the user-defined script (i.e. using `yum`, `apt-get`, etc.) is currently not possible.
  

## Configuration

You need:
 * Valid AWS [IAM](https://aws.amazon.com/iam/) user credentials (Access Key and Secret Key ID) with permissions to deploy Lambda functions.
   
* An IAM Role for the Lambda function be be authorized to access other AWS services during its execution.

### IAM User Credentials

 The credentials have to be configured in your ```$HOME/.aws/credentials``` file (as when using [AWS CLI](https://aws.amazon.com/cli/)). Check the AWS CLI documentation, specially section ["Configuration and Credential Files"](http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html).

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

You can automatically install the dependencies by issuing the following command:
```
sudo pip install -r requirements.txt
```

3. (Optional) Define an alias for increased usability:
```
cd scar 
alias scar=`pwd`/scar.py
```

## Basic Usage

1. Create a Lambda function to execute a container (out of a Docker image that is stored in Docker Hub).

In these examples the [grycap/cowsay](https://hub.docker.com/r/grycap/cowsay/) Docker image in Docker Hub will be employed:
```
scar init -n lambda-docker-cowsay -m 128 -t 300 grycap/cowsay
```
Notice that the memory and time limits for the Lambda function can be specified in the command-line. Upon first execution, the file `$HOME/.scar/scar.cfg` is created with default values for the memory and timeout, among other features. The command-line values always take precedence over the values in the configuration file.

Further information about the command-line arguments is available in the help:
```
scar --help
```
 
2. Execute the Lambda function

```
scar run lambda-docker-cowsay
```
The first invocation to the Lambda function will pull the Docker image from Docker Hub so it will take considerably longer than the subsequent invocations, which will most certainly reuse the existing Docker image, stored in ```/tmp```.

3. Access the logs

The logs are stored in CloudWatch with a default retention policy of 30 days.  The logs for a specific invocation a Lambda function can be obtained as follows:
```
scar log -ri <Request-Id> <Log-Group-Name> 'Log-Stream-Name' 
```
These values are shown in the output when executing `scar run`. Do not forget to use the single quotes, as indicated in the example, to avoid unwanted shell expansions.

4. Remove the Lambda function

You can remove the Lambda function together with the logs generated in CloudWatch by:
```
scar rm lambda-docker-cowsay
```

## Advanced Usage

### Executing a shell-script
You can execute the Lambda function and specify a shell-script locally available in your machine to be executed within the container.
```
scar run -s test/test-cowsay.sh lambda-docker-cowsay
```
The shell-script can be changed in each different execution of the Lambda function.

### Passing Environment Variables

You can specify environment variables to the run command which will be in turn passed to the executed Docker container and made available to your shell-script:
```
scar run -e TEST1=45 -e TEST2=69 -s test/test-global-vars.sh lambda-docker-cowsay
```

### Executing Applications

Applications available in the Docker image can be directly executed:
```
 scar run lambda-docker-cowsay /usr/games/fortune
 ```

### Passing Arguments

You can also supply arguments which will be passed to the command executed in the Docker container:
```
scar run lambda-docker-cowsay /usr/bin/perl /usr/games/cowsay Hello World
```
Note that since cowsay is a Perl script you will have to prepend it with the location of the Perl interpreter (in the Docker container).

### Obtaining a JSON Output

For easier scripting, a JSON output can be obtained by including the `--json` or the `-v` (even more verbose output) flags.
```
scar run --json lambda-docker-cowsay
```

### Local Testing of the Docker images via udocker

You can test locally if the Docker image will be able to run in AWS Lambda by means of udocker (available in the `lambda` directory) and taking into account the following limitations:

 * udocker cannot run on macOS. Use a Linux box instead.
 * Images based in Alpine will not work.
 
 Procedure for testing:

0. (Optional) Define an alias for easier usage
```
alias udocker=`pwd`/lambda/udocker
```
1. Pull the image from Docker Hub into udocker
```
udocker pull grycap/cowsay
```
2. Create the container
```
udocker create --name=my-container grycap/cowsay
```
3. Change the execution mode to Fakechroot
```
udocker setup --execmode=F1 my-container
```
4. Execute the container
```
udocker run my-container
```
5. (Optional) Get a shell into the container
```
udocker run my-container /bin/sh
```
Further information is available in the udocker documentation:
```
udocker help
```

### Local Testing of the Lambda functions with emulambda

For easier debugging of the Lambda functions, [emulambda](https://github.com/fugue/emulambda) can be employed to locally execute them.

1. Install emulambda
2. Execute a sample local test
```
sh test/emulambda/run-local-test.sh
```   
This test locally executes the ubuntu:16.04 image in DockerHub via udocker executing a simple shell-script.

## Licensing
SCAR is licensed under the Apache License, Version 2.0. See
[LICENSE](https://github.com/grycap/scar/blob/master/LICENSE) for the full
license text.

## Acknowledgements
* [udocker](https://github.com/indigo-dc/udocker)