# Video Processing on AWS Lambda and AWS Batch

In this example we are going to process an input video by combining the benefits of the highly-scalable AWS Lambda service with the convenience of batch-based computing provided by AWS Batch. The video is going to be split in different images and then those images are going to be analyzed by a neural network. This is a clear example of a serverless workflow.

Two different Lambda functions are defined to do this work: first `scar-batch-ffmpeg-split`, a function that creates an AWS Batch job that splits the video in 1-second pictures and stores them in S3; second `scar-lambda-darknet`, a Lambda function that processes each image to perform object detection and stores the result also in Amazon S3. Both functions are defined in the configuration file `scar-video-process.yaml`.

More information about the AWS Batch integration can be found in the [documentation](https://scar.readthedocs.io/en/latest/batch.html).

## Create the processing functions

To create the workflow you only need to execute one command:

```sh
scar init -f scar-video-process.yaml
```

## Launch the execution

In order to launch an execution you have to upload a file to the defined input bucket of the Lambda function that creates the AWS Batch job. In this case, the following command will start the execution:

```sh
scar put -b scar-video/input -p ../ffmpeg/seq1.avi
```

## Process the output

When the execution of the second function finishes, the script used produces two output files for each Lambda invocation. SCAR copies them to the S3 bucket specified as output. To check if the files are created and copied correctly you can use the command:

```sh
scar ls -b scar-video/output
```

Which lists the following outputs:

```
output/001.out
output/001.png
output/002.out
output/002.png
...
output/067.out
output/067.png
output/068.out
output/068.png
```

The files are created in the output folder following the `s3://scar-video/output/*.*` structure.

To download the generated files you can also use SCAR with the following command:

```sh
scar get -b scar-video/output -p /tmp/video/
```

This command creates the `video/output` folder in the `/tmp` path.

## Delete the Lambda functions

Do not forget to delete the functions when you finish your testing:

```sh
scar rm -f scar-video-process.yaml
```

Have in mind that the bucket, the folders and the files created are not deleted when the function is deleted.

If you want to delete the bucket you have to do it manually using, for example, AWS CLI::

```sh
  aws s3 rb s3://scar-video --force
```