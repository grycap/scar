FROM alpine

ENV AWS_DEFAULT_REGION us-east-1

RUN apk update && apk add python3

RUN pip3 install awscli

ENTRYPOINT ["aws"]
