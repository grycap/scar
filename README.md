SCAR - Serverless Container-aware ARchitectures
===============================================

SCAR is a framework to transparently execute containers (e.g. Docker) in serverless platforms (e.g. AWS Lambda) to create ultra-elastic application architectures in the Cloud.

## Approach

SCAR uses the following underlying technologies:

* [udocker](https://github.com/indigo-dc/udocker/): A tool to execute Docker containers in user space.
* [AWS Lambda](https://aws.amazon.com/lambda): A serverless compute service that runs Lambda functions in response to events.

SCAR creates Lambda functions and provides a command-line interface to transparently execute Docker containers in AWS Lambda.

## Configuration

### IAM Role

The Lambda functions require a role in order to acquire the required permissions to access the different AWS services during its execution.

There is a sample policy in the [lambda-execute.role](docs/aws/lambda-execute.role) file. This role should be created beforehand using Amazon IAM.

## Installation

Install the required dependencies:

* [AWS SDK for Python (Boto 3)](https://github.com/boto/boto3) (v1.4.4+ is required)
* [Tabulate](https://pypi.python.org/pypi/tabulate)

You can automatically install them issuing the following command:
```
sudo pip install -r requirements.txt
```

## Licensing
SCAR is licensed under the Apache License, Version 2.0. See
[LICENSE](https://github.com/grycap/scar/blob/master/LICENSE) for the full
license text.