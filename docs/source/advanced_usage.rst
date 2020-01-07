Advanced Usage
==============

Define a shell-script for each invocation of the Lambda function
----------------------------------------------------------------

Instead of packaging the script to be used inside the container image and having to modify the image each time you want to modify the script, you can specify a shell-script when initializing the Lambda function to trigger its execution inside the container on each invocation of the Lambda function. For example::

  cat >> cow.sh << EOF
  #!/bin/bash
  /usr/games/cowsay "Executing init script !!"
  EOF

  cat >> cow.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-cowsay
        init_script: cow.sh
        container:
          image: grycap/cowsay
  EOF

  scar init -f cow.yaml

or using CLI parameters::

  scar init -s cow.sh -n scar-cowsay -i grycap/cowsay

Now whenever this Lambda function is executed, the script will be run in the container::

  scar run -f cow.yaml

  Request Id: fb925bfa-bc65-47d5-beed-077f0de471e2
  Log Group Name: /aws/lambda/scar-cowsay
  Log Stream Name: 2019/12/19/[$LATEST]0eb088e8a18d4599a572b7bf9f0ed321
   __________________________
  < Executing init script !! >
   --------------------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||


As explained in next section, this can be overridden by speciying a different shell-script when running the Lambda function.


Executing an user-defined shell-script
--------------------------------------

You can execute the Lambda function and specify a shell-script locally available in your machine to be executed within the container::

  cat >> runcow.sh << EOF
  #!/bin/bash
  /usr/games/cowsay "Executing run script !!"
  EOF

  cat >> cow.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-cowsay
        run_script: runcow.sh
        container:
          image: grycap/cowsay
  EOF

  scar init -f cow.yaml

Now if you execute the function without passing more parameters, the entrypoint of the container is executed::

  scar run -n scar-cowsay

  Request Id: 97492a12-ca84-4539-be80-45696501ee4a
  Log Group Name: /aws/lambda/scar-cowsay
  Log Stream Name: 2019/12/19/[$LATEST]d5cc7a9db9b44e529873130f6d005fe1
   ____________________________________
  / No matter where I go, the place is \
  \ always called "here".              /
   ------------------------------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

But, when you use the configuration file with the ``run_script`` property::
  
  scar run -f cow.yaml

or use CLI parameters::

  scar run -n scar-cowsay -s runcow.sh

or a combination of both (to avoid editing the initial .yaml file)::

  scar run -f cow.yaml -s runcow.sh

the passed script is executed::

  Request Id: db3ff40e-ab51-4f90-95ad-7473751fb9c7
  Log Group Name: /aws/lambda/scar-cowsay
  Log Stream Name: 2019/12/19/[$LATEST]d5cc7a9db9b44e529873130f6d005fe1
   _________________________
  < Executing run script !! >
   -------------------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

Have in mind that the script used in combination with the run command is no saved anywhere.
It is uploaded and executed inside the container, but the container image is not updated.
The shell-script needs to be specified and can be changed in each different execution of the Lambda function.


Passing environment variables
-----------------------------

You can specify environment variables to the init command which will be in turn passed to the executed Docker container and made available to your shell-script.
Using a configuration file::

  cat >> cow.sh << EOF
  #!/bin/bash
  env | /usr/games/cowsay
  EOF

  cat >> cow-env.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-cowsay
        run_script: runcow.sh
        container:
          image: grycap/cowsay
          environment:
            Variables:
              TESTKEY1: val1
              TESTKEY2: val2
  EOF

  scar init -f cow-env.yaml

or using CLI parameters::

  scar init -n scar-cowsay -i grycap/cowsay -e TEST1=45 -e TEST2=69 -s cow.sh


Executing custom commands and arguments
---------------------------------------

To run commands inside the docker image you can specify the command to be executed at the end of the command line.
This command overrides any ``init`` or ``run`` script defined::

  scar run -f cow.yaml df -h

  Request Id: 39e6fc0d-6831-48d4-aa03-8614307cf8b7
  Log Group Name: /aws/lambda/scar-cowsay
  Log Stream Name: 2019/12/19/[$LATEST]9764af5bf6854244a1c9469d8cb84484
  Filesystem      Size  Used Avail Use% Mounted on
  /dev/root       526M  206M  309M  41% /
  /dev/vdb        1.5G   21M  1.4G   2% /dev


Obtaining a JSON Output
-----------------------

For easier scripting, a JSON output can be obtained by including the `-j` or the `-v` (even more verbose output) flags::

  scar run -f cow.yaml -j

  { "LambdaOutput": 
    {
      "StatusCode": 200,
      "Payload": " _________________________________________\n/  \"I always avoid prophesying beforehand \\\n| because it is much better               |\n|                                         |\n| to prophesy after the event has already |\n| taken place. \" - Winston                |\n|                                         |\n\\ Churchill                               /\n -----------------------------------------\n        \\   ^__^\n         \\  (oo)\\_______\n            (__)\\       )\\/\\\n                ||----w |\n                ||     ||\n",
      "LogGroupName": "/aws/lambda/scar-cowsay",
      "LogStreamName": "2019/12/19/[$LATEST]a4ba02914fd14ab4825d6c6635a1dfd6",
      "RequestId": "fcc4e24c-1fe3-4ca9-9f00-b15ec18c1676"
    }
  }


Upload docker image files using an S3 bucket
--------------------------------------------

SCAR allows to upload a saved docker image.
We created the image file with the command ``docker save grycap/cowsay > cowsay.tar.gz``::

  cat >> cow.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-cowsay
        container:
          image_file: cowsay.tar.gz
        deployment:
          bucket: scar-test
  EOF

  scar init -f cow.yaml

or for the CLI fans::

  scar init -db scar-cowsay -n scar-cowsay -if cowsay.tar.gz

Have in mind that the maximum deployment package size allowed by AWS is an unzipped file of 250MB.
The image file is unpacked in a temporal folder and the udocker layers are created.
Depending on the size of the layers, SCAR will try to upload them or will show the user an error.  

Upload 'slim' docker image files in the payload
-----------------------------------------------

Finally, if the image is small enough, SCAR allows to upload it in the function payload wich is ~50MB::

  docker save grycap/minicow > minicow.tar.gz

  cat >> minicow.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-cowsay
        container:
          image_file: minicow.tar.gz
  EOF

  scar init -f minicow.yaml

To help with the creation of slim images, you can use `minicon <https://github.com/grycap/minicon>`_.
Minicon is a general tool to analyze applications and executions of these applications to obtain a filesystem that contains all the dependencies that have been detected.
By using minicon the size of the cowsay image was reduced from 170MB to 11MB.