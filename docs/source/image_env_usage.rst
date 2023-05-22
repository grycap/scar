Using Lambda Image Environment
==============================

Scar uses by default the python3.7 Lambda environment using udocker program to execute the containers.
In 2021 AWS added native support to ECR container images. Scar also supports to use this environment
to execute your containers.

This functionality requires docker to be installed (check installation documentation
`here <https://docs.docker.com/engine/install/>`_).

To use it you only have to set to ``image`` the lamda ``runtime`` property setting.
You can set it in the scar configuration file::

  {
    "aws": {
      "lambda": {
        "runtime": "image"
      }
    }
  }

Or in the function definition file::

  functions:
    aws:
    - lambda:
        runtime: image
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: image/name

Or event set it as a parameter in the ``init`` scar call::

  scar  init -f function_def.yaml -rt image

In this case the scar client will prepare the image and upload it to AWS ECR as required by the 
Lambda Image Environment.

To use this functionality you should use `supervisor <https://github.com/grycap/faas-supervisor>`_ 
version 1.5.0 or newer.

Using the image runtime the scar client will build a new container image adding the supervisor and
other needed files to the user provided image. This image will be then uploaded to an ECR registry
to enable Lambda environment to create the function. So the user that executes the scar client
must have the ability to execute the docker commands (be part of the ``docker`` group, see 
`docker documentation <https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user>`_)


Use alpine based images
-----------------------

Using the container image environment there is no limitation to use alpine based images (musl based).
You only have to add the ``alpine`` flag in the function definition::

  functions:
    aws:
    - lambda:
        runtime: image
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: image/name
          alpine: true

If you use an alpine based image and you do not set the ``alpine`` flag you will get an execution Error::

  Error: fork/exec /var/task/supervisor: no such file or directory

Use already prepared ECR images
--------------------------------

You can also use a previously prepared ECR image instead of building it and and pushing to ECR.
In this case you have to specify the full ECR image name and add set to false the ``create_image``
flag in the function definition::

  functions:
    aws:
    - lambda:
        runtime: image
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: 000000000000.dkr.ecr.us-east-1.amazonaws.com/scar-function
          create_image: false

But this ECR image must have been prepared to work with scar. So it must have the
``init_script`` and the ``supervisor`` installed and set it as the ``CMD`` of the docker
image. You can use this example to create your own ``Dockefile``::

  from your_repo/your_image

  # Create a base dir
  ARG FUNCTION_DIR="/var/task"
  WORKDIR ${FUNCTION_DIR}
  # Set workdir in the path
  ENV PATH="${FUNCTION_DIR}:${PATH}"
  # Add PYTHONIOENCODING to avoid UnicodeEncodeError as sugested in:
  # https://github.com/aws/aws-lambda-python-runtime-interface-client/issues/19
  ENV PYTHONIOENCODING="utf8"

  # Copy your script, similar to:
  # https://github.com/grycap/scar/blob/master/examples/darknet/yolo.sh
  COPY script.sh ${FUNCTION_DIR}
  # Download the supervisor binary
  # https://github.com/grycap/faas-supervisor/releases/latest
  # Copy the supervisor
  COPY supervisor ${FUNCTION_DIR}
  # Set it as the CMD
  CMD [ "supervisor" ]


Do not delete ECR image on function deletion
--------------------------------------------

By default the scar client deletes the ECR image in the function deletion process.
If you want to maintain it for future functions you can modify the scar configuration
file and set to false ``delete_image`` flag in the ecr configuration section::

  {
    "aws": {
      "ecr": {
        "delete_image": false
      }
    }
  }

Or set it in the function definition::

  functions:
    aws:
    - lambda:
        runtime: image
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: image/name
      ecr:
        delete_image: false

ARM64 support
-------------

Using the container image environment you can also specify the architecture to execute your lambda 
function (x86_64 or arm64) setting the architectures field in the function definition. If not set
the default architecture will be used (x86_64)::

  functions:
    aws:
    - lambda:
        runtime: image
        architectures:
          - arm64
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: image/name

EFS support
------------

Using the container image environment you can also configure file system access for your Lambda function.
First you have to set the VPC parameters to use the same subnet where the EFS is deployed. Also verify
that the iam role set in the scar configuration has the correct permissions and the Security Groups is
properly configured to enable access to NFS port (see `Configuring file system access for Lambda functions <https://docs.aws.amazon.com/lambda/latest/dg/configuration-filesystem.html>`_).
Then you have to add the ``file_system`` field setting the arns and mount paths of the file systems to mount
as shown in the following example::


  functions:
    aws:
    - lambda:
        runtime: image
        vpc:
          SubnetIds:
            - subnet-00000000000000000
          SecurityGroupIds:
            - sg-00000000000000000
        file_system:
          - Arn: arn:aws:elasticfilesystem:us-east-1:000000000000:access-point/fsap-00000000000000000
            LocalMountPath: /mnt/efs
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: image/name

