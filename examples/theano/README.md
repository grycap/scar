# Running Theano on AWS Lambda

You can run [Theano](http://deeplearning.net/software/theano/) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/theano](https://hub.docker.com/r/grycap/theano/) Docker image, based on the [bitnami/minideb:jessie](https://hub.docker.com/r/bitnami/minideb/) one.

Note that this image does not have a C++ compiler and, therefore, Theano will be unable to execute optimized C-implementations and will default to Python implementations. Thus, performance will be severely degraded. However, including a C++ compiler will make this image unable to run on AWS 

## Usage in AWS Lambda via SCAR

You can run a container out of this image on AWS Lambda via [SCAR](https://github.com/grycap/scar) using the following procedure:

1. Create the Lambda function

```sh
scar init -f scar-theano.yaml
```

2. Execute the Lambda function with an script to compile and run the application

```sh
scar run -f scar-theano.yaml -s theano-hw.sh
```

The first invocation will take considerably longer than the subsequent ones, where the container will be cached. You can modify the script and perform another `scar run`.

You can also run multiple concurrent invocations of this Lambda function to perform highly-parallel event-driven processing. See the [SCAR Programming Model](http://scar.readthedocs.io/en/latest/prog_model.html).