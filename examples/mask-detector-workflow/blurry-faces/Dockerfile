FROM python:slim-buster

RUN pip install --no-cache-dir opencv-python numpy tensorflow && \
    rm -rf /root/.cache/pip/* && \
    rm -rf /tmp/*

RUN apt update && \
    apt install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /opt/blurry-faces

WORKDIR /opt/blurry-faces/src

