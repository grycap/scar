# Running Darknet on AWS Lambda

You can run [Darknet](https://pjreddie.com/darknet) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/darknet](https://hub.docker.com/r/grycap/darknet/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

[Darknet](https://pjreddie.com/darknet) is an open source neural network framework written in C and CUDA. For the example we will be using the the library 'You only look once' [Yolo](https://pjreddie.com/darknet/yolo/) which is  is a state-of-the-art, real-time object detection system

Since we are using Darknet on the CPU it takes around 6-12 seconds per image, using the GPU version would be much faster.

## Usage in AWS Lambda via SCAR

> WARNING:  To work properly this software needs at least a lambda function with 1024MB of RAM

You can run a container out of this image on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -s yolo-sample-object-detection.sh -es s3-bucket -m 1024 -i grycap/darknet
```

2. Launch the Lambda function uploading a file to the `/input` folder of the specified S3 bucket.

For this example we are using this image: https://github.com/pjreddie/darknet/blob/master/data/dog.jpg
You also need the aws client installed in your machine.

```sh
wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/dog.jpg -O /tmp/dog.jpg
aws s3 cp /tmp/dog.jpg s3://s3-bucket/input/dog.jpg
```

Take into consideration than the first invocation will take considerably longer than the subsequent ones, where the container will be cached.

3. In the output folder of the S3 bucket you will see the output of the yolo system with the name of the image that you uploaded.

In our case the output file is dog.out and the content:

```sh
/tmp/8645455b-6228-11e7-b45c-37719f6fd852/input/dog.jpg: Predicted in 18.879135 seconds.
dog: 82%
truck: 64%
bicycle: 85%
```
