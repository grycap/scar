FROM debian:stretch-slim

ARG ADD_BASE_DIR_ARCHITRAVE=examples/mpi-example
ARG ADD_PRIVATE_BASE_DIR
ARG BUILD_PACKAGES=' git make gcc g++ iproute2 cmake  build-essential gfortran curl '

ENV DEBIAN_FRONTEND=noninteractive
## Set to either lambda or batch
ENV EXEC_TYPE=lambda

ENV APP_PARAMS=""
ENV MPI_PARAMS='-np 1 --debug-daemons --allow-run-as-root'
ENV GIT_REPO=https://github.com/mpitutorial/mpitutorial
ENV GIT_REPO_REL_PATH_SRC=mpitutorial/tutorials/mpi-hello-world/code
ENV GIT_REPO_REL_PATH_EXEC=mpitutorial/tutorials/mpi-hello-world/code/mpi_hello_world
ENV APP_BIN=/opt/$GIT_REPO_REL_PATH_EXEC
ENV SSH_PRIV_FILE_KEY=ssh_host_rsa_key
ENV SSH_PUB_FILE_KEY=ssh_host_rsa_key.pub

ADD  ${ADD_BASE_DIR_ARCHITRAVE}/run.sh ${ADD_BASE_DIR_ARCHITRAVE}/mpi-run.sh /opt/

RUN apt-get update \
  && apt-get install -y $BUILD_PACKAGES openmpi-bin libopenmpi-dev locales \
  && locale-gen en_US.UTF-8 \
  && cd /opt/ \
  && git clone $GIT_REPO \
  && cd /opt/$GIT_REPO_REL_PATH_SRC \
  && make \
  && apt-get remove --purge -y $BUILD_PACKAGES gnupg* gnupg-agent* \
  && apt-get autoremove --purge -y \
  && ulimit -n 1024 \
  && chmod 755 /opt/$GIT_REPO_REL_PATH_EXEC \
  && chmod 755 /opt/mpi-run.sh \
  && chmod 755 /opt/run.sh \
  && echo $(date) > /build_date \
  && echo "Build date: $(cat  /build_date)"

CMD /opt/run.sh
