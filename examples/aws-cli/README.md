# Alpine-less AWS CLI Docker Image 

Docker image for [AWS CLI](https://aws.amazon.com/cli/) based on the [python:slim](https://hub.docker.com/r/library/python/tags/slim/) Docker image.

Built to be used by [SCAR](https://github.com/grycap/scar) on AWS Lamda.
Not based on Alpine since it is meant to be executed using [udocker](github.com/indigo-dc/udocker)'s Fakechroot execution mode. 

## Usage

Credentials can be passed through the following environment variables:

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`

Assuming that these variables are already populated on your machine, you would list all the EC2 instances by issuing the command:
```
docker run --rm -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY grycap/aws-cli ec2 describe-instances
```
Further information is available in the [AWS CLI documentation](https://aws.amazon.com/documentation/cli/).