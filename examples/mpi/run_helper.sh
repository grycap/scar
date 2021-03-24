# Uncomment AWS_BATCH_JOB_NUM_NODES,AWS_BATCH_JOB_NODE_INDEX, and AWS_BATCH_JOB_MAIN_NODE_INDEX when running batch on single node
# export AWS_BATCH_JOB_NUM_NODES=1
# export AWS_BATCH_JOB_NODE_INDEX=0
# export AWS_BATCH_JOB_MAIN_NODE_INDEX=0

export APP_PARAMS=''
export APP_BIN=''
bash /opt/run.sh
