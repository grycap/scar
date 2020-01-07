# ImageMagick on AWS Lambda

[ImageMagick](https://www.imagemagick.org/) can be easily run on AWS Lambda to perform image manipulation by means of [SCAR](https://github.com/grycap/scar).

## Local Usage
Assuming that you want to use the `/tmp` directory for input and output image files:

```sh
docker run --rm -v /tmp:/tmp grycap/imagemagick convert 
```

## Usage in AWS Lambda via SCAR

You can run ImageMagick in AWS Lambda via SCAR to automatically perform image manipulation (for example to convert to grayscale) on images uploaded to the `input` folder of the `scar-test` S3 bucket by using the following procedure:

1. Create the Lambda function

```sh
scar init -f scar-imagemagick.yaml
```

2. Upload a file to the S3 bucket

```sh
scar put -b scar-imagemagick/input -p homer.png
```

The converted image to grayscale will be available in `s3://scar-imagemagick/output/homer.png`

3. Download a file from the S3 bucket

```sh
scar get -b scar-imagemagick/output -p /tmp/
```

The image will be downloaded in the path `/tmp/output/homer.png`.

The first invocation will take considerable longer time than most of the subsequent invocations since the container will be cached.

You can upload as many images as you want. Multiple concurrent Lambda invocations will be performed to transform the images.