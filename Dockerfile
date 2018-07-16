FROM python:3.7.0-stretch

MAINTAINER @iMerica <imerica@me.com>

RUN apt-get update && apt-get install -y zip

RUN addgroup --system scar  && adduser --system --group scar

RUN git clone --branch master --depth 1 https://github.com/grycap/scar.git /usr/bin/scar && \
    pip install -r /usr/bin/scar/requirements.txt && \
    pip install pyyaml

RUN touch /scar.log && chown scar /scar.log

ENV PYTHONUNBUFFERED=1

USER scar

ENTRYPOINT ["python3", "/usr/bin/scar/scar.py"]


