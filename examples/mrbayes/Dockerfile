FROM ubuntu:14.04
MAINTAINER Amanda Calatrava <amcaar@i3m.upv.es>

ENV LD_LIBRARY_PATH /usr/local/lib

# Package and dependencies to install MrBayes (including MPI and BEAGLE)
RUN apt-get update && apt-get install -y \
    build-essential \
    autoconf \
    automake \ 
    libtool \
    subversion \
    pkg-config \
    openjdk-6-jdk \
    git \
    wget \
    openmpi-bin \
    openmpi-doc \
    libopenmpi-dev

RUN git clone --depth=1 https://github.com/beagle-dev/beagle-lib.git && \
    cd beagle-lib && \ 
    ./autogen.sh && \
    ./configure --prefix=/usr/local/ && \
    make install

RUN wget http://sourceforge.net/projects/mrbayes/files/mrbayes/3.2.6/mrbayes-3.2.6.tar.gz -O /tmp/mrbayes-3.2.6.tar.gz && \
    cd /tmp && \
    tar zxvf mrbayes-3.2.6.tar.gz  && \
    cd /tmp/mrbayes-3.2.6/src && \
    autoconf && \
    ./configure --enable-mpi=yes && \
    make && \
    make install

ADD mrbayes-sample-run.sh /tmp

