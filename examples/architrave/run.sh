#!/bin/bash

echo "Build date: $(cat  /build_date)"
echo "Runing as: ${USER} home @ ${HOME}"

if [ "${EXEC_TYPE,,}" = 'lambda' ]; then
  export OMPI_MCA_plm_rsh_agent=/bin/false
  { time mpirun ${MPI_PARAMS} ${APP_BIN} ${APP_PARAMS}; } 2>&1 | cat > $TMP_OUTPUT_DIR/time.log

elif [ "${EXEC_TYPE,,}" = 'batch' ]; then

# The following comment line will be replaced with the necessary env vars:
#=ENV_VARS=
  export AWS_BATCH_EXIT_CODE_FILE=~/batch_exit_code.file
  echo "Running on node index $AWS_BATCH_JOB_NODE_INDEX out of $AWS_BATCH_JOB_NUM_NODES nodes"
  echo "Master node index is $AWS_BATCH_JOB_MAIN_NODE_INDEX and its IP is $AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS"
  
  cd /tmp
  wget -nc https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip
	unzip awscli-exe-linux-x86_64.zip
	chmod +x aws/install
	./aws/install
	
	/usr/local/bin/aws configure set default.s3.max_concurrent_requests 30
	/usr/local/bin/aws configure set default.s3.max_queue_size 10000
	/usr/local/bin/aws configure set default.s3.multipart_threshold 64MB
	/usr/local/bin/aws configure set default.s3.multipart_chunksize 16MB
	/usr/local/bin/aws configure set default.s3.max_bandwidth 4096MB/s
	/usr/local/bin/aws configure set default.s3.addressing_style path
	
	
	mkdir -p ${S3_BATCH_MNT}/deps
	mkdir -p ${S3_BATCH_MNT}/exec
	rm -rf ${S3_BATCH_MNT}/exec/*
	mkdir -p ${S3_BATCH_MNT}/output
	rm -rf ${S3_BATCH_MNT}/output/*
	mkdir -p ${S3_BATCH_MNT}/mpi
	rm -rf ${S3_BATCH_MNT}/mpi/*
	/usr/local/bin/aws s3 cp s3://scar-architrave/batch/private.7z ${S3_BATCH_MNT}
	/usr/local/bin/aws s3 cp s3://scar-architrave/batch/deps.tar.gz ${S3_BATCH_MNT}
	tar -zxf ${S3_BATCH_MNT}/deps.tar.gz -C ${S3_BATCH_MNT}/deps

  #rm -rf /mnt/batch/exec/*
  #rm -rf /mnt/batch/output/*
  #rm -rf /mnt/batch/mpi/*

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

  echo "Running app"
  /opt/mpi-run.sh

else
  echo "ERROR: unknown execution type '${EXEC_TYPE}'"
  exit 1 # terminate and indicate error
fi
