Configuration
=============

To use SCAR with AWS you need:

* Valid AWS `IAM <https://aws.amazon.com/iam/>`_ user credentials (Access Key and Secret Key ID) with permissions to deploy Lambda functions.
* An IAM Role for the Lambda function to be authorized to access other AWS services during its execution.

IAM User Credentials
^^^^^^^^^^^^^^^^^^^^

The credentials have to be configured in your ``$HOME/.aws/credentials`` file (as when using `AWS CLI <https://aws.amazon.com/cli/>`_). Check the AWS CLI documentation, specially section `'Configuration and Credential Files' <http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html>`_.

IAM Role
^^^^^^^^

The Lambda functions require an `IAM Role <http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html>`_ in order to acquire the required permissions to access the different AWS services during its execution.

There is a sample policy in the `lambda-execute-role.json <https://github.com/grycap/scar/blob/master/docs/aws/lambda-execute-role.json>`_ file. This IAM Role should be created beforehand. There is further documentation on this topic in the `'Creating IAM roles' <http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html>`_ section of the AWS documentation.

Configuration file
^^^^^^^^^^^^^^^^^^

The first time you execute SCAR a default configuration file is created in the user location: ``$HOME/.scar/scar.cfg``.
As explained above, it is mandatory to set a value for the aws.iam.role property. The rest of the values can be customized to your preferences::

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


The values represent:

* **aws.iam.role**: The `ARN <http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html>`_ of the IAM Role that you just created in the previous section.
* **aws.lambda.region**: The `AWS region <http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html>`_ on which the AWS Lambda function will be created.
* **aws.lambda.time**: Default maximum execution time of the AWS Lambda function [1]_.
* **aws.lambda.memory**: Default maximum memory allocated to the AWS Lambda function [1]_.
* **aws.lambda.description**: Default description of the AWS Lambda function [1]_.
* **aws.lambda.timeout_threshold:** Default time used to postprocess the container output. Also used to avoid getting timeout error in case the execution of the container takes more time than the lambda_time [1]_.
* **aws.cloudwatch.log_retention_policy_in_days**: Default time (in days) used to store the logs in cloudwatch. Any log older than this parameter will be deleted.

.. [1] These parameters can also be set or updated with the SCAR CLI