# Alpine-less Cowsay

Docker image for [Cowsay](https://en.wikipedia.org/wiki/Cowsay) and [Fortune](https://en.wikipedia.org/wiki/Fortune_(Unix) based on the [ubuntu:16.04](https://hub.docker.com/r/library/ubuntu/tags/16.04/) Docker image.

## Local Usage

Basic execution (Fortune + Cowsay) with a random message:

```sh
docker run --rm grycap/cowsay
```

To obtain a customized message:

```sh
docker run --rm grycap/cowsay /usr/games/cowsay "Hello World"
```

## Usage in AWS Lambda via SCAR

You can run this image in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function using the 'scar-cowsay.yaml' configuration file provided:

```sh
scar init -f scar-cowsay.yaml
```

2. Execute the Lambda function

```sh
scar run -f scar-cowsay.yaml
```

3. When finished, delete the function with the command:

```sh
scar rm -f scar-cowsay.yaml
```

## Deploy docker image in AWS Lambda via SCAR

As explained in the [SCAR documentation](http://scar.readthedocs.io/en/latest/advanced_usage.html#upload-slim-docker-image-files-in-the-payload), if the image is small enough (i.e. less than 40MB) you can upload it directly in the function payload.
To test that we minimized the cowsay image using [minicon](https://github.com/grycap/minicon) and now we are going to deploy it:

1. First download and save the docker image locally:

```sh
docker pull grycap/minicow
docker save grycap/minicow > minicow.tar.gz
```

2. Create the Lambda function using the 'scar-minicow.yaml' configuration file:

```sh
scar init -f scar-minicow.yaml
```

3. Execute the Lambda function

```sh
scar run -f scar-minicow.yaml
```

From the user perspective nothing changed in comparison with the previous execution, but the main difference with the 'standard' lambda deployment is that the container is already available when the function is launched for the first time. Moreover, the function doesn't need to connect to any external repository to download the container, so this is also useful to execute small binaries or containers that you don't want to upload to a public repository.