FROM ubuntu:latest

RUN apt-get update && apt-get install -y wget \    
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system scar && adduser --system --group scar

RUN wget https://github.com/grycap/scar/releases/download/v1.0.0/scar -O /usr/bin/scar \
 && chmod +x /usr/bin/scar

USER scar

ENV SCAR_LOG_PATH ~/

ENTRYPOINT ["/usr/bin/scar"]


