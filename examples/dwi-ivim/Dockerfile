FROM bitnami/minideb

RUN apt-get update \
  && apt-get install -y libgomp1 \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY modeloIVIM /opt/dwi/
