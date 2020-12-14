# MPI with SCAR
Running a distributed MPI app in a Docker container on Lambda and Batch

There are two different modes of running for this example: lambda through the __lambda.yaml__ and batch through __batch.yaml__.
This example uses the S3 bucket __scar-mpi-example__ for the input (the execution trigger) and the output of the job execution.
It is created automatically once a job is initialized, along with the input and output folders.

The steps to run the example are:

* Init the function using scar

`scar init -f <batch or lambda>.yaml`

* [Batch only] Generate private/public keys used by ssh to communicate between nodes. The default names can be changed using the env variables SSH_PRIV_FILE_KEY and SSH_PUB_FILE_KEY

* [Batch only] Upload a tar.gz archive file with the public and private keys in the root of the archive to the root of the bucket __scar-mpi-example__

* Upload a file to the bucket __scar-mpi-example/input__

* The results are uploaded to  __scar-mpi-example/output__ once the execution has been successfully finalized
