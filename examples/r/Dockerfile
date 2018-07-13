FROM debian:stretch-slim
LABEL maintainer="gmolto@dsic.upv.es" 

ENV R_HOME /root
ENV PATH "$PATH:/$R_HOME/bin"
ENV LD_LIBRARY_PATH "$R_HOME/lib"
ADD https://s3.amazonaws.com/scar-public/rlang-debslim.tgz /root
WORKDIR $R_HOME
RUN tar zxvf /root/*.tgz
CMD ["R"]
