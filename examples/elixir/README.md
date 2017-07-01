# Running Elixir in AWS Lambda

You can run [Elixir](https://elixir-lang.org/) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/elixir](https://hub.docker.com/r/grycap/elixir/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

## Usage in AWS Lambda via SCAR

You can run a container out of this image in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -n scar-grycap-elixir grycap/elixir
```

2. Execute the Lambda function with an script to compile and run an Erlang application

```sh
scar run -s examples/elixir/elixir-hw.sh scar-grycap-elixir
```

You can also run multiple concurrent invocations of this Lambda function to perform highly-parallel event-driven processing. See the [SCAR Programming Model](https://github.com/grycap/scar/blob/master/README.md#programming-model).