.. highlight:: none

AWS Batch Integration
=======================

Set up your configuration file
------------------------------

To be able to use the batch environment, first you need to set up your configuration file, located in `~/.scar/scar.cfg`

The new variables added to the scar config file are::

  "batch": {
    "state": "ENABLED",
    "type": "MANAGED",
    "security_group_ids": [""],
    "comp_type": "EC2",
    "desired_v_cpus": 0,
    "min_v_cpus": 0,
    "max_v_cpus": 2,
    "subnets": [""],
    "instance_types": ["m3.medium"]
  }
  
To be able to deploy EC2 instances you have to fill the `security_group_ids` and the `subnets` variables.
The `subnets` variable defines the VPC subnets into which the compute resources are launched.
The `security_group_ids` defines the EC2 security group that is associated with the instances launched in the compute environment.
More info about the variables and the different values that can be assigned can be found in the `AWS API Documentation <https://docs.aws.amazon.com/batch/latest/APIReference/API_CreateComputeEnvironment.html>`_.


Define a job to be executed in batch
------------------------------------

SCAR allows to transparently integrate the executions of jobs through `AWS Batch <https://aws.amazon.com/batch/>`_. To enable this functionality you only need to set the execution mode of the Lambda function to one of the two available used to create batch jobs ('lambda-batch' or 'batch') and SCAR will take care of the integration process (before using this feature make sure you have the correct rights set in your aws account).

The following configuration file defines a Lambda function that creates an AWS Batch job (the required script can be found in `mrbayes-sample-run.sh <https://raw.githubusercontent.com/grycap/scar/master/examples/mrbayes/mrbayes-sample-run.sh>`_)::

  cat >> scar-mrbayes-batch.yaml << EOF
  functions:
    scar-mrbayes-batch:
      image: grycap/mrbayes
      init_script: mrbayes-sample-run.sh
      execution_mode: batch
      s3:
        input_bucket: scar-mrbayes
      environment:
        ITERATIONS: "10000"          
  EOF

  scar init -f scar-mrbayes-batch.yaml
 
Combine AWS Lambda and AWS Batch executions
-------------------------------------------
As explained in the section :doc:`/prog_model`, if you define an output bucket as the input bucket of another function, a workflow can be created.
By doing this, AWS Batch and AWS Lambda executions can be combined through S3 events.

An example of this execution can be found in the `video process example <https://github.com/grycap/scar/tree/master/examples/video-process>`_.

Limits
------
When defining an AWS Batch job have in mind that the `AWS Batch service <https://docs.aws.amazon.com/batch/latest/userguide/service_limits.html>`_ has some limits that are lower than the `Lambda service <https://docs.aws.amazon.com/lambda/latest/dg/limits.html>`_.

For example, the Batch Job definition size is limited to 24KB and the invocation payload in Lambda is limited to 6MB in synchronous calls and 128KB in asynchronous calls.

To create the AWS Batch job, the Lambda function defines a Job with the payload content included, and sometimes (i.e. when the script passed as payload is greater than 24KB) the Batch Job definition can fail.

The payload limit can be avoided by redefining the script used and passing the large payload files using other service (e.g S3 or some bash command like 'wget' or 'curl' to download the information in execution time).

Also, AWS Batch does not allow to override the container entrypoint so containers with an entrypoint defined can not execute an user script.
