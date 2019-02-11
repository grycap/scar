FROM ubuntu:latest
RUN addgroup --system scar && adduser --system --group scar
USER scar
WORKDIR /home/scar/
COPY --from=sbuilder /scar/dist/scar /usr/bin/
ENV SCAR_LOG_PATH=/home/scar/
