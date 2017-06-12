# Alpine-less Cowsay

Docker image for [Cowsay](https://en.wikipedia.org/wiki/Cowsay) and [Fortune](https://en.wikipedia.org/wiki/Fortune_(Unix)) based on the [ubuntu:16.04](https://hub.docker.com/r/library/ubuntu/tags/16.04/) Docker image.

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

1. Create the Lambda function

```sh
scar init -n lambda-cowsay grycap/cowsay
```

2. Execute the Lambda function

```sh
scar run lambda-cowsay
```