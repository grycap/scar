Advanced Usage
==============

Define a shell-script for each invocation of the Lambda function
----------------------------------------------------------------

Instead of packaging the script to be used inside the container image and having to modify the image each time you want to modify the script, you can specify a shell-script when initializing the Lambda function to trigger its execution inside the container on each invocation of the Lambda function. For example::

  cat >> init-script.yaml << EOF
  functions:
    scar-cowsay:
      image: grycap/cowsay
      init_script: src/test/test-cowsay.sh
  EOF

  scar init -f init-script.yaml

or using CLI parameters::

  scar init -s src/test/test-cowsay.sh -n scar-cowsay -i grycap/cowsay

Now whenever this Lambda function is executed, the script will be run in the container::

  scar run -f init-script.yaml

As explained in next section, this can be overridden by speciying a different shell-script when running the Lambda function.


Executing an user-defined shell-script
--------------------------------------

You can execute the Lambda function and specify a shell-script locally available in your machine to be executed within the container::

  cat >> run-script.yaml << EOF
  functions:
    scar-cowsay:
      image: grycap/cowsay
      run_script: src/test/test-cowsay.sh
  EOF

  scar run -f run-script.yaml

or using CLI parameters::

  scar run -s src/test/test-cowsay.sh -n scar-cowsay

or a combination of both (to avoid editing the .yaml file)::

  scar run -f run-script.yaml -s /tmp/test-cowsay.sh

Have in mind that the script used in combination with the run command is no saved anywhere. It is uploaded and executed inside the container, but the container image is not updated. The shell-script needs to be specified and can be changed in each different execution of the Lambda function.


Passing environment variables
-----------------------------

You can specify environment variables to the init command which will be in turn passed to the executed Docker container and made available to your shell-script.
Using a configuration file::

  cat >> env-var.yaml << EOF
  functions:
    scar-cowsay:
      image: grycap/cowsay
      init_script: src/test/test-global-vars.sh
      environment:
        TEST1: 45
        TEST2: 69
  EOF

  scar init -f env-var.yaml

or using CLI parameters::

  scar init -e TEST1=45 -e TEST2=69 -s src/test/test-global-vars.sh -n scar-cowsay

You can also update the environment variables by changing the configuration file and then using the update command::

  cat >> env-var.yaml << EOF
  functions:
    scar-cowsay:
      image: grycap/cowsay
      init_script: src/test/test-global-vars.sh
      environment:
        TEST1: 145
        TEST2: i69
        TEST3: 42
  EOF

  scar update -f env-var.yaml

or::

  scar update -e EST1: 145 -e TEST2: i69 -e TEST2: 42 -n scar-cowsay  

In addition, the following environment variables are automatically made available to the underlying Docker container:

* AWS_ACCESS_KEY_ID
* AWS_SECRET_ACCESS_KEY
* AWS_SESSION_TOKEN
* AWS_SECURITY_TOKEN

This allows a script running in the Docker container to access other AWS services. As an example, see how the AWS CLI runs on AWS Lambda in the `examples/aws-cli <https://github.com/grycap/scar/tree/master/examples/aws-cli>`_ folder.


Executing cli commands
----------------------

To run commands inside the docker image you can specify the command to be executed at the end of the command line::

  scar run -f basic-cow.yaml ls


Passing arguments
^^^^^^^^^^^^^^^^^

You can also supply arguments which will be passed to the command executed in the Docker container::

  scar run -f basic-cow.yaml /usr/bin/perl /usr/games/cowsay Hello World

Note that since cowsay is a Perl script you will have to prepend it with the location of the Perl interpreter (in the Docker container).


Obtaining a JSON Output
-----------------------

For easier scripting, a JSON output can be obtained by including the `-j` or the `-v` (even more verbose output) flags::

  scar run -f basic-cow.yaml -j

Upload docker images using an S3 bucket
---------------------------------------

If you want to save some space inside the lambda function you can deploy a lambda function using an S3 bucket by issuing the following command::

  cat >> s3-bucket.yaml << EOF
  functions:
    scar-cowsay:
      image: grycap/cowsay
      s3:
        deployment_bucket: scar-cowsay
  EOF

  scar init -f s3-bucket.yaml

or using the CLI::

  scar init -db scar-cowsay -n scar-cowsay -i grycap/cowsay

The maximum deployment package size allowed by AWS is an unzipped file of 250MB. With this restriction in mind, SCAR downloads the docker image to a temporal folder and creates the udocker file structure needed. 
* If the image information and the container filesystem fit in the 250MB SCAR will upload everything and the lambda function will not need to download or create a container structure thus improving the execution time of the function. This option gives the user the full 500MB of ``/tmp/`` storage.
* If the container filesystem doesn't fit in the deployment package SCAR will only upload the image information, that is, the layers. Also the lambda function execution time is improved because it doesn't need to dowload the container. In this case udocker needs to create the container filesystem so the first function invocation can be delayed for a few of seconds. This option usually duplicates the available space in the ``/tmp/`` folder with respect to the SCAR standard initialization.

Upload docker image files using an S3 bucket
--------------------------------------------

SCAR also allows to upload a saved docker image::

  cat >> s3-bucket.yaml << EOF
  functions:
    scar-cowsay:
      image_file: slim_cow.tar.gz
      s3:
        deployment_bucket: scar-cowsay
  EOF

  scar init -f s3-bucket.yaml

and for the CLI fans::

  scar init -db scar-cowsay -n scar-cowsay -if slim_cow.tar.gz

The behavior of SCAR is the same as in the case above (when uploading an image from docker hub). The image file is unpacked in a temporal folder and the udocker layers and container filesystem are created. Depending on the size of the layers and the filesystem, SCAR will try to upload everything or only the image layers.  

Upload 'slim' docker image files in the payload
-----------------------------------------------

Finally, if the image is small enough, SCAR allows to upload it in the function payload. Due to the SCAR libraries weighting ~10MB, the maximum size of the image uploaded using this method should not be bigger than ~40MB::

  cat >> slim-image.yaml << EOF
  functions:
    scar-cowsay:
      image_file: slimcow.tar.gz
  EOF

  scar init -f slim-image.yaml

To help with the creation of slim images, you can use `minicon <https://github.com/grycap/minicon>`_. Minicon is a general tool to analyze applications and executions of these applications to obtain a filesystem that contains all the dependencies that have been detected. By using minicon the size of the cowsay image was reduced from 170MB to 11MB.
