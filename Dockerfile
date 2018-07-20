FROM grycap/jenkins:ubuntu14.04-git as builder

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    zip \
    python3 \
    python3-pip \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system scar && adduser --system --group scar

RUN git clone --branch update-dockerfile https://github.com/grycap/scar /home/scar/code
WORKDIR /home/scar/code
RUN pip3 install -r requirements.txt \
 && pip3 install pyinstaller
RUN chown -R scar:scar /home/scar/code

USER scar
RUN pyinstaller --onefile src/providers/aws/cloud/lambda/udockerb.py
RUN pyinstaller --onefile \
  --add-data="src/providers/aws/cloud/lambda/scarsupervisor.py:src/providers/aws/cloud/lambda" \
  --add-data="src/providers/aws/cloud/lambda/__init__.py:src/providers/aws/cloud/lambda" \
  --add-data="src/exceptions.py:src" \
  --add-data="src/utils.py:src" \
  --add-data="src/providers/aws/cloud/lambda/udocker-1.1.0-RC2.tar.gz:src/providers/aws/cloud/lambda" \
  --add-binary="dist/udockerb:src/providers/aws/cloud/lambda" \
  --add-binary="/usr/bin/curl:src/bin" \
  --add-binary="/usr/bin/zip:src/bin" \
  scar.py


FROM ubuntu:latest
RUN addgroup --system scar && adduser --system --group scar
USER scar
WORKDIR /home/scar/
COPY --from=builder /home/scar/code/dist/scar .
ENV SCAR_LOG_PATH=/home/scar/
ENTRYPOINT ["./scar"]
