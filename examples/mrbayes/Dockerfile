FROM ubuntu:14.04
MAINTAINER Amanda Calatrava <amcaar@i3m.upv.es>

ENV LD_LIBRARY_PATH /usr/local/lib

# Package and dependencies to install MrBayes (including MPI and BEAGLE)
RUN apt-get update && apt-get install -y \    
    autoconf \
    make \ 
    gcc  \    
    wget

RUN wget http://sourceforge.net/projects/mrbayes/files/mrbayes/3.2.6/mrbayes-3.2.6.tar.gz -O /tmp/mrbayes-3.2.6.tar.gz && \
    cd /tmp && \
    tar zxvf mrbayes-3.2.6.tar.gz  && \
    cd /tmp/mrbayes-3.2.6/src && \
    autoconf && \
    ./configure --with-beagle=no && \
    make && \
    make install

ADD mrbayes-sample-run.sh /tmp

