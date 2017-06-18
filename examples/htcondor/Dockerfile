#Original file from https://github.com/DS-CNAF/htcondor-docker-centos/tree/master
#Modified by Germán Moltó (gmolto@dsic.upv.es) to add support for SCAR
#All the credit goes to the original developers.
FROM centos:7
MAINTAINER Matteo Panella <matteo.panella@cnaf.infn.it>
ENV TINI_VERSION v0.9.0

COPY files/htcondor-stable-rhel7.repo /etc/yum.repos.d/

RUN set -ex \
        && mkdir -p /var/run/lock \
        && yum makecache fast \
        && yum --disablerepo=htcondor-stable -y install wget epel-release \
        && wget -qO /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor http://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor \
        && rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor \
        && wget -qO /sbin/tini https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini \
        && chmod +x /sbin/tini \
        && yum -y remove wget \
        && yum -y install condor supervisor \
        && yum clean all

COPY files/supervisord.conf /etc/supervisord.conf
COPY files/condor.ini /etc/supervisord.d/condor.ini
COPY files/condor-wrapper.sh /usr/local/sbin/condor-wrapper.sh
COPY files/condor_config /etc/condor/condor_config
COPY files/run.sh /usr/local/sbin/run.sh

#ENTRYPOINT ["/sbin/tini", "--", "/usr/local/sbin/run.sh"]
ENTRYPOINT ["/usr/local/sbin/run.sh"]
