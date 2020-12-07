#!/bin/bash

echo "Build date: $(cat  /build_date)"
echo "Runing as: ${USER} home @ ${HOME}"

if [ "${EXEC_TYPE,,}" = 'lambda' ]; then
  echo 'Run lambda'
  export OMPI_MCA_plm_rsh_agent=/bin/false
  { time mpirun ${MPI_PARAMS} ${APP_BIN} ${APP_PARAMS}; } 2>&1 | cat > $TMP_OUTPUT_DIR/time.log

elif [ "${EXEC_TYPE,,}" = 'batch' ]; then
  echo 'Run batch'

  apt update
  apt install -y openssh-server openssh-client
  echo "Configure ssh"
  sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
  echo "export VISIBLE=now" >> /etc/profile
  echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
  mkdir -p ${HOME}/.ssh
  touch ${HOME}/.ssh/sshd_config
  #ssh-keygen -t rsa -f ${SSHDIR}/ssh_host_rsa_key -N ''
  cat /opt/ssh_host_rsa_key.pub > ${HOME}/.ssh/authorized_keys
  cp /opt/ssh_host_rsa_key  ${HOME}/.ssh/id_rsa
  echo " IdentityFile ${HOME}/.ssh/id_rsa" >> /etc/ssh/ssh_config
  echo "Host *" >> /etc/ssh/ssh_config
  echo " StrictHostKeyChecking no" >> /etc/ssh/ssh_config
  chmod -R 600 ${HOME}/.ssh/*
  chown -R ${USER}:${USER} ${HOME}/.ssh/
    # check if ssh agent is running or not, if not, run
  eval `ssh-agent -s`
  ssh-add ${HOME}/.ssh/id_rsa

  chmod +x ${APP_BIN}
  service ssh status
  service ssh restart
  service ssh status

  export AWS_BATCH_JOB_NODE_INDEX=0
  export AWS_BATCH_JOB_NUM_NODES=1
  export AWS_BATCH_JOB_MAIN_NODE_INDEX=0

  echo "Running app"
  /opt/mpi-run.sh

else
  echo "ERROR: unknown execution type '${EXEC_TYPE}'"
  exit 1 # terminate and indicate error
fi
