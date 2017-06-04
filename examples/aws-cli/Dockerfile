FROM bitnami/minideb:jessie

MAINTAINER Germán Moltó - gmolto@dsic.upv.es

ENV AWS_DEFAULT_REGION us-east-1

RUN install_packages python python-pip

RUN pip install --upgrade awscli

ENTRYPOINT ["/usr/bin/python", "/usr/local/bin/aws"]