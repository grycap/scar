FROM python:3-alpine

ENV SCAR_LOG_PATH='/var/log/'
ENV SUPERVISOR_TYPE='BATCH'

RUN pip3 install faas-supervisor

COPY batch_handler.py batch_handler.py

ENTRYPOINT python3 batch_handler.py