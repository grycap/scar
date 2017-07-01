# Running Erlang in AWS Lambda

You can run [Erlang](https://www.erlang.org/) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/erlang](https://hub.docker.com/r/grycap/erlang/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

## Usage in AWS Lambda via SCAR

You can run a container out of this image in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -n scar-grycap-erlang grycap/erlang
```

2. Execute the Lambda function with an script to compile and run an Erlang application

```sh
scar run -s examples/erlang/erlang-hw.sh scar-grycap-erlang
```
The first invocation will take considerably longer than the subsequent ones, where the container will be cached. You can modify the script and perform another `scar run`.

You can also run multiple concurrent invocations of this Lambda function to perform highly-parallel event-driven processing. See the [SCAR Programming Model](https://github.com/grycap/scar/blob/master/README.md#programming-model).