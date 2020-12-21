FROM debian:stretch-slim

ARG ADD_BASE_DIR=examples/mpi
ARG BUILD_PACKAGES=' wget locales git make gcc g++ iproute2 cmake  build-essential gfortran curl  '

ENV DEBIAN_FRONTEND=noninteractive
## Set to either lambda or batch
ENV EXEC_TYPE=lambda

ENV APP_PARAMS=""
ENV GIT_REPO=https://github.com/mpitutorial/mpitutorial
ENV GIT_REPO_REL_PATH_SRC=mpitutorial/tutorials/mpi-hello-world/code
ENV GIT_REPO_REL_PATH_EXEC=mpitutorial/tutorials/mpi-hello-world/code/mpi_hello_world
ENV APP_BIN=/opt/$GIT_REPO_REL_PATH_EXEC
ENV SSH_PRIV_FILE_KEY=ssh_host_rsa_key
ENV SSH_PUB_FILE_KEY=ssh_host_rsa_key.pub

ENV LANG en_US.UTF-8

ADD ${ADD_BASE_DIR}/run.sh  ${ADD_BASE_DIR}/debs.lst  /opt/

RUN apt-get update \
  && apt-get install -y $BUILD_PACKAGES \
  && locale-gen en_US.UTF-8 \
  && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
  && dpkg-reconfigure --frontend=noninteractive locales \
  && update-locale LANG=en_US.UTF-8 \
  && wget -q --no-check-certificate -qO- https://download.open-mpi.org/release/open-mpi/v1.4/openmpi-1.4.3.tar.bz2 | tar xvfj - -C /tmp/ \
  && cd /tmp/openmpi-1.4.3/ \
  && ./configure --disable-pty-support --disable-doc \
  && make -j`nproc` \
  && make install \
  && ldconfig \
  #&& wget -q -P /tmp -i /opt/debs.lst \
  && cd /opt/ \
  && git clone $GIT_REPO \
  && cd /opt/$GIT_REPO_REL_PATH_SRC \
  && make \
  && apt-get remove --purge -y $BUILD_PACKAGES gnupg* gnupg-agent* \
  && apt-get autoremove --purge -y \
  #&& dpkg --force-all -i /tmp/*.deb \
  && rm -rf /tmp/* /var/lib/apt/lists/* \
  && ulimit -n 1024 \
  && chmod 755 /opt/$GIT_REPO_REL_PATH_EXEC \
  && chmod 755 /opt/run.sh \
  && echo $(date) > /build_date \
  && echo "Build date: $(cat  /build_date)"


CMD /opt/run.sh
