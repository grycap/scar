# SCAR - Serverless Container-aware ARchitectures

[![License](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Build Status](https://jenkins.i3m.upv.es/buildStatus/icon?job=grycap/scar)](https://jenkins.i3m.upv.es/job/grycap/job/scar/)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/1968/badge)](https://bestpractices.coreinfrastructure.org/projects/1968)

# ![SCAR](scar-logo.png)

SCAR is a framework to transparently execute containers out of Docker images in AWS Lambda, in order to run applications (see examples for [ImageMagick](examples/imagemagick/README.md), [FFmpeg](examples/ffmpeg/README.md) and [AWS CLI](examples/aws-cli/README.md), as well as deep learning frameworks such as [Theano](examples/theano/README.md) and [Darknet](examples/darknet/README.md)) and code in virtually any programming language (see examples for [Ruby](examples/ruby), [R](examples/r), [Erlang](examples/erlang) and [Elixir](examples/elixir)) on AWS Lambda.

SCAR provides the benefits of AWS Lambda with the execution environment you decide, provided as a Docker image available in Docker Hub. It is probably the easiest, most convenient approach to run generic applications on AWS Lambda, as well as code in your favourite programming language, not only in those languages supported by AWS Lambda.

SCAR also supports a High Throughput Computing [Programming Model](https://scar.readthedocs.io/en/latest/prog_model.html) to create highly-parallel event-driven file-processing serverless applications that execute on customized runtime environments provided by Docker containers run on AWS Lambda. The development of SCAR has been published in the [Future Generation Computer Systems](https://www.journals.elsevier.com/future-generation-computer-systems) scientific journal.

SCAR is integrated with API Gateway in order to expose an application via a highly-available HTTP-based REST API that supports both synchronous and asynchronous invocations. It is also integrated with AWS Batch. This way, AWS Lambda can be used to acommodate the execution of large bursts of short requests while long-running executions are delegated to AWS Batch.

SCAR allows to create serverless workflows by combining functions that run on either AWS Batch or AWS Lambda which produce output files that trigger the execution of functions that, again, run on either AWS Batch or AWS Lambda, using the very same Docker images, thus effectively creating highly-scalable cross-services serverless workflows.

<a name="toc"></a>
**Related resources**:  
  [Scientific Paper](http://linkinghub.elsevier.com/retrieve/pii/S0167739X17316485) ([pre-print](http://www.grycap.upv.es/gmolto/publications/preprints/Perez2018scc.pdf)).

## Update 3.0.0

Since version 3.0.0 SCAR creates a lambda layer called 'faas-supervisor' that includes the core functionality for the lambda containers.
This layer allows to deploy new functions faster. The layer is created once (the first time that a function is created or after a layer update) and then it's linked to all the other functions.

If a new version of the supervisor is released (e.g. when a new feature is added or a bug is found) the functions can be updated with the command `scar update -a -sl`.

To check the supervisor layer version that your function is using you only have to do an ls like `scar ls`

## Documentation

SCAR documentation can be found in [readthedocs](http://scar.readthedocs.io/en/latest/).

Also the examples have extra information that is usefull to execute them.

## Licensing

SCAR is licensed under the Apache License, Version 2.0. See
[LICENSE](https://github.com/grycap/scar/blob/master/LICENSE) for the full
license text.

<a id="furtherinfo"></a>
## Further information

There is further information on the architecture of SCAR and use cases in the scientific publication ["Serverless computing for container-based architectures"](http://linkinghub.elsevier.com/retrieve/pii/S0167739X17316485) (pre-print available [here](http://www.grycap.upv.es/gmolto/publications/preprints/Perez2018scc.pdf)), included in the Future Generation Computer Systems journal. Please acknowledge the use of SCAR by including the following cite:

```
A. Pérez, G. Moltó, M. Caballer, and A. Calatrava, “Serverless computing for container-based architectures,” Futur. Gener. Comput. Syst., vol. 83, pp. 50–59, Jun. 2018.
```

<a id="acknowledgements"></a>
## Acknowledgements

* [udocker](https://github.com/indigo-dc/udocker)
