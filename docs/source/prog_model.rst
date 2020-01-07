Event-Driven File-Processing Programming Model
==============================================

SCAR supports an event-driven programming model suitable for the execution of highly-parallel file-processing applications that require a customized runtime environment.

The following command::

  cat >> darknet.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-darknet-s3
        memory: 2048
        init_script: yolo.sh
        container:
          image: grycap/darknet
        input:
        - storage_provider: s3
          path: scar-darknet/input
        output:
        - storage_provider: s3
          path: scar-darknet/output        
  EOF

  scar init -f darknet.yaml

Creates a Lambda function to execute the shell-script `yolo.sh <https://github.com/grycap/scar/blob/master/examples/darknet/yolo.sh>`_ inside a Docker container created out of the ``grycap/darknet`` Docker image stored in Docker Hub.

The following workflow summarises the programming model:

#) The Amazon S3 bucket ``scar-darknet`` is created with an ``input`` folder inside it if it doesn't exist.
#) The Lambda function is triggered upon uploading a file into the ``input`` folder created.
#) The Lambda function retrieves the file from the Amazon S3 bucket and makes it available for the shell-script running inside the container in the path ``$TMP_INPUT_DIR``. The ``$INPUT_FILE_PATH`` environment variable will point to the location of the input file.
#) The shell-script processes the input file and produces the output (either one or multiple files) in the folder specified by the ``$TMP_OUTPUT_DIR`` global variable.
#) The output files are automatically uploaded by the Lambda function into the ``output`` folder created inside of the ``scar-darknet`` bucket.

Many instances of the Lambda function may run concurrently and independently, depending on the files to be processed in the S3 bucket. Initial executions of the Lambda may require retrieving the Docker image from Docker Hub but this will be cached for subsequent invocations, thus speeding up the execution process.

For further information, examples of such application are included in the `examples/ffmpeg <https://github.com/grycap/scar/tree/master/examples/ffmpeg>`_ folder, in order to run the `FFmpeg <https://ffmpeg.org/>`_ video codification tool, and in the `examples/imagemagick <https://github.com/grycap/scar/tree/master/examples/imagemagick>`_, in order to run the `ImageMagick <https://www.imagemagick.org>`_ image manipulation tool, both on AWS Lambda.

More Event-Driven File-Processing thingies
------------------------------------------

SCAR also supports another way of executing highly-parallel file-processing applications that require a customized runtime environment.

After creating a function with the configuration file defined in the previous section, you can activate the SCAR event launcher using the ``run`` command like this::

  scar run -f darknet.yaml

This command lists the files in the ``input`` folder of the ``scar-darknet`` bucket and sends the required events (one per file) to the lambda function.

.. note::  The input path must be previously created and must contain some files in order to launch the functions. The bucket could be previously defined and you don't need to create it with SCAR.

The following workflow summarises the programming model, the differences with the main programming model are in bold:

#) **The folder 'input' inside the amazon S3 bucket 'scar-darknet' will be searched for files.**
#) **The Lambda function is triggered once for each file found in the folder. The first execution is of type 'request-response' and the rest are 'asynchronous' (this is done to ensure the caching and accelerate the subsequent executions).**
#) The Lambda function retrieves the file from the Amazon S3 bucket and makes it available for the shell-script running inside the container. The ``$INPUT_FILE_PATH`` environment variable will point to the location of the input file.
#) The shell-script processes the input file and produces the output (either one or multiple files) in the path specified by the ``$TMP_OUTPUT_DIR`` global variable.
#) The output files are automatically uploaded by the Lambda function into the ``output`` folder of ``scar-darknet`` bucket.

.. image:: images/wait.png
   :align: center

Function Definition Language (FDL)
----------------------------------

In the last update of SCAR, the language used to define functions was improved and now several functions with their complete configurations can be defined in one configuration file. Additionally, differente storage providers with different configurations can be used.

A complete working example of this functionality can be found `here <https://github.com/grycap/scar/tree/master/examples/video-process>`_.

In this example two functions are created, one with Batch delegation to process videos and the other in Lambda to process the generated images. The functions are connected by their linked buckets as it can be seen in the configuration file::

  cat >> scar-video-process.yaml << EOF
  functions:
    aws:
    - lambda:
        name: scar-batch-ffmpeg-split
        init_script: split-video.sh
        execution_mode: batch
        container:
          image: grycap/ffmpeg
        input:
        - storage_provider: s3
          path: scar-video/input
        output:
        - storage_provider: s3
          path: scar-video/split-images
    - lambda:
        name: scar-lambda-darknet
        init_script: yolo-sample-object-detection.sh
        memory: 3008
        container:
          image: grycap/darknet
        input:
        - storage_provider: s3
          path: scar-video/split-images
        output:
        - storage_provider: s3
          path: scar-video/output
  EOF

  scar init -f scar-video-process.yaml

Using the common folder ``split-images`` these functions can be connected to create a workflow.
None of this buckets or folders must be previously created for this to work. SCAR manages the creation of the required buckets/folders.

To launch this workflow you only need to upload a video to the folder ``input`` of the ``scar-video`` bucket, with the command::

  scar put -b scar-video/input -p seq1.avi

This will launch first, the splitting function that will create 68 images (one per each second of the video), and second, the 68 Lambda functions that process the created images and analyze them.