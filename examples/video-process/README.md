# Video procession infrastructure

In this example we are going to process an input video. The video is going to be split in different images and then those images are going to be analyzed by a neural network.

Two different Lambda functions are defined to do this work: first, a function that creates an AWS Batch job that splits the video and stores it in S3; second, a Lambda function that processes each image and stores the result also in Amazon S3.

The two different configuration files can be found in this folder. The file 'scar-batch-ffmpeg-split.yaml' defines a function that creates a Batch job and the file 'scar-lambda-darknet.yaml' defines a functions that analyzes the images created.

More information about the AWS Batch integration can be found in the [official documentation](https://scar.readthedocs.io/en/latest/batch.html).

## Create the infrastructure

To create the functions you only need to execute two commands:

```sh
scar init -f scar-batch-ffmpeg-split.yaml
```
```sh
scar init -f scar-lambda-darknet.yaml
```

## Launch the execution

In order to launch an execution you have to upload a file to the defined input bucket of the Lambda function that creates the AWS Batch job. In this case, the following command will start the execution:

```sh
scar put -b scar-ffmpeg -bf scar-ffmpeg-split/input -p ../ffmpeg/seq1.avi
```

## Process the output

When the execution of the function finishes, the script used produces two output files for each Lambda invocation. SCAR copies them to the S3 bucket specified as output. To check if the files are created and copied correctly you can use the command:

```sh
scar ls -b scar-ffmpeg -bf scar-ffmpeg-split/image-output
```

Which outputs:

```
scar-batch-ffmpeg-split/image-output/c45433a2-e8e4-11e8-8c48-ab3c38d92053/image-result.png
scar-batch-ffmpeg-split/image-output/c45433a2-e8e4-11e8-8c48-ab3c38d92053/result.out
...
scar-batch-ffmpeg-split/image-output/c46aefe9-e8e4-11e8-97ef-8342661a6503/image-result.png
scar-batch-ffmpeg-split/image-output/c46aefe9-e8e4-11e8-97ef-8342661a6503/result.out
scar-batch-ffmpeg-split/image-output/c479475e-e8e4-11e8-995c-b14a6469fc4a/image-result.png
scar-batch-ffmpeg-split/image-output/c479475e-e8e4-11e8-995c-b14a6469fc4a/result.out
```

The files are created in the output folder following the `s3://scar-ffmpeg/scar-batch-ffmpeg-split/image-output/$REQUEST_ID/*.*` structure.


To download the created files you can also use SCAR. Download a folder with:

```sh
scar get -b scar-ffmpeg -bf scar-batch-ffmpeg-split/image-output -p /tmp/lambda/
```

This command creates and `image-output` folder and all the subfolders in the `/tmp/lambda/` folder

## Delete the Lambda functions

Don't forget to delete the functions when you finish your testing:

```sh
scar rm -f scar-batch-ffmpeg-split.yaml
```

```sh
scar rm -f scar-lambda-darknet.yaml
```

Have in mind that the bucket, the folders and the files created are not deleted when the function is deleted.

If you want to delete the bucket you have to do it manually.