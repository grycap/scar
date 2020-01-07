# FFmpeg on AWS Lambda

[FFmpeg](https://ffmpeg.org/) can be easily run on AWS Lambda to perform scalable video transcodification by means of SCAR.

## Choosing the Docker image

There are several Docker images available in [Docker Hub](https://hub.docker.com/search/?isAutomated=0&isOfficial=0&page=1&pullCount=0&q=ffmpeg&starCount=0) that include FFmpeg. You have to discard those that will not fit within the 512 MB limit of AWS Lambda. The following Docker image is appropriate:

* [sameersbn/ffmpeg](https://hub.docker.com/r/sameersbn/ffmpeg/), an 85 MB (compressed) Docker image based on Ubuntu 14.04.

## Goal

In this example, the goal is that videos uploaded to an Amazon S3 bucket are automatically converted to grayscale into that same bucket without requiring any installation or infrastructure provisioning.

## Creating the file processing script

A sample script to be executed inside the Docker container running on AWS Lambda is shown in the file [grayify-video.sh](grayify-video.sh). This script is agnostic to the Lambda function and it assumes that:

1. The user will upload the video into the `input` folder of the `scar-ffmpeg` Amazon S3 bucket.
2. The input video file will automatically be made available in the in the path specified by the `$INPUT_FILE_PATH` environment variable.
3. The script will convert to video to grayscale.
4. The output video file will be saved in the path specified by the `$TMP_OUTPUT_DIR` environment variable.
5. The video file will be automatically uploaded to the `output` folder of the `scar-ffmpeg` Amazon S3 bucket and deleted from the underlying storage.

## Create the Lambda function

This example assumes that the Amazon S3 bucket is `scar-ffmpeg`, if the bucket doesn't exist it will create it.

```sh
scar init -f scar-ffmpeg.yaml
```

## Test the Lambda function

Upload a video to the S3 bucket. For these examples we are using sample videos from the [ICPR 2010 Contest on Semantic Descriptio if Human Activities (SDAH 2010)](http://cvrc.ece.utexas.edu/SDHA2010/Human_Interaction.html).

```sh
scar put -b scar-ffmpeg/input -p seq1.avi
```

To check the progress of the function invocation you can call the `log` command:

```sh
scar log -f scar-ffmpeg.yaml
```

Whe the execution finishes, the converted video to grayscale will be available in `s3://scar-ffmpeg/output/seq1.avi`. Moreover you can list the files in the specified bucket with the command:

```sh
scar ls -b scar-ffmpeg/output/
```

After the function finishes you can download the generated output video using the following command:

```sh
scar get -b scar-ffmpeg/output -p /tmp/
```
This command will download the ouput folder of the S3 bucket to the /tmp/ folder of your computer

As an additional feature, you can also upload multiple videos to S3 using a folder instead an specific file.

```sh
scar put -b scar-ffmpeg/input -p /my-videos/
```
Multiple concurrent Lambda invocations of the same function will process in parallel the video files. Notice that the first invocation(s) will take considerably longer until caching of the Docker container is performed.

## Limitations

Those of AWS Lambda:

* Maximum execution time of 15 minutes.
* Maximum temporary storage space in /tmp of 512 MB (which may be possible shared across different executions of the same Lambda function).
