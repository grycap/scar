# Running Darknet on AWS Lambda

You can run [Darknet](https://pjreddie.com/darknet) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/darknet](https://hub.docker.com/r/grycap/darknet/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

[Darknet](https://pjreddie.com/darknet) is an open source neural network framework written in C and CUDA. For the example we will be using the the library 'You only look once' [Yolo](https://pjreddie.com/darknet/yolo/) which is  is a state-of-the-art, real-time object detection system

Since we are using Darknet on the CPU it takes around 6-12 seconds per image, using the GPU version would be much faster.

## Usage in AWS Lambda via SCAR

### Event driven execution (using S3)

> WARNING:  To work properly this software needs at least a lambda function with 1024MB of RAM

You can run a container out of this image on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -s yolo-sample-object-detection.sh -ib s3-bucket -m 2048 -n darknet -i grycap/darknet
```

2. Launch the Lambda function uploading a file to the `s3://s3-bucket/darknet/input` folder in S3.

For this example we are using this image (https://github.com/pjreddie/darknet/blob/master/data/dog.jpg): 
![dog.jpg](dog.jpg)

```sh
wget https://raw.githubusercontent.com/grycap/scar/master/examples/darknet/dog.jpg -O /tmp/dog.jpg
scar put -b s3-bucket -bf darknet/input -p /tmp/dog.jpg
```

Take into consideration than the first invocation will take considerably longer than the subsequent ones, where the container will be cached.

To check the progress of the function invocation you can call the `log` command:
```sh
scar log -n darknet
```

### HTTP invocation (using API Gateway)

The same can be achieved by defining an HTTP endpoint with the AWS API Gateway and invoking the function using a POST request.

1. We start by creating the Lambda function and linking it to and API endpoint

```sh
scar init -s yolo-sample-object-detection.sh -ib s3-bucket -m 2048 -n darknet -i grycap/darknet -api darknet-api
```

2. Launch the Lambda function using the `invoke` command of SCAR (due to the 29 timeout of the API endpoint, it's very probable that the first execution gives you an `Error (Gateway Timeout): Endpoint request timed out` although if you check the logs the lambda function should have finished correctly):

```sh
scar invoke -n darknet -X POST -d /tmp/dog.jpg
```

To avoid the api timeout you can launch the function asynchronously:

```sh
scar invoke -n darknet -X POST -d /tmp/dog.jpg -a
```

### Processing the output

3. When the execution of the function finishes, the script used produces two output files and SCAR copies them to the S3 bucket used. To check if the files are created and copied correctly you can use the command:

```sh
scar ls -b s3-bucket -bf darknet/output
```

Command output:
```
darknet/output/68f5c9d5-5826-44gr-basc-8f8b23f44cdf/image-result.png
darknet/output/68f5c9d5-5826-44gr-basc-8f8b23f44cdf/result.out
```

The files are created in the output folder following the `s3://s3-bucket/darknet/output/$REQUEST_ID/*.*` structure.

To download the created files you can also use SCAR:

Download an specific file with :
```sh
scar get -b s3-bucket -bf darknet/output/68f5c9d5-5826-44gr-basc-8f8b23f44cdf/image-result.png -p /tmp/result.png
```

Download a folder with:

```sh
scar get -b s3-bucket -bf darknet/output -p /tmp/lambda/
```

This command creates and `ouput` folder and all the subfolders in the `/tmp/lambda/` folder


In our case the two output files are result.out:

```sh
/tmp/68f5c9d5-5826-44gr-basc-8f8b23f44cdf/input/dog.jpg: Predicted in 12.383388 seconds.
dog: 82%
truck: 64%
bicycle: 85%
```

and image-result.png:
![image-result.png](image-result.png)
