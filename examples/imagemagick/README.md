# ImageMagick on AWS Lambda

[ImageMagick](https://www.imagemagick.org/) can be easily run on AWS Lambda to perform image manipulation by means of [SCAR](https://github.com/grycap/scar).

## Local Usage
Assuming that you want to use the `/tmp` directory for input and output image files:

```sh
docker run --rm -v /tmp:/tmp grycap/imagemagick convert 
```

## Usage in AWS Lambda via SCAR

You can run ImageMagick in AWS Lambda via SCAR to automatically perform image manipulation (for example to convert to grayscale) on files uploaded to the `input` folder of the `scar-test` S3 bucket by using the following procedure:

1. Create the Lambda function

```sh
scar init -s examples/imagemagick/grayify-image.sh -n lambda-imagemagick -es scar-test grycap/imagemagick
```

2. Upload a file to the S3 bucket

```sh
aws s3 cp /tmp/homer.png s3://scar-test/input/homer.png
```
The converted image to grayscale will be available in `s3://scar-test/output/homer.png`

The first invocation will take considerable longer time than most of the subsequent invocations since the container will be cached.