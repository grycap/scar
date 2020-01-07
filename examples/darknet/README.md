# Running Darknet on AWS Lambda

You can run [Darknet](https://pjreddie.com/darknet) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/darknet](https://hub.docker.com/r/grycap/darknet/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

[Darknet](https://pjreddie.com/darknet) is an open source neural network framework written in C and CUDA. For the example we will be using the the library 'You only look once' [Yolo](https://pjreddie.com/darknet/yolo/) which is  is a state-of-the-art, real-time object detection system

Since we are using Darknet on the CPU it takes around 6-12 seconds per image, using the GPU version would be much faster.

## Usage in AWS Lambda via SCAR

> WARNING:  To work properly this software needs at least a lambda function with 1024MB of RAM

For the example we are using this image: ![dog.jpg](dog.jpg):

### Event driven invocation (using S3)

You can run a container out of this image on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

Create the Lambda function using the `scar-darknet.yaml` configuration file:

```sh
scar init -f scar-darknet.yaml
```

Launch the Lambda function uploading a file to the `s3://scar-darknet/input` folder in S3.

```sh
scar put -b scar-darknet/input -p dog.jpg
```

Take into consideration than the first invocation will take considerably longer than the subsequent ones, where the container will be cached.

To check the progress of the function invocation you can call the `log` command:
```sh
scar log -f scar-darknet.yaml
```

### HTTP invocation (using API Gateway)

The same can be achieved by defining an HTTP endpoint with the AWS API Gateway and invoking the function using a POST request.

We start by creating the Lambda function and linking it to and API endpoint:

```sh
scar init -f scar-darknet-api-s3.yaml
```

Launch the Lambda function using the `invoke` command of SCAR (due to the 29 timeout of the API endpoint, it's very probable that the first execution gives you an `Error (Gateway Timeout): Endpoint request timed out` although if you check the logs the lambda function should have finished correctly):

```sh
scar invoke -f scar-darknet-api-s3.yaml -db dog.jpg
```

To avoid the api timeout you can launch the function asynchronously:

```sh
scar invoke -f scar-darknet-api-s3.yaml -db dog.jpg -a
```

> WARNING: Check the [AWS lambda limits](https://docs.aws.amazon.com/lambda/latest/dg/limits.html) to know the maximum size of files that can be send as payload of the POST request

### Processing the S3 output

When the execution of the function finishes, the script used produces two output files and SCAR copies them to the S3 bucket used. To check if the files are created and copied correctly you can use the command:

```sh
scar ls -b scar-darknet/output
```

Which outputs:
```
output/dog.out
output/dog.png
```

The files are created in the output folder following the `s3://$BUCKET_NAME/output/*.*` structure.


To download the created files you can also use SCAR. Download a folder with:

```sh
scar get -b scar-darknet/output -p /tmp/lambda/
```

This command creates the `ouput` folder and all the required subfolders (if any) in the `/tmp/lambda/` folder

In our case the two output files are result.out:

```sh
/tmp/tmpzhmispbg/dog.jpg: Predicted in 28.073856 seconds.
dog: 80%
truck: 73%
bicycle: 81%
```

and image-result.png:
![image-result.png](image-result.png)

Don't forget to delete the function when you finish your testing:

```sh
scar rm -f scar-darknet-api-s3.yaml
```

Have in mind that the bucket and the folders and files created are not deleted when the function is deleted.

If you want to delete the bucket you have to do it manually.