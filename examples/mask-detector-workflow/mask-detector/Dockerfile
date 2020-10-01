FROM python:slim-buster

RUN pip install --no-cache-dir opencv-python numpy && \
    rm -rf /root/.cache/pip/* && \
    rm -rf /tmp/*

RUN apt update && \
    apt install -y --no-install-recommends libgl1 libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /opt/mask-detector

WORKDIR /opt/mask-detector

COPY mask-detector-image.py .
COPY cfg cfg

