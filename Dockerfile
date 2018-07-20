FROM grycap/jenkins:ubuntu14.04-git as ubuilder
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    python3 \
    python3-pip \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
RUN pip3 install pyinstaller 
RUN wget https://raw.githubusercontent.com/grycap/scar/master/src/providers/aws/cloud/lambda/udockerb.py
RUN pyinstaller --onefile \
  --add-binary="/usr/bin/curl:src/bin" \
  udockerb.py

FROM ubuntu:latest as sbuilder
RUN apt-get update && apt-get install -y \
    zip \
    git \
    python3 \
    python3-pip \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
RUN git clone --branch update-dockerfile https://github.com/grycap/scar
WORKDIR /scar
RUN pip3 install -r requirements.txt \
 && pip3 install pyinstaller urllib3 configparser
COPY --from=ubuilder /dist/udockerb /scar/
RUN pyinstaller --onefile \
  --add-data="src/providers/aws/cloud/lambda/scarsupervisor.py:src/providers/aws/cloud/lambda" \
  --add-data="src/providers/aws/cloud/lambda/__init__.py:src/providers/aws/cloud/lambda" \
  --add-data="src/exceptions.py:src" \
  --add-data="src/utils.py:src" \
  --add-data="src/providers/aws/cloud/lambda/udocker-1.1.0-RC2.tar.gz:src/providers/aws/cloud/lambda" \
  --add-binary="udockerb:src/providers/aws/cloud/lambda" \
  --add-binary="/usr/bin/zip:src/bin" \
  --hidden-import=urllib3 \
  --hidden-import=configparser \
  scar.py


FROM ubuntu:latest
RUN addgroup --system scar && adduser --system --group scar
USER scar
WORKDIR /home/scar/
COPY --from=sbuilder /scar/dist/scar /usr/bin/
ENV SCAR_LOG_PATH=/home/scar/
ENTRYPOINT ["/usr/bin/scar"]
