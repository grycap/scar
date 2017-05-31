FROM python:2.7-slim

MAINTAINER Germán Moltó - gmolto@dsic.upv.es

ENV AWS_DEFAULT_REGION us-east-1

RUN pip install --upgrade awscli

ENTRYPOINT ["/usr/local/bin/python", "/usr/local/bin/aws"]