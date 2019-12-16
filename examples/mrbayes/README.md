# MrBayes Docker Image

Docker image for [MrBayes](http://mrbayes.sourceforge.net/) based on the [ubuntu:14.04](https://hub.docker.com/r/library/ubuntu/tags/14.04/) Docker image.

## Usage in AWS Lambda via SCAR

You can run this image in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -f scar-mrbayes.yaml
```

2. Execute the Lambda function uploading a file to the linked bucket.

```sh
scar put -b scar-mrbayes/input -p cynmix.nex
```
3. Check the function logs to see when the execution has finished.

```sh
scar ls -b scar-mrbayes
```

4. Download the generated result file

```sh
scar get -b scar-mrbayes/output -p .
```
