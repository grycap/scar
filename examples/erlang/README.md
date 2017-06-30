# Running Erlang in AWS Lambda

You can run [Erlang](https://www.erlang.org/) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/erlang](https://hub.docker.com/r/grycap/erlang/) Docker image.

This Docker image is based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) Docker image.

## Usage in AWS Lambda via SCAR

You can run this image in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -n scar-grycap-erlang grycap/erlang
```

2. Execute the Lambda function with an script to compile and run an Erlang application

```sh
scar run -s examples/erlang/erlang-hw.sh scar-grycap-erlang
```
