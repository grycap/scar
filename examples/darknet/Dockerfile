FROM bitnami/minideb

COPY darknet.tar.gz /tmp/ 

RUN tar xvzf /tmp/darknet.tar.gz -C /opt/ \
  && rm /tmp/darknet.tar.gz

RUN apt-get update \
  && apt-get install -y --no-install-recommends wget ca-certificates \
  && wget https://pjreddie.com/media/files/yolo.weights -P /opt/darknet/ \
  && apt-get remove -y wget ca-certificates \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*