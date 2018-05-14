# Running Ruby Code in AWS Lambda

You can run [Ruby](https://www.ruby-lang.org) on AWS Lambda via [SCAR](https://github.com/grycap/scar) using, for example, the [ruby:2.2.10-slim-jessie](https://hub.docker.com/r/library/ruby/) Docker image.

## Usage in AWS Lambda via SCAR

You can run a container out of this image on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -n scar-ruby-test -i ruby:2.2.10-slim-jessie
```

2. Execute the Lambda function with an script to run sample Ruby script

```sh
scar run -n scar-ruby-test -s examples/ruby/run-ruby-script.sh
```

The first invocation will take a bit longer than the subsequent ones, where the container will be cached. You can modify the script and perform another `scar run`.

You can also run multiple concurrent invocations of this Lambda function to perform highly-parallel event-driven processing. See the [SCAR Programming Model](https://github.com/grycap/scar/blob/master/README.md#programming-model).