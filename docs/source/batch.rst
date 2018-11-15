.. highlight:: none

AWS Batch Integration
=======================

Define a job to be executed in batch
------------------------------------

SCAR allows to transparently integrate a Batch job execution. To enable this functionality you only need to set the execution mode of the lambda function to one of the two available used to create batch jobs ('lambda-batch' or 'batch') and SCAR will take care of the integration process (before using this feature make sure you have the correct rights set in your aws account).

The following configuration file defines a lambda function that creates a batch job (the required script can be found in `mrbayes-sample-run.sh <https://raw.githubusercontent.com/grycap/scar/master/examples/mrbayes/mrbayes-sample-run.sh>`_)::

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
 
Combine lambda and batch executions
-----------------------------------
As explained in section :doc:`/prog_model`, if you define an output bucket as the input bucket of another function, a workflow can be created.
By doing this, batch and lambda executions can be combined through S3 events.

An example of this execution can be found in the `video process example <https://github.com/grycap/scar/tree/master/examples/video-process>`_

Limits
------
When defining a Batch job have in mind that the `Batch service <https://docs.aws.amazon.com/batch/latest/userguide/service_limits.html>`_ has some limits that are lower than the `Lambda service <https://docs.aws.amazon.com/lambda/latest/dg/limits.html>`_.

For example, the Batch Job definition size is limited to 24KB and the invocation payload in Lambda is limited to 6MB in synchronous calls and 128KB in asynchronous calls.

To create the Batch job, the Lambda function defines a Job with the payload content included, and sometimes (i.e. when the script passed as payload is greater than 24KB) the Batch Job definition can fail.

The payload limit can be avoided by redefining the script used and passing the large payload files using other service (e.g S3 or some bash command like 'wget' or 'curl' to download the information in execution time).

Also, AWS Batch does not allow to override the container entrypoint so containers with an entrypoint defined can not execute an user script.
