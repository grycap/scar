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

The following policy can be used in the IAM Role::

  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "logs:*"
        ],
        "Resource": "arn:aws:logs:*:*:*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject"
        ],
        "Resource": "arn:aws:s3:::*"
      }
    ]
  }

This IAM Role should be created beforehand. There is further documentation on this topic in the `'Creating IAM roles' <http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html>`_ section of the AWS documentation.

Configuration file
^^^^^^^^^^^^^^^^^^

The first time you execute SCAR a default configuration file is created in the user location: ``$HOME/.scar/scar.cfg``.
As explained above, it is mandatory to set a value for the ``aws.iam.role`` property to use the Lambda service.
If you also want to use the Batch service you have to update the values of the ``aws.batch.compute_resources.security_group_ids``, and ``aws.batch.compute_resources.subnets``.
An explanation of all the configurable properties can be found in the `example configuration file <https://github.com/grycap/scar/blob/master/fdl-example.yaml>`_.
Below is the complete default configuration file ::
  {
    "scar": {
      "config_version": "1.0.9"
    },
    "aws": {
      "iam": {
        "boto_profile": "default",
        "role": ""
      },
      "lambda": {
        "boto_profile": "default",
        "region": "us-east-1",
        "execution_mode": "lambda",
        "timeout": 300,
        "memory": 512,
        "description": "Automatically generated lambda function",
        "runtime": "python3.7",
        "layers": [],
        "invocation_type": "RequestResponse",
        "asynchronous": false,
        "log_type": "Tail",
        "log_level": "INFO",
        "environment": {
          "Variables": {
            "UDOCKER_BIN": "/opt/udocker/bin/",
            "UDOCKER_LIB": "/opt/udocker/lib/",
            "UDOCKER_DIR": "/tmp/shared/udocker",
            "UDOCKER_EXEC": "/opt/udocker/udocker.py"
          }
        },
        "deployment": {
          "max_payload_size": 52428800,
          "max_s3_payload_size": 262144000
        },
        "container": {
          "environment": {
            "Variables": {}
          },
          "timeout_threshold": 10
        },
        "supervisor": {
          "version": "1.2.0-rc4",
          "layer_name": "faas-supervisor",
          "license_info": "Apache 2.0"
        }
      },
      "s3": {
        "boto_profile": "default",
        "region": "us-east-1",
        "event": {
          "Records": [
            {
              "eventSource": "aws:s3",
              "s3": {
                "bucket": {
                  "name": "{bucket_name}",
                  "arn": "arn:aws:s3:::{bucket_name}"
                },
                "object": {
                  "key": "{file_key}"
                }
              }
            }
          ]
        }
      },
      "api_gateway": {
        "boto_profile": "default",
        "region": "us-east-1",
        "endpoint": "https://{api_id}.execute-api.{api_region}.amazonaws.com/{stage_name}/launch",
        "request_parameters": {
          "integration.request.header.X-Amz-Invocation-Type": "method.request.header.X-Amz-Invocation-Type"
        },
        "http_method": "ANY",
        "method": {
          "authorizationType": "NONE",
          "requestParameters": {
            "method.request.header.X-Amz-Invocation-Type": false
          }
        },
        "integration": {
          "type": "AWS_PROXY",
          "integrationHttpMethod": "POST",
          "uri": "arn:aws:apigateway:{api_region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{lambda_region}:{account_id}:function:{function_name}/invocations",
          "requestParameters": {
            "integration.request.header.X-Amz-Invocation-Type": "method.request.header.X-Amz-Invocation-Type"
          }
        },
        "path_part": "{proxy+}",
        "stage_name": "scar",
        "service_id": "apigateway.amazonaws.com",
        "source_arn_testing": "arn:aws:execute-api:{api_region}:{account_id}:{api_id}/*",
        "source_arn_invocation": "arn:aws:execute-api:{api_region}:{account_id}:{api_id}/{stage_name}/ANY"
      },
      "cloudwatch": {
        "boto_profile": "default",
        "region": "us-east-1",
        "log_retention_policy_in_days": 30
      },
      "batch": {
        "boto_profile": "default",
        "region": "us-east-1",
        "vcpus": 1,
        "memory": 1024,
        "enable_gpu": false,
        "state": "ENABLED",
        "type": "MANAGED",
        "environment": {
          "Variables": {}
        },
        "compute_resources": {
          "security_group_ids": [],
          "type": "EC2",
          "desired_v_cpus": 0,
          "min_v_cpus": 0,
          "max_v_cpus": 2,
          "subnets": [],
          "instance_types": [
            "m3.medium"
          ],
          "launch_template_name": "faas-supervisor",
          "instance_role": "arn:aws:iam::{account_id}:instance-profile/ecsInstanceRole"
        },
        "service_role": "arn:aws:iam::{account_id}:role/service-role/AWSBatchServiceRole"
      }
    }
  }