Using Lambda Image Environment
==============================

Scar uses by default the python3.7 Lambda environment using udocker program to execute the containers.
In 2021 AWS added native support to ECR container images. Scar also supports to use this environment
to execute your containers.

To use it you only have to modify your scar configuration file, setting ``image`` as the lambda runtime::

  {
    "aws": {
      "lambda": {
        "runtime": "image"
      }
    }
  }

In this case the scar client will prepare the image and upload it to AWS ECR as required by the 
Lambda Image Environment.

Use alpine based images
-----------------------

Using the container image environment there is no limitation to use alpine based images (musl based).
You only have to add the ``alpine`` flag in the function definition::

  functions:
    aws:
    - lambda:
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: image/name
          alpine: true

Use already prepared ECR images
--------------------------------

You can also use a previously prepared ECR image instead of building it and and pushing to ECR.
In this case you have to specify the full ECR image name and add set to falsr the ``create_image``
flag in the function definition::

  functions:
    aws:
    - lambda:
        name: scar-function
        memory: 2048
        init_script: script.sh
        container:
          image: 000000000000.dkr.ecr.us-east-1.amazonaws.com/scar-function
          create_image: false

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