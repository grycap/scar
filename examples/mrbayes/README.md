# MrBayes Docker Image

Docker image for [MrBayes](http://mrbayes.sourceforge.net/) based on the [ubuntu:14.04](https://hub.docker.com/r/library/ubuntu/tags/14.04/) Docker image.

## Local Usage

Gaining shell access:

```sh
docker run --rm -ti grycap/mrbayes /bin/bash
```

A sample execution can be initiated with:

```sh
docker run --rm -ti grycap/mrbayes /tmp/mrbayes-sample-run.sh
```

## Usage in AWS Lambda via SCAR

You can run this image in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

 ```sh
 scar init -n lambda-mrbayes -i grycap/mrbayes
 ```

2. Execute the Lambda function passing an execution script

 ```sh
 scar run -s examples/mrbayes/mrbayes-sample-run.sh -n lambda-mrbayes
 ```

## Using recursive capabilities in AWS Lambda via SCAR

There are two ways of using a recusive function via SCAR:
* Using the lambda cache capabilities
* Using an associated S3 bucket

The time limit in both examples is set to see the recursive example, if you want to use the default time (i.e. 300s) you should update also the ITERATIONS variable inside the respective scripts.

Also, the output of the scar functions is only the output of the first iteration (if the invocation is not asynchronous). If you want to check the rest of the outputs you can use the 'log' function of SCAR or check the CloudWatch logs using the AWS web page.

### Using the lambda cache capabilities

1. Create the Lambda function

 ```sh
 scar init -n lambda-recursive-mrbayes -s examples/mrbayes/recursive/in-memory/mrbayes-recursive-big.sh -t 120 -r -m 1024 -i grycap/mrbayes
 ```

2. Execute the Lambda function passing an execution script

 ```sh
 scar run -n lambda-recursive-mrbayes
 ```

3. Check the complete log trace of the lambda function

 ```sh
 scar log -n lambda-recursive-mrbayes
 ```

### Using an associated S3 bucket

1. Create the Lambda function

 ```sh
 scar init -n lambda-recursive-mrbayes -es recursive-bucket -s examples/mrbayes/recursive/with-s3/mrbayes-recursive.sh -t 120 -r -m 1024 -i grycap/mrbayes
 ```

2. Execute the Lambda function uploading a file to the 'input/' folder of the s3 bucket

3. Check the complete log trace of the lambda function

 ```sh
 scar log -n lambda-recursive-mrbayes
 ```

