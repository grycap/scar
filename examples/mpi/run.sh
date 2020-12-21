#!/bin/bash
echo "Executing as AWS ${EXEC_TYPE}"
echo "Build date: $(cat  /build_date)"
echo "Runing as: ${USER} home @ ${HOME}"
echo "Running with interpreter: $(readlink -f $(which sh))"
echo "Running MPI binary: ${APP_BIN}"

log () {
  echo "${BASENAME} - ${1}"
}

# Standard function to print an error and exit with a failing return code
error_exit () {
  log "${BASENAME} - ${1}" >&2
  log "${2:-1}" > $AWS_BATCH_EXIT_CODE_FILE
  kill  $(cat /tmp/supervisord.pid)
}

usage () {
  if [ "${#@}" -ne 0 ]; then
    log "* ${*}"
    log
  fi
  cat <<ENDUSAGE
Usage:
export AWS_BATCH_JOB_NODE_INDEX=0
export AWS_BATCH_JOB_NUM_NODES=10
export AWS_BATCH_JOB_MAIN_NODE_INDEX=0
export AWS_BATCH_JOB_ID=string
./mpi-run.sh
ENDUSAGE

  error_exit
}

# wait for all nodes to report
wait_for_nodes () {
  log "Running as master node"

  touch $HOST_FILE_PATH
  ip=$(/sbin/ip -o -4 addr list eth0 | awk '{print $4}' | cut -d/ -f1)

  if [ -x "$(command -v nvidia-smi)" ] ; then
      NUM_GPUS=$(ls -l /dev/nvidia[0-9] | wc -l)
      availablecores=$NUM_GPUS
  else
      availablecores=$(nproc)
  fi

  log "master details -> $ip:$availablecores"
  echo "$ip slots=$availablecores" >> $HOST_FILE_PATH

  lines=$(sort $HOST_FILE_PATH|uniq|wc -l)
  i=0
  numCyclesWait=30
  while [ "$AWS_BATCH_JOB_NUM_NODES" -gt "$lines" ] && [ "$i" -lt "$numCyclesWait" ]
  do
    log "$lines out of $AWS_BATCH_JOB_NUM_NODES nodes joined, check again in 3 seconds"
    sleep 3
    lines=$(sort $HOST_FILE_PATH|uniq|wc -l)
    ((i=i+1))
  done

  if [ "$i" -eq "$numCyclesWait" ]; then
    echo "children did not join"
    exit 1
  fi

  # Make the temporary file executable and run it with any given arguments
  log "All nodes successfully joined"

  # remove duplicates if there are any.
  awk '!a[$0]++' $HOST_FILE_PATH > ${HOST_FILE_PATH}-deduped
  cat $HOST_FILE_PATH-deduped
  log "executing main MPIRUN workflow"

  { time  mpirun --mca btl_tcp_if_include eth0 --debug-daemons -x PATH -x LD_LIBRARY_PATH --machinefile ${HOST_FILE_PATH}-deduped \
      ${APP_BIN} ${APP_PARAMS}; } 2>&1 | cat > ${TMP_OUTPUT_DIR}/time.log
  sleep 2
  echo 'Exec output:'
  cat ${TMP_OUTPUT_DIR}/time.log

  #if [ "${NODE_TYPE}" = 'main' ]; then
    # env GZIP=-9 tar -czvf $SCRATCH_DIR/batch_output_${AWS_BATCH_JOB_ID}.tar.gz $SCRATCH_DIR/output/*
    # aws s3 cp $SCRATCH_DIR/batch_output_${AWS_BATCH_JOB_ID}.tar.gz $S3_BUCKET/output/batch_output_${AWS_BATCH_JOB_ID}.tar.gz
  #fi

  #log "done! goodbye, writing exit code to $AWS_BATCH_EXIT_CODE_FILE and shutting down my supervisord"
  #echo "0" > $AWS_BATCH_EXIT_CODE_FILE
  #kill  $(cat /tmp/supervisord.pid)
  #echo "#!/bin/bash" > ${S3_BATCH_MNT}/exec/docker_done
  #echo "env GZIP=-9 tar -czvf /mnt/batch/output/result.tar.gz /mnt/batch/output/*" > ${S3_BATCH_MNT}/exec/docker_done
  #echo "/usr/local/bin/aws s3 cp /mnt/batch/output/result.tar.gz s3://scar-architrave/output/result_$(date | tr ' ' _ ).tar.gz" >> ${S3_BATCH_MNT}/exec/docker_done
  log "Signaling children to exit"
  cat ${HOST_FILE_PATH}-deduped | awk -F_ '{print $1}' | xargs -I{} -n1 ssh {} "touch ${BATCH_SIGNAL_DIR}/master_done/done"

  log "Wait for children to finish their execution"
  num_finished=$(ls ${BATCH_SIGNAL_DIR}/workers_done/|uniq|wc -l)
  while [ "$AWS_BATCH_JOB_NUM_NODES" -gt "$((num_finished+1))" ]
  do
    log "$num_finished out of $AWS_BATCH_JOB_NUM_NODES nodes are done, check again in 1 second"
    sleep 1
    num_finished=$(ls ${BATCH_SIGNAL_DIR}/workers_done/|uniq|wc -l)
  done

  #while inotifywait ${S3_BATCH_MNT}/exec -e create; do { echo "EC2 host post-execution process completed, exiting container"; break; }; done
  exit 0
}

