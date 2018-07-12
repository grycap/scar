# SCAR - Serverless Container-aware ARchitectures

[![License](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/1968/badge)](https://bestpractices.coreinfrastructure.org/projects/1968)

# ![SCAR](scar-logo.png)

SCAR is a framework to transparently execute containers out of Docker images in AWS Lambda, in order to run applications (see examples for [ImageMagick](examples/imagemagick/README.md), [FFmpeg](examples/ffmpeg/README.md) and [AWS CLI](examples/aws-cli/README.md), as well as deep learning frameworks such as [Theano](examples/theano/README.md) and [Darknet](examples/darknet/README.md)) and code in virtually any programming language (see examples for [Ruby](examples/ruby), [R](examples/r), [Erlang](examples/erlang) and [Elixir](examples/elixir)) on AWS Lambda.

SCAR provides the benefits of AWS Lambda with the execution environment you decide, provided as a Docker image available in Docker Hub. It is probably the easiest, most convenient approach to run generic applications on AWS Lambda, as well as code in your favourite programming language, not only in those languages supported by AWS Lambda.

SCAR also supports a High Throughput Computing [Programming Model](#programming-model) to create highly-parallel event-driven file-processing serverless applications that execute on customized runtime environments provided by Docker containers run on AWS Lambda. The development of SCAR has been published in the [Future Generation Computer Systems](https://www.journals.elsevier.com/future-generation-computer-systems) scientific journal.

<a name="toc"></a>
**Related resources**:
  [Website](https://grycap.github.io/scar/) |
  [Scientific Paper](http://linkinghub.elsevier.com/retrieve/pii/S0167739X17316485) ([pre-print](http://www.grycap.upv.es/gmolto/publications/preprints/Perez2018scc.pdf)).

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
