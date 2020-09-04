#!/bin/bash

if [ "${EXEC_TYPE,,}" = 'lambda' ]; then
  export OMPI_MCA_plm_rsh_agent=/bin/false
  mpirun ${MPI_PARAMS} ${APP_BIN} ${APP_PARAMS}

elif [ "${EXEC_TYPE,,}" = 'batch' ]; then

  chmod 755 /opt/run.sh
  /opt/run_batch.sh
else
  echo "ERROR: unknown execution type '${EXEC_TYPE}'"
  exit 1 # terminate and indicate error
fi
