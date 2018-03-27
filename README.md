# SCAR - Serverless Container-aware ARchitectures

[![License](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# ![SCAR](scar-logo.png)

SCAR is a framework to transparently execute containers out of Docker images in AWS Lambda, in order to run applications (see examples for [ImageMagick](examples/imagemagick/README.md), [FFmpeg](examples/ffmpeg/README.md) and [AWS CLI](examples/aws-cli/README.md), as well as deep learning frameworks such as [Theano](examples/theano/README.md) and [Darknet](examples/darknet/README.md)) and code in virtually any programming language (see examples for [R](examples/r), [Erlang](examples/erlang) and [Elixir](examples/elixir)) on AWS Lambda.

SCAR provides the benefits of AWS Lambda with the execution environment you decide, provided as a Docker image available in Docker Hub. It is probably the easiest, most convenient approach to run generic applications on AWS Lambda, as well as code in your favourite programming language, not only in those languages supported by AWS Lambda.

SCAR also supports a High Throughput Computing [Programming Model](#programming-model) to create highly-parallel event-driven file-processing serverless applications that execute on customized runtime environments provided by Docker containers run on AWS Lambda. The development of SCAR has been published in the [Future Generation Computer Systems](https://www.journals.elsevier.com/future-generation-computer-systems) scientific journal.

<a name="toc"></a>
**Related resources**:
  [Website](https://grycap.github.io/scar/) |
  [Scientific Paper](http://linkinghub.elsevier.com/retrieve/pii/S0167739X17316485) ([pre-print](http://www.grycap.upv.es/gmolto/publications/preprints/Perez2018scc.pdf)).

**Table of contents**

  * [Approach](#approach)
  * [Limitations](#limitations)
  * [Installation](#installation)
  * [Configuration](#configuration)
  * [Basic Usage](#basicusage)
  * [Advanced Usage](#advancedusage)
      * [Executing a user defined shell script](#executing_a_user_defined_shell_script)
      * [Event-Driven File-Processing Programming Model](#programming-model)
      * [Upload docker images using an S3 bucket](#uploading_docker_images_using_s3)
      * [Upload docker image files using an S3 bucket](#uploading_docker_image_files_using_s3)
      * [Local Testing of the Docker images via udocker](#localtesting)
      * [Local Testing of the Docker images via emulambda](#emulambda)  
  * [Further Information](#furtherinfo)
  * [Acknowledgements](#acknowledgements)
  
<a name="approach"></a>

## Approach

SCAR provides a command-line interface to create a Lambda function to execute a container out of a Docker image stored in [Docker Hub](https://hub.docker.com/). Each invocation of the Lambda function will result in the execution of such a container (optionally executing a shell-script inside the container for further versatility).

 The following underlying technologies are employed:

* [udocker](https://github.com/indigo-dc/udocker/): A tool to execute Docker containers in user space.
  * The [Fakechroot](https://github.com/dex4er/fakechroot/wiki) execution mode of udocker is employed, since Docker containers cannot be natively run on AWS Lambda. Isolation is provided by the boundary of the Lambda function itself.
* [AWS Lambda](https://aws.amazon.com/lambda): A serverless compute service that runs Lambda functions in response to events.

SCAR can optionally define a trigger so that the Lambda function is executed whenever a file is uploaded to an Amazon S3 bucket. This file is automatically made available to the underlying Docker container run on AWS Lambda so that an user-provided shell-script can process the file. See the [Programming Model](#programming-model) for more details.


<a name="limitations"></a>

## Limitations

* The Docker container must fit within the current [AWS Lambda limits](http://docs.aws.amazon.com/lambda/latest/dg/limits.html):
  * Compressed + uncompressed Docker image under 512 MB (udocker needs to download the image before uncompressing it).
  * Maximum execution time of 300 seconds (5 minutes).
* The following Docker images cannot be currently used:
  * Those based on Alpine Linux (due to the use of MUSL instead of GLIBC, which is not supported by Fakechroot).
* Installation of packages in the user-defined script (i.e. using `yum`, `apt-get`, etc.) is currently not possible.

<a name="installation"></a>

## Installation

1. Clone the GitHub repository:

```sh
git clone https://github.com/grycap/scar.git
```

2. Install the required dependencies:

* [zip](https://linux.die.net/man/1/zip) (linux package)
* [AWS SDK for Python (Boto 3)](https://github.com/boto/boto3) (v1.4.4+ is required)
* [Tabulate](https://pypi.python.org/pypi/tabulate)

You can automatically install the python dependencies by issuing the following command:

```sh
sudo pip install -r requirements.txt
```

The zip package can be installed using apt:

```sh
sudo apt install zip
```

3. (Optional) Define an alias for increased usability:

```sh
cd scar
alias scar=`pwd`/scar.py
```

<a name="configuration"></a>

## Configuration

You need:

* Valid AWS [IAM](https://aws.amazon.com/iam/) user credentials (Access Key and Secret Key ID) with permissions to deploy Lambda functions.

* An IAM Role for the Lambda function to be authorized to access other AWS services during its execution.

### IAM User Credentials

 The credentials have to be configured in your ```$HOME/.aws/credentials``` file (as when using [AWS CLI](https://aws.amazon.com/cli/)). Check the AWS CLI documentation, specially section ["Configuration and Credential Files"](http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html).

### IAM Role

The Lambda functions require an [IAM Role](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html) in order to acquire the required permissions to access the different AWS services during its execution.

There is a sample policy in the [lambda-execute-role.json](docs/aws/lambda-execute-role.json) file. This IAM Role should be created beforehand. There is further documentation on this topic in the ["Creating IAM roles"](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html) section of the AWS documentation.

### Configuration file

The first time you execute SCAR a default configuration file is created in the following location: `~/.scar/scar.cfg`.
As explained above, it is mandatory to set a value for the aws.iam.role property. The rest of the values can be customized to your environment:
```sh
{ "aws" : { 
  "iam" : {"role" : ""},
  "lambda" : {
    "region" : "us-east-1",
    "time" : 300,
    "memory" : 512,
    "description" : "Automatically generated lambda function",
    "timeout_threshold" : 10 },
  "cloudwatch" : { "log_retention_policy_in_days" : 30 }}
}
```

The values represent:

* aws.iam.role: The [ARN](http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html) of the IAM Role that you just created in the previous section.
* aws.lambda.region: The [AWS region](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html) on which the AWS Lambda function will be created.
* aws.lambda.time: Default maximum execution time of the AWS Lambda function (can be customized with the `-t` parameter in `scar init`).
* aws.lambda.memory: Default maximum memory allocated to the AWS Lambda function (can be customized with the `-m` parameter in `scar init`).
* aws.lambda.description: Default description of the AWS Lambda function (can be customized with the `-d` parameter in `scar init`).
* aws.lambda.timeout_threshold: Default time used to postprocess the container output. Also used to avoid getting timeout error in case the execution of the container takes more time than the lambda_time (can be customized with the `-tt` parameter in `scar init`).
* aws.cloudwatch.log_retention_policy_in_days: Default time (in days) used to store the logs in cloudwatch. Any log older than this parameter will be deleted.

<a name="basicusage"></a>

## Basic Usage

1. Create a Lambda function to execute a container (out of a Docker image that is stored in Docker Hub).

In these examples the [grycap/cowsay](https://hub.docker.com/r/grycap/cowsay/) Docker image in Docker Hub will be employed:

```sh
scar init -n lambda-docker-cowsay -m 128 -t 300 -i grycap/cowsay
```

Notice that the memory and time limits for the Lambda function can be specified in the command-line. Upon first execution, the file `$HOME/.scar/scar.cfg` is created with default values for the memory and timeout, among other features. The command-line values always take precedence over the values in the configuration file. The default values are 128 MB for the memory (minimize memory) and 300 seconds for the timeout (maximize runtime).

Further information about the command-line arguments is available in the help:

```sh
scar --help
```

2. Execute the Lambda function

```sh
scar run -n lambda-docker-cowsay
```

The first invocation to the Lambda function will pull the Docker image from Docker Hub so it will take considerably longer than the subsequent invocations, which will most certainly reuse the existing Docker image, stored in ```/tmp```.

3. Access the logs

The logs are stored in CloudWatch with a default retention policy of 30 days.  The following command retrieves all the logs related to the Lambda function:

```sh
scar log -n lambda-docker-cowsay
```

If you only want the logs related to a log-stream-name you can use:

```sh
scar log -n lambda-docker-cowsay -ls 'log-stream-name'
```

And finally if you know the request id generated by your invocation, you can specify it to get the logs related:

```sh
scar log lambda-docker-cowsay -ri request-id
```

You can also specify the log stream name to retrieve the values related with the request id, usually this will be faster if the function has generated a lot of log output:

```sh
scar log lambda-docker-cowsay -ls 'log-stream-name' -ri request-id
```

All values are shown in the output when executing `scar log`. Do not forget to use the single quotes, as indicated in the example, to avoid unwanted shell expansions.

4. Remove the Lambda function

You can remove the Lambda function together with the logs generated in CloudWatch by:

```sh
scar rm -n lambda-docker-cowsay
```

<a name="advancedusage"></a>

## Advanced Usage

<a name="executing_a_user_defined_shell_script"></a>
### Executing an user-defined shell-script

You can execute the Lambda function and specify a shell-script locally available in your machine to be executed within the container.

```sh
scar run -s src/test/test-cowsay.sh -n lambda-docker-cowsay
```

The shell-script can be changed in each different execution of the Lambda function.

### Execute a shell-script upon invocation of the Lambda function

A shell-script can be specified when initializing the Lambda function to trigger its execution inside the container on each invocation of the Lambda function. For example:

```sh
scar init -s src/test/test-env.sh -n lambda-test-init-script -i ubuntu:16.04
```

Now whenever this Lambda function is executed, the script will be run in the container:

```sh
scar run -n lambda-test-init-script
```

This can be overridden by speciying a different shell-script when running the Lambda function.

### Passing Environment Variables

You can specify environment variables to the run command which will be in turn passed to the executed Docker container and made available to your shell-script:

```sh
scar run -e TEST1=45 -e TEST2=69 -s src/test/test-global-vars.sh -n lambda-docker-cowsay
```

In particular, the following environment variables are automatically made available to the underlying Docker container:

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`
* `AWS_SESSION_TOKEN`
* `AWS_SECURITY_TOKEN`

This allows a script running in the Docker container to access other AWS services. As an example, see how the AWS CLI is run on AWS Lambda in the [examples/aws-cli](examples/aws-cli) folder.

### Executing Applications

Applications available in the Docker image can be directly executed:

```sh
 scar run -n lambda-docker-cowsay /usr/games/fortune
```

### Passing Arguments

You can also supply arguments which will be passed to the command executed in the Docker container:

```sh
scar run -n lambda-docker-cowsay /usr/bin/perl /usr/games/cowsay Hello World
```

Note that since cowsay is a Perl script you will have to prepend it with the location of the Perl interpreter (in the Docker container).

### Obtaining a JSON Output

For easier scripting, a JSON output can be obtained by including the `--json` or the `-v` (even more verbose output) flags.

```sh
scar run --json -n lambda-docker-cowsay
```

<a id="programming-model"></a>

## Event-Driven File-Processing Programming Model

SCAR supports an event-driven programming model suitable for the execution of highly-parallel file-processing applications that require a customized runtime environment.

The following command:

```sh
scar init -s user-defined-script.sh -n lambda-function-name -es bucket-name -i repo/image:latest
```

Creates a Lambda function to execute the shell-script `user-defined-script.sh` inside a Docker container created out of the `repo/image:latest` Docker image stored in Docker Hub.

The following workflow summarises the programming model, which heavily uses the [convention over configuration](https://en.wikipedia.org/wiki/Convention_over_configuration) pattern:

1. The Amazon S3 bucket `bucket-name` will be created if it does not exist, and the `input` and `output` folders inside.
1. The Lambda function is triggered upon uploading a file into the `input` folder of the `bucket-name` bucket.
1. The Lambda function retrieves the file from the Amazon S3 bucket and makes it available for the shell-script running inside the container in the `/tmp/$REQUEST_ID/input` folder. The `$SCAR_INPUT_FILE` environment variable will point to the location of the input file.
1. The shell-script processes the input file and produces the output (either one or multiple files) in the folder `/tmp/$REQUEST_ID/output`.
1. The output files are automatically uploaded by the Lambda function into the `output` folder of `bucket-name`.

Many instances of the Lambda function may run concurrently and independently, depending on the files to be processed in the S3 bucket. Initial executions of the Lambda may require retrieving the Docker image from Docker Hub but this will be cached for subsequent invocations, thus speeding up the execution process.

For further information, examples of such application are included in the [examples/ffmpeg](examples/ffmpeg) folder, in order to run the [FFmpeg](https://ffmpeg.org/) video codification tool, and in the [examples/imagemagick](examples/imagemagick), in order to run the [ImageMagick](https://www.imagemagick.org) image manipulation tool, both on AWS Lambda.

## More Event-Driven File-Processing thingies

SCAR also supports another way of executing highly-parallel file-processing applications that require a customized runtime environment.

After creating a function with the command:

```sh
scar init -s user-defined-script.sh -n lambda-function-name -i repo/image:latest
```

You can activate the SCAR event launcher using the `run` command like this:

```sh
scar run -es bucket-name -n lambda-function-name
```

This command lists the files in the `input` folder of the specified bucket and sends the required events (one per file) to the lambda function.

The following workflow summarises the programming model, the differences with the main programming model are in bold:

1. **The folder `input` inside the amazon S3 bucket `bucket-name` will be searched for files.**
1. **The Lambda function is triggered once for each file found in the `input` folder. The first execution is of type `request-response` and the rest are `asynchronous`(this is done to ensure the caching and accelerate the execution).**
1. The Lambda function retrieves the file from the Amazon S3 bucket and makes it available for the shell-script running inside the container in the `/tmp/$REQUEST_ID/input` folder. The `$SCAR_INPUT_FILE` environment variable will point to the location of the input file.
1. The shell-script processes the input file and produces the output (either one or multiple files) in the folder `/tmp/$REQUEST_ID/output`.
1. The output files are automatically uploaded by the Lambda function into the `output` folder of `bucket-name`.

<a name="uploading_docker_images_using_s3"></a>
### Upload docker images using an S3 bucket

If you want to save some space inside the lambda function you can deploy a lambda function using an S3 bucket by issuing the following command:

```sh
scar run -db bucket-name -n lambda-function-name -i repo/image
```

The maximum deployment package size allowed by AWS is an unzipped file of 250MB. With this restriction in mind, SCAR downloads the docker image to a temporal folder and creates the udocker file structure needed. 
* If the image information and the container filesystem fit in the 250MB SCAR will upload everything and the lambda function will not need to download or create a container structure thus improving the execution time of the function. This option gives the user the full 500MB of `/tmp/` storage.
* If the container filesystem doesn't fit in the deployment package SCAR will only upload the image information, that is, the layers. Also the lambda function execution time is improved because it doesn't need to dowload the container. In this case udocker needs to create the container filesystem so the first function invocation can be delayed a couple of seconds. This option usually duplicates the available space in the `/tmp/` folder with respect to the SCAR standard initialization.

<a name="uploading_docker_image_files_using_s3"></a>
### Upload docker image files using an S3 bucket

SCAR also allows to upload a saved docker image

```sh
scar run -db bucket-name -n lambda-function-name -if docker_image.tar.gz
```

The behavior of SCAR is the same as in the case above (when uploading an image from docker hub). The image file is unpacked in a temporal folder and the udocker layers and container filesystem are created. Depending on the size of the layers and the filesystem, SCAR will try to upload everything or only the image layers.

<a id="localtesting"></a>

## Local Testing of the Docker images via udocker

You can test locally if the Docker image will be able to run in AWS Lambda by means of udocker (available in the `lambda` directory) and taking into account the following limitations:

* udocker cannot run on macOS. Use a Linux box instead.
* Images based in Alpine will not work.

 Procedure for testing:

0. (Optional) Define an alias for easier usage

```sh
alias udocker=`pwd`/lambda/udocker
```

1. Pull the image from Docker Hub into udocker

```sh
udocker pull grycap/cowsay
```

2. Create the container

```sh
udocker create --name=my-container grycap/cowsay
```

3. Change the execution mode to Fakechroot

```sh
udocker setup --execmode=F1 my-container
```

4. Execute the container

```sh
udocker run my-container
```

5. (Optional) Get a shell into the container

```sh
udocker run my-container /bin/sh
```

Further information is available in the udocker documentation:

```sh
udocker help
```

<a id="emulambda"></a>

## Local Testing of the Lambda functions with emulambda

For easier debugging of the Lambda functions, [emulambda](https://github.com/fugue/emulambda) can be employed to locally execute them.

1. Install emulambda

2. Execute a sample local test

```sh
sh test/emulambda/run-local-test.sh
```

This test locally executes the ubuntu:16.04 image in DockerHub via udocker executing a simple shell-script.

## Licensing

SCAR is licensed under the Apache License, Version 2.0. See
[LICENSE](https://github.com/grycap/scar/blob/master/LICENSE) for the full
license text.

<a id="furtherinfo"></a>
## Further information

There is further information on the architecture of SCAR and use cases in the scientific publication ["Serverless computing for container-based architectures"](http://linkinghub.elsevier.com/retrieve/pii/S0167739X17316485) (pre-print available [here](http://www.grycap.upv.es/gmolto/publications/preprints/Perez2018scc.pdf)), included in the Future Generation Computer Systems journal. Please acknowledge the use of SCAR by including the following cite:

```
A. Pérez, G. Moltó, M. Caballer, and A. Calatrava, “Serverless computing for container-based architectures,” Futur. Gener. Comput. Syst., vol. 83, pp. 50–59, Jun. 2018.
```

<a id="acknowledgements"></a>
## Acknowledgements

* [udocker](https://github.com/indigo-dc/udocker)
