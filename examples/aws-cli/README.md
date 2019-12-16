# Alpine AWS CLI Docker Image

Docker image for [AWS CLI](https://aws.amazon.com/cli/) based on the [alpine](https://hub.docker.com/_/alpine) Docker image.

## Local Usage

Credentials can be passed to the Docker container through the following environment variables:

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`

Assuming that these variables are already populated on your machine, you would list all your defined lambda functions by issuing the command:

```sh
docker run --rm -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY grycap/aws-cli lambda list-functions
```

Further information is available in the [AWS CLI documentation](https://aws.amazon.com/documentation/cli/).

## Usage in AWS Lambda via SCAR

You can run AWS CLI in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Modify the configuration file `scar-aws-cli.yaml` to include your keys and initialize the lambda function

```sh
scar init -f scar-aws-cli.yaml
```

2. Invoke the Lambda function with the parameters that you want to execute in the aws-cli

```sh
scar run -f scar-aws-cli.yaml lambda list-functions
```