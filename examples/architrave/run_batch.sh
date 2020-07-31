#!/bin/bash

if [ "${EXEC_TYPE,,}" = 'lambda' ]; then
  export OMPI_MCA_plm_rsh_agent=/bin/false
  mpirun ${MPI_PARAMS} ${APP_BIN} ${APP_PARAMS}

elif [ "${EXEC_TYPE,,}" = 'batch' ]; then

  wget -q -P /tmp https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip
  unzip -q -d /tmp /tmp/awscli-exe-linux-x86_64.zip
  /tmp/aws/install
  echo "Version of dist: ${VERSION}"
  mkdir ~/.aws/
  ## S3 OPTIMIZATION
  aws configure set default.s3.max_concurrent_requests 30
  aws configure set default.s3.max_queue_size 10000
  aws configure set default.s3.multipart_threshold 64MB
  aws configure set default.s3.multipart_chunksize 16MB
  aws configure set default.s3.max_bandwidth 4096MB/s
  aws configure set default.s3.addressing_style path
  printf '%s\n' '[default]' "aws_access_key_id=${AWS_ACCESS_KEY}" "aws_secret_access_key=${AWS_SECRET_ACCESS_KEY}" > ~/.aws/credentials
  printf '%s\n' '[default]' "region=${AWS_REGION}" "output=${AWS_OUTPUT}" > ~/.aws/config
  #aws s3 cp $S3_INPUT/common $SCRATCH_DIR
  chmod +x ${SCRATCH_DIR}/simest
  ## Install ssh from S3
  mkdir /tmp/deps_batch
  aws cli cp ${S3_INPUT}/batch /tmp/batch
  dpkg -i /tmp/batch/deps/*.deb

  # COnfigure ssh
  sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
  echo "export VISIBLE=now" >> /etc/profile
  echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
  mkdir -p ${SSHDIR}
  touch ${SSHDIR}/sshd_config
  ssh-keygen -t rsa -f ${SSHDIR}/ssh_host_rsa_key -N ''
  cp ${SSHDIR}/ssh_host_rsa_key.pub ${SSHDIR}/authorized_keys
  cp ${SSHDIR}/ssh_host_rsa_key ${SSHDIR}/id_rsa
  echo " IdentityFile ${SSHDIR}/id_rsa" >> /etc/ssh/ssh_config
  echo "Host *" >> /etc/ssh/ssh_config
  echo " StrictHostKeyChecking no" >> /etc/ssh/ssh_config
  chmod -R 600 ${SSHDIR}/*
  chown -R ${USER}:${USER} ${SSHDIR}/
    # check if ssh agent is running or not, if not, run
  eval `ssh-agent -s`
  ssh-add ${SSHDIR}/id_rsa

  /opt/mpi-run.sh
else
  echo "ERROR: unknown execution type '${EXEC_TYPE}'"
  exit 1 # terminate and indicate error
fi
