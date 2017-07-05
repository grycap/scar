FROM bitnami/minideb

COPY system /opt/darknet/

RUN apt-get update \
  && apt-get install -y --no-install-recommends wget ca-certificates \
  && wget https://pjreddie.com/media/files/yolo.weights -P /opt/darknet/ \
  && apt-get remove -y wget ca-certificates \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* 

