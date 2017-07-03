# Original Dockerfile from https://hub.docker.com/r/kaixhin/theano/~/dockerfile/
# Modified by @alpegon to fit within the AWS Lambda limits
FROM bitnami/minideb

RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  python-dev \
  python-setuptools \
  python-numpy \
  python-scipy \
  python-pip \
  libopenblas-base  \
  
  && pip install --upgrade --no-deps git+git://github.com/Theano/Theano.git six \
  && apt-get remove -y \
     git \
     python-pip \

  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
