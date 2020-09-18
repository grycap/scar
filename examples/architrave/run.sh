#!/bin/bash

echo "Build date: $(cat  /build_date)"

if [ "${EXEC_TYPE,,}" = 'lambda' ]; then
  export OMPI_MCA_plm_rsh_agent=/bin/false
  mpirun ${MPI_PARAMS} ${APP_BIN} ${APP_PARAMS}

elif [ "${EXEC_TYPE,,}" = 'batch' ]; then

# The following comment line will be replaced with the necessary env vars:
#=ENV_VARS=

  export AWS_BATCH_EXIT_CODE_FILE=~/batch_exit_code.file
  echo "Running on node index $AWS_BATCH_JOB_NODE_INDEX out of $AWS_BATCH_JOB_NUM_NODES nodes"
  echo "Master node index is $AWS_BATCH_JOB_MAIN_NODE_INDEX and its IP is $AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS"

  mkdir ${SCRATCH_DIR}
  mkdir ${JOB_DIR}
  mkdir ${S3_BATCH_MNT}/output
  dpkg -i ${S3_BATCH_MNT}/deps/*.deb

  echo "Add private data from S3"
  7z x -aoa -p${PRIVATE_PASSWD} -o/opt ${S3_BATCH_MNT}/*.7z

  echo "Configure ssh"
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

  chmod +x ${APP_BIN}

  echo "Running app"
  /opt/mpi-run.sh

else
  echo "ERROR: unknown execution type '${EXEC_TYPE}'"
  exit 1 # terminate and indicate error
fi
