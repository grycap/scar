Approach
========

SCAR provides a command-line interface to create a Lambda function to execute a container out of a Docker image stored in `Docker Hub <https://hub.docker.com/>`_. Each invocation of the Lambda function will result in the execution of such a container (optionally executing a shell-script inside the container for further versatility).

The following underlying technologies are employed:

- `udocker <https://github.com/indigo-dc/udocker/>`_: A tool to execute Docker containers in user space.

  - The `Fakechroot <https://github.com/dex4er/fakechroot/wiki>`_ execution mode of udocker is employed, since Docker containers cannot be natively run on AWS Lambda. Isolation is provided by the boundary of the Lambda function itself.

- `AWS Lambda <https://aws.amazon.com/lambda>`_: A serverless compute service that runs Lambda functions in response to events.

SCAR can optionally define a trigger so that the Lambda function is executed whenever a file is uploaded to an Amazon S3 bucket. This file is automatically made available to the underlying Docker container run on AWS Lambda so that an user-provided shell-script can process the file. See the :doc:`/prog_model` for more details.