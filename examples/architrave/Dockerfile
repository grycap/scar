FROM debian:stretch-slim

ARG ADD_BASE_DIR_ARCHITRAVE=./
ARG ADD_PRIVATE_BASE_DIR
ARG BUILD_PACKAGES=' make gcc g++ iproute2 cmake  build-essential gfortran curl '


ENV VERSION=1.8
ENV DEBIAN_FRONTEND=noninteractive
## Set to either lambda or batch
ENV EXEC_TYPE=lambda
ENV SSHDIR=/root/.ssh

ENV EXAMPLE_FILE=/opt/examples/example
ENV TMP_OUTPUT_DIR=/tmp
ENV APP_BIN=/opt/simest
ENV APP_PARAMS=""
ENV MPI_PARAMS='-np 1 --debug-daemons'
ENV JOB_DIR=/root/exec/
ENV SCRATCH_DIR=/root/scratch
ENV AWS_ACCESS_KEY=''
ENV AWS_SECRET_ACCESS_KEY=''
ENV AWS_REGION='us-east-1'
ENV AWS_OUTPUT='json'
ENV S3_BUCKET="s3://scar-architrave"
ENV S3_BATCH_DEPS_REL_PATH=batch/deps.tar.gz
ENV S3_BATCH_PRIVATE_REL_PATH=<none>
ENV PRIVATE_PASSWD=<none>
ENV S3_BATCH_MNT=/mnt/batch

ADD  ${ADD_PRIVATE_BASE_DIR} ${ADD_BASE_DIR_ARCHITRAVE}/run.sh ${ADD_BASE_DIR_ARCHITRAVE}/mpi-run.sh ${ADD_BASE_DIR_ARCHITRAVE}/debs.lst

RUN apt-get update \
  && apt-get install -y $BUILD_PACKAGES wget p7zip-full \
  && wget -q --no-check-certificate -qO- https://download.open-mpi.org/release/open-mpi/v1.4/openmpi-1.4.3.tar.bz2 | tar xvfj - -C /tmp/ \
  && cd /tmp/openmpi-1.4.3/ \
  && ./configure --disable-pty-support --disable-doc \
  && make -j8 \
  && make install \
  && wget -q -P /tmp -i /opt/debs.lst  \
  && apt-get remove --purge -y $BUILD_PACKAGES gnupg* gnupg-agent* \
  && apt-get autoremove --purge -y \
  && dpkg --force-all -i /tmp/*.deb \
  && ulimit -n 1024 \
  && rm -rf /tmp/* /var/lib/apt/lists/* \
  && chmod 755 /opt/mpi-run.sh \
  && chmod 755 /opt/run.sh

CMD /opt/run.sh
