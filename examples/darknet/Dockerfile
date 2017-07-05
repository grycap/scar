FROM bitnami/minideb

COPY system /opt/darknet/

RUN apt-get update \
  && apt-get install -y wget \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* 

RUN wget https://pjreddie.com/media/files/yolo.weights -P /opt/darknet/
