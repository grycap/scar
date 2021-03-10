FROM debian:stretch-slim

ARG ADD_BASE_DIR_ARCHITRAVE=examples/architrave
ARG ADD_PRIVATE_BASE_DIR
ARG BUILD_PACKAGES=' make gcc g++ iproute2 cmake  build-essential gfortran curl locales '

ENV DEBIAN_FRONTEND=noninteractive
## Set to either lambda or batch
ENV EXEC_TYPE=lambda

ENV APP_IN_FILE=/opt/examples/example
ENV TMP_OUTPUT_DIR=/tmp
ENV APP_BIN=/opt/simest
ENV APP_PARAMS1=""
ENV APP_PARAMS2=""
#ENV S3_BUCKET="s3://scar-architrave"
#ENV S3_BATCH_DEPS_REL_PATH=batch/deps.tar.gz
#ENV S3_BATCH_PRIVATE_REL_PATH=<none>
ENV PRIVATE_PASSWD=<none>

ADD  ${ADD_PRIVATE_BASE_DIR} ${ADD_BASE_DIR_ARCHITRAVE}/run.sh ${ADD_BASE_DIR_ARCHITRAVE}/debs.lst /opt/

RUN apt-get update \
  && apt-get install -y $BUILD_PACKAGES p7zip-full wget unzip \
  && locale-gen en_US.UTF-8 \
  && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
  && dpkg-reconfigure --frontend=noninteractive locales \
  && update-locale LANG=en_US.UTF-8 \
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
  && chmod 755 /opt/run.sh \
  && echo $(date) > /build_date \
  && echo "Build date: $(cat  /build_date)"

CMD /opt/run.sh
