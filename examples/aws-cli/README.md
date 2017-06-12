# Alpine-less AWS CLI Docker Image

Docker image for [AWS CLI](https://aws.amazon.com/cli/) based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) Docker image.

## Local Usage

Credentials can be passed through the following environment variables:

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`

Assuming that these variables are already populated on your machine, you would list all the EC2 instances by issuing the command:

```sh
docker run --rm -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY grycap/aws-cli ec2 describe-instances
```

Further information is available in the [AWS CLI documentation](https://aws.amazon.com/documentation/cli/).

## Usage in AWS Lambda via SCAR

You can run AWS CLI in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -n lambda-aws-cli grycap/aws-cli
```

2. Execute the Lambda function

```sh
scar run -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY lambda-aws-cli ec2 describe-instances
```

You have the AWS CLI running on AWS Lambda.