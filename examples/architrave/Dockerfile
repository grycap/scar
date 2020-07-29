FROM debian:stretch-slim

ARG ADD_BASE_DIR_ARCHITRAVE=scar/examples/architrave
ARG ADD_PRIVATE_BASE_DIR=architrave
ARG SSHDIR=/root/.ssh
ARG BUILD_PACKAGES=' wget make gcc g++ iproute2 cmake  build-essential gfortran curl unzip '

ENV ADD_PRIVATE_BASE_DIR=${ADD_PRIVATE_BASE_DIR}
ENV ADD_BASE_DIR_ARCHITRAVE=${ADD_BASE_DIR_ARCHITRAVE}

ENV EXAMPLE_FILE=/opt/examples/example
ENV TMP_OUTPUT_DIR=/tmp
ENV APP_BIN=/opt/simest
ENV APP_PARAMS=""
ENV MPI_PARAMS='-np 1 --debug-daemons'
ENV JOB_DIR /root/exec/
ENV SCRATCH_DIR /root/scratch
ENV NOTVISIBLE "in users profile"
ENV VERSION=1.7
ENV DEBIAN_FRONTEND=noninteractive
## Set to either lambda or batch
ENV EXEC_TYPE=lambda
ENV AWS_ACCESS_KEY=''
ENV AWS_SECRET_ACCESS_KEY=''
ENV AWS_REGION='us-east-1'
ENV AWS_OUTPUT='json'

# ADD http://launchpadlibrarian.net/265139591/wget_1.13.4-2ubuntu1.4_amd64.deb \
#   http://launchpadlibrarian.net/280581005/libidn11_1.23-2ubuntu0.1_amd64.deb \
#   http://launchpadlibrarian.net/304494179/libssl1.0.0_1.0.1-4ubuntu5.39_amd64.deb \
#   http://launchpadlibrarian.net/312073165/multiarch-support_2.15-0ubuntu10.18_amd64.deb \
#   http://launchpadlibrarian.net/365856917/libc6-dev_2.27-3ubuntu1_amd64.deb \
#   http://launchpadlibrarian.net/365856930/libc-dev-bin_2.27-3ubuntu1_amd64.deb \
#   http://launchpadlibrarian.net/367128628/linux-libc-dev_4.15.0-20.21_amd64.deb \
ADD  ${ADD_PRIVATE_BASE_DIR} ${ADD_BASE_DIR_ARCHITRAVE}/run_batch.sh ${ADD_BASE_DIR_ARCHITRAVE}/mpi-run.sh ${ADD_BASE_DIR_ARCHITRAVE}/debs.lst /opt/

RUN apt-get update \
  && apt-get install -y $BUILD_PACKAGES \
  && wget -q --no-check-certificate -qO- https://download.open-mpi.org/release/open-mpi/v1.4/openmpi-1.4.3.tar.bz2 | tar xvfj - -C /tmp/ \
  && cd /tmp/openmpi-1.4.3/ \
  && ./configure --disable-pty-support \
  && make -j8 \
  && make install \
  && wget -q -P /tmp -i /opt/debs.lst  \
  && apt-get remove --purge -y $BUILD_PACKAGES gnupg* gnupg-agent* \
  && apt-get autoremove --purge -y \
  # && apt-get purge $(dpkg-query -Wf '${Package;-40}${Priority}\n' |  awk '$2 ~ /optional|extra/ { print $1 }') \
  # && apt-get install -y openssh-server openssh-client bash groff less \
  # dpkg -i /opt/libc6-dev* /opt/libc-dev-bin* /opt/linux-libc-dev* \
  # && dpkg -i --force-all /opt/*.deb \
  && dpkg --force-all -i /tmp/*.deb \
  # && apt-get remove --allow-remove-essential --purge -y $BUILD_PACKAGES $(apt-mark showauto) \
  && ulimit -n 1024 \
  && rm -rf /tmp/* /var/lib/apt/lists/* \
  && chmod 755 /opt/mpi-run.sh \
  && chmod 755 /opt/run_batch.sh \
  && chmod 755 ${APP_BIN}


CMD /opt/run_batch.sh
