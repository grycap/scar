# Uncomment PRIVATE_PASSWD, AWS_BATCH_JOB_NUM_NODES,AWS_BATCH_JOB_NODE_INDEX, and AWS_BATCH_JOB_MAIN_NODE_INDEX when running batch on single node
# export AWS_BATCH_JOB_NUM_NODES=1
# export AWS_BATCH_JOB_NODE_INDEX=0
# export AWS_BATCH_JOB_MAIN_NODE_INDEX=0

export PRIVATE_PASSWD=''
export APP_PARAMS1=''
export APP_PARAMS2=''
export APP_BIN=''
export APP_IN_FILE=''
bash /opt/run.sh
