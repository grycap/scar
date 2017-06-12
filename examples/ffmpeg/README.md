# FFmpeg on AWS Lambda

[FFmpeg](https://ffmpeg.org/) can be easily run on AWS Lambda to perform scalable video transcodification by means of SCAR.

## Choosing the Docker image

There are several Docker images available in [Docker Hub](https://hub.docker.com/search/?isAutomated=0&isOfficial=0&page=1&pullCount=0&q=ffmpeg&starCount=0) that include FFmpeg. You have to discard those based on Alpine and those that will not fit within the 512 MB limit of AWS Lambda. The following Docker image is appropriate:

* [sameersbn/ffmpeg](https://hub.docker.com/r/sameersbn/ffmpeg/), an 85 MB (compressed) Docker image based on Ubuntu 14.04.

## Goal

In this example, the goal is that videos uploaded to an Amazon S3 bucket are automatically converted to grayscale into that same bucket without requiring any installation or infrastructure provisioning.

## Creating the file processing script

A sample script to be executed inside the Docker container running on AWS Lambda is shown in the file [grayify-video.sh](grayify-video.sh). This script is agnostic to the Lambda function and it assumes that:

1. The user will upload the video into the `input` folder of an Amazon S3 bucket.
2. The input video file will automatically be made available in  `tmp/$REQUEST_ID/input`.
3. The script will convert to video to grayscale.
4. The output file will be saved in `/tmp/$REQUEST_ID/output`.
5. The file will be automatically uploaded to the `output` folder of the Amazon S3 bucket and deleted from the underlying storage.

## Create the Lambda function

This example assumes that the Amazon S3 bucket is `scar-test`. Since there is a flat namespace, please change this name for your tests.

```sh
scar init -s grayify-video.sh -n lambda-ffmpeg-01 -es scar-test sameersbn/ffmpeg
```

## Test the Lambda function

Upload a video to the S3 bucket. For these examples we are using sample videos from the [ICPR 2010 Contest on Semantic Descriptio if Human Activities (SDAH 2010)](http://cvrc.ece.utexas.edu/SDHA2010/Human_Interaction.html).

```sh
aws s3 cp s3://scar-data/sdha2010/seq1.avi s3://scar-test/input/seq1.avi
```

The converted video to grayscale will be available in `s3://scar-test/output/seq2.avi`.

## Limitations

Those of AWS Lambda:

* Maximum execution time of 5 minutes.
* Maximum temporary storage space in /tmp of 512 MB.
