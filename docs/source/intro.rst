About SCAR
==========

SCAR is a framework to transparently execute containers out of Docker images in AWS Lambda, in order to run applications (see examples for `ImageMagick <https://github.com/grycap/scar/tree/master/examples/imagemagick>`_, `FFmpeg <https://github.com/grycap/scar/tree/master/examples/ffmpeg>`_ and `AWS CLI <https://github.com/grycap/scar/tree/master/examples/aws-cli>`_, as well as deep learning frameworks such as `Theano <https://github.com/grycap/scar/tree/master/examples/theano>`_ and `Darknet <https://github.com/grycap/scar/tree/master/examples/darknet>`_) and code in virtually any programming language (see examples for `Ruby <https://github.com/grycap/scar/tree/master/examples/ruby>`_, `R <https://github.com/grycap/scar/tree/master/examples/r>`_, `Erlang <https://github.com/grycap/scar/tree/master/examples/erlang>`_ and `Elixir <https://github.com/grycap/scar/tree/master/examples/elixir>`_) on AWS Lambda.

SCAR provides the benefits of AWS Lambda with the execution environment you decide, provided as a Docker image available in Docker Hub. It is probably the easiest, most convenient approach to run generic applications on AWS Lambda, as well as code in your favourite programming language, not only in those languages supported by AWS Lambda.

SCAR also supports a High Throughput Computing :doc:`/prog_model` to create highly-parallel event-driven file-processing serverless applications that execute on customized runtime environments provided by Docker containers run on AWS Lambda. The development of SCAR has been published in the `Future Generation Computer Systems <https://www.journals.elsevier.com/future-generation-computer-systems>`_ scientific journal.

SCAR is integrated with API Gateway in order to expose an application via a highly-available HTTP-based REST API that supports both synchronous and asynchronous invocations. It is also integrated with AWS Batch. This way, AWS Lambda can be used to acommodate the execution of large bursts of short requests while long-running executions are delegated to AWS Batch.

SCAR has been developed by the `Grid and High Performance Computing Group (GRyCAP) <http://www.grycap.upv.es>`_ at the `Instituto de Instrumentación para Imagen Molecular (I3M) <http://www.i3m.upv.es>`_ from the `Universitat Politècnica de València (UPV) <http://www.upv.es>`_.

.. image:: images/grycap.png
   :scale: 70 %
   
.. image:: images/i3m.png
   :scale: 70 %
   
.. image:: images/upv.png
   :scale: 70 %

There is further information on the architecture of SCAR and use cases in the scientific publication `"Serverless computing for container-based architectures" <http://linkinghub.elsevier.com/retrieve/pii/S0167739X17316485>`_ (pre-print available `here <http://www.grycap.upv.es/gmolto/publications/preprints/Perez2018scc.pdf>`_), included in the Future Generation Computer Systems journal. Please acknowledge the use of SCAR by referencing the following cite::

 A. Pérez, G. Moltó, M. Caballer, and A. Calatrava, “Serverless computing for container-based architectures,” Futur. Gener. Comput. Syst., vol. 83, pp. 50–59, Jun. 2018.
