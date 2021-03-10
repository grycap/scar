.. highlight:: none

AWS Batch Integration
=======================

AWS Batch allows to efficiently execute batch computing jobs on AWS by dynamically provisioning the required underlying EC2 instances on which Docker-based jobs are executed.
SCAR allows to transparently integrate the execution of the jobs through `AWS Batch <https://aws.amazon.com/batch/>`_.
Three execution modes are now available in SCAR:

  * `lambda`: This is the default execution mode. All executions will be run on AWS Lambda.
  * `lambda-batch`: Executions will be run on AWS Lambda. If the default timeout is reached, then the execution is automatically delegated to AWS Batch.
  * `batch`: Executions will be automatically diverted to AWS Batch.

This way, you can use AWS Lambda as a highly-scalable cache for burts of short computational jobs while longer executions can be automatically delegated to AWS Batch.
The very same `programming model <https://scar.readthedocs.io/en/latest/prog_model.html>`_ is maintained regardless of the service employed to perform the computation.

Set up your configuration file
------------------------------

To be able to use `AWS Batch <https://aws.amazon.com/batch/>`_, first you need to set up your configuration file, located in `~/.scar/scar.cfg`

The variables responsible for batch configuration are::

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

Since AWS Batch deploys Amazon EC2 instances, the REQUIRED variables are:
 * `security_group_ids`: The EC2 security group that is associated with the instances launched in the compute environment. This allows to define the inbound and outbound network rules in order to allow or disallow TCP/UDP traffic generated from (or received by) the EC2 instance. You can choose the default VPC security group.
 * `subnets`:  The VPC subnet(s) identifier(s) on which the EC2 instances will be deployed. This allows to use multiple Availability Zones for enhanced fault-tolerance.

The remaining variables have default values that should be enough to manage standard batch jobs.
The default `fdl file <https://github.com/grycap/scar/blob/master/fdl-example.yaml>`_ explains briefly the remaining Batch variables and how are they used.

Additional info about the variables and the different values that can be assigned can be found in the `AWS API Documentation <https://docs.aws.amazon.com/batch/latest/APIReference/API_CreateComputeEnvironment.html>`_.

Set up your Batch IAM role
--------------------------

The default IAM role used in the creation of the EC2 for the Batch Compute Environment is **arn:aws:iam::$ACCOUNT_ID:instance-profile/**ecsInstanceRole****. Thus, if you want to provide S3 access to your Batch jobs you have to specify the corresponding policies in the aforementioned role.
If you have a role aleredy configured, you can set it in the configuration file by changin the variable `batch.compute_resources.instance_role`.


Define a job to be executed in batch
------------------------------------

To enable this functionality you only need to set the execution mode of the Lambda function to one of the two available used to create batch jobs ('lambda-batch' or 'batch') and SCAR will take care of the integration process (before using this feature make sure you have the correct rights set in your AWS account).

As an example, the following configuration file defines a Lambda function that creates an AWS Batch job to execute the `plants classification example <https://github.com/grycap/scar/tree/master/examples/plant-classification>`_ (all the required scripts and example files used in this example can be found there)::

  cat >> scar-plants.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-plants
        init_script: bootstrap-plants.sh
        memory: 1024
        execution_mode: batch
        container:
          image: deephdc/deep-oc-plant-classification-theano
        input:
        - storage_provider: s3
          path: scar-plants/input
        output:
        - storage_provider: s3
          path: scar-plants/output
  EOF

You can then create the function::

  scar init -f scar-plants.yaml

Additionally for this example to run you have to upload the execution script to S3::

  scar put -b scar-plants -p plant-classification-run.sh

Once uploaded you have to manually set their access to public so it can be accessed from batch. This has to be done to deal with the batch limits as it is explained in the next section.

And trigger the execution of the function by uploading a file to be processed to the corresponding folder::

  scar put -b scar-plants/input -p daisy.jpg

SCAR automatically creates the compute environment in AWS Batch and submits a job to be executed. Input and output data files are transparently managed as well according to the programming model.

The CloudWatch logs will reveal the execution of the Lambda function as well as the execution of the AWS Batch job.
Notice that whenever the execution of the AWS Batch job has finished, the EC2 instances will be eventually terminated.
Also, the number of EC2 instances will increase and shrink to handle the incoming number of jobs.

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

The payload limit can be avoided by redefining the script used and passing the large payload files using other service (e.g S3 or some bash command like 'wget' or 'curl' to download the information in execution time). As we didi with the plant classification example, where a `bootstrap script <https://github.com/grycap/scar/blob/master/examples/plant-classification/bootstrap-plants.sh>`_ was used to download the `executed script <https://github.com/grycap/scar/blob/master/examples/plant-classification/plant-classification-run.sh>`_.

Also, AWS Batch does not allow to override the container entrypoint so containers with an entrypoint defined can not execute an user script.
