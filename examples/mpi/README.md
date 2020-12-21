# MPI with SCAR


Running a distributed MPI app in a Docker container on Lambda and Batch

There are two different modes of running for this example: lambda through the __lambda.yaml__ and batch through __batch.yaml__.
This example uses the S3 bucket __scar-mpi__ for the input (the execution trigger) and the output of the job execution.
It is created automatically once a job is initialized, along with the input and output folders.

The steps to run the example are:

* Clone the repository (__/tmp__ for our example)

`git clone https://github.com/grycap/scar /tmp`

* Create a docker ignore if you plan to run Amazon Lambda or Batch with an uploaded image to DockerHub. The contents of the ignore are listed in this README.

* [Lambda/Batch when upload to DockerHub] Build the the Docker image locally

`docker build --build-arg ADD_BASE_DIR=scar/examples/mpi --label scar-mpi -t scar-mpi -f /tmp/scar/examples/mpi/Dockerfile /tmp`

* [Lambda/Batch when upload local image to DockerHub] Dump the Docker image and upload it to DockerHub in case of Amazon Batch with container built locally.

`sudo docker save scar-mpi > /tmp/scar-mpi.img`

* Prepare __run_helper.yaml__. Follow the instructions inside the file.

* [Batch] Set the Docker repo/image in __batch.yaml__

* Init the function using scar

`scar init -f <batch or lambda>.yaml`

* [Batch] Generate private/public keys used by ssh to communicate between nodes. The default names can be changed using the env variables SSH_PRIV_FILE_KEY and SSH_PUB_FILE_KEY

* [Batch] Upload a tar.gz archive file with the public and private keys in the root of the archive to the root of the bucket __scar-mpi__

* [Batch] Upload the modified __run_helper.yaml__ file to the bucket __scar-mpi/input__

* [Lambda] Run the function using SCAR

`scar run -f lambda.yaml`

* The results are uploaded automatically to  __scar-mpi/output__ once the execution has been successfully finalized (__time.log__ for our example with the application log). The log file is also displayed in the console, so SCAR should show the result.

## Git ignore examples

Use these lines to create a __.dockerignore__ file in __/tmp__.
This is needed to avoid including unnecessary files during the image building

```
# Ignore everything
**

# Allow files and directories
!/scar/examples/mpi/**

# Ignore unnecessary files inside allowed directories
# This should go after the allowed directories
**/batch.yaml
**/lambda.yaml
**/run_helper.sh
**/README.md
**/LICENSE
```