# Fetch and run a script
report_to_master () {
  # get own ip and num cpus
  #
  ip=$(/sbin/ip -o -4 addr list eth0 | awk '{print $4}' | cut -d/ -f1)

  if [ -x "$(command -v nvidia-smi)" ] ; then
      NUM_GPUS=$(ls -l /dev/nvidia[0-9] | wc -l)
      availablecores=$NUM_GPUS
  else
      availablecores=$(nproc)
  fi

  log "I am a child node -> $ip:$availablecores, reporting to the master node -> ${AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS}"
#  echo "$ip slots=$availablecores" | ssh ${AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS} "cat >> /$HOST_FILE_PATH" -vvv
#  sleep 15
#  echo "$ip slots=$availablecores" | ssh ${AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS} "cat >> /$HOST_FILE_PATH" -vvv

  until echo "$ip slots=$availablecores" | ssh ${AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS} "cat >> /$HOST_FILE_PATH"
  do
    echo "Sleeping 5 seconds and trying again"
    sleep 5
  done

  echo "Wait for master to finish"
  while inotifywait ${BATCH_SIGNAL_DIR}/master_done -e create; do { echo "Child ${ip} has finished its execution, done! goodbye"; break; }; done
  ssh ${AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS} "touch ${BATCH_SIGNAL_DIR}/workers_done/${ip}"
  exit 0
}

if [ "${EXEC_TYPE,,}" = 'lambda' ]; then
  echo 'Run lambda'
  export OMPI_MCA_plm_rsh_agent=/bin/false
  { time mpirun -np 1 --debug-daemons  ${APP_BIN} ${APP_PARAMS}; } 2>&1 | cat > $TMP_OUTPUT_DIR/time.log
  cat $TMP_OUTPUT_DIR/time.log
elif [ "${EXEC_TYPE,,}" = 'batch' ]; then
  echo 'Run batch'

  apt update
  apt install -y inotify-tools iproute2 wget unzip openssh-server openssh-client locales

  locale-gen en_US.UTF-8
  sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
  dpkg-reconfigure --frontend=noninteractive locales
  update-locale LANG=en_US.UTF-8
  wget -nc -nv https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip
  unzip -qq awscli-exe-linux-x86_64.zip
  chmod +x aws/install
  ./aws/install
  /usr/local/bin/aws configure set default.s3.max_concurrent_requests 30
  /usr/local/bin/aws configure set default.s3.max_queue_size 10000
  /usr/local/bin/aws configure set default.s3.multipart_threshold 64MB
  /usr/local/bin/aws configure set default.s3.multipart_chunksize 16MB
  /usr/local/bin/aws configure set default.s3.max_bandwidth 4096MB/s
  /usr/local/bin/aws configure set default.s3.addressing_style path
  /usr/local/bin/aws s3 cp s3://scar-mpi-example/ssh.tar.gz /opt
  cd /opt
  tar -zvxf /opt/ssh.tar.gz

  echo "Configure ssh"
  sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
  echo "export VISIBLE=now" >> /etc/profile
  echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
  mkdir -p ${HOME}/.ssh
  touch ${HOME}/.ssh/sshd_config
  #ssh-keygen -t rsa -f ${SSHDIR}/ssh_host_rsa_key -N ''
  cat /opt/${SSH_PUB_FILE_KEY} > ${HOME}/.ssh/authorized_keys
  cp /opt/${SSH_PRIV_FILE_KEY}  ${HOME}/.ssh/id_rsa
  echo " IdentityFile ${HOME}/.ssh/id_rsa" >> /etc/ssh/ssh_config
  echo "Host *" >> /etc/ssh/ssh_config
  echo " StrictHostKeyChecking no" >> /etc/ssh/ssh_config
  echo "PermitRootLogin without-password" >> /etc/ssh/sshd_config
  #sed -i -e 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config
  #cat /etc/ssh/sshd_config
  chmod -R 600 ${HOME}/.ssh/*
  chown -R ${USER}:${USER} ${HOME}/.ssh/
    # check if ssh agent is running or not, if not, run
  eval `ssh-agent -s`

  chmod +x ${APP_BIN}
  service ssh status
  service ssh restart
  service ssh status
  ssh-add ${HOME}/.ssh/id_rsa
  service ssh restart
#  export AWS_BATCH_JOB_NODE_INDEX=0
#  export AWS_BATCH_JOB_NUM_NODES=1
#  export AWS_BATCH_JOB_MAIN_NODE_INDEX=0

  echo "Running app"

  #/opt/mpi-run.sh


#PATH="$PATH:/opt/openmpi/bin/"
BASENAME="${0##*/}"
HOST_FILE_PATH="/tmp/hostfile"
AWS_BATCH_EXIT_CODE_FILE="/tmp/batch-exit-code"

BATCH_SIGNAL_DIR=/tmp/batch
if [ -d "${BATCH_SIGNAL_DIR}" ]; then rm -Rf ${BATCH_SIGNAL_DIR}; fi
mkdir -p ${BATCH_SIGNAL_DIR}/master_done
mkdir -p ${BATCH_SIGNAL_DIR}/workers_done

#aws s3 cp $S3_INPUT $SCRATCH_DIR
#tar -xvf $SCRATCH_DIR/*.tar.gz -C $SCRATCH_DIR

sleep 2

# Set child by default switch to main if on main node container
NODE_TYPE="child"
if [ "${AWS_BATCH_JOB_MAIN_NODE_INDEX}" == "${AWS_BATCH_JOB_NODE_INDEX}" ]; then
  log "Running synchronize as the main node"
  NODE_TYPE="main"
fi


# Main - dispatch user request to appropriate function
log $NODE_TYPE
case $NODE_TYPE in
  main)
    wait_for_nodes "${@}"
    ;;

  child)
    report_to_master "${@}"
    ;;

  *)                                                                                                                                                                                                                                               log $NODE_TYPE
    usage "Could not determine node type. Expected (main/child)"
    ;;
esac

else
  echo "ERROR: unknown execution type '${EXEC_TYPE}'"
  exit 1 # terminate and indicate error
fi
