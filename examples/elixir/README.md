# Running Elixir in AWS Lambda

You can run [Elixir](https://elixir-lang.org/) on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/elixir](https://hub.docker.com/r/grycap/elixir/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

## Usage in AWS Lambda via SCAR

You can run a container out of this image on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -f scar-elixir.yaml
```

2. Execute the Lambda function with an script to compile and run an Erlang application

```sh
scar run -f scar-elixir.yaml -s elixir-hw.sh 
```

The first invocation will take considerably longer than the subsequent ones, where the container will be cached. You can modify the script and perform another `scar run`.

You can also run multiple concurrent invocations of this Lambda function to perform highly-parallel event-driven processing. See the [SCAR Programming Model](http://scar.readthedocs.io/en/latest/prog_model.html).