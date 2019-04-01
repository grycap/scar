FROM python:3-alpine

ENV SCAR_LOG_PATH='/var/log/'
ENV SUPERVISOR_TYPE='BATCH'

RUN apk add git && git clone --branch storage https://github.com/grycap/faas-supervisor && cd faas-supervisor && pip3 install -U .

COPY batch_handler.py batch_handler.py

ENTRYPOINT python3 batch_handler.py