FROM ubuntu:16.04

# Include global arg in this stage of the build
ARG FUNCTION_DIR="/var/task"
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy function code
COPY awslambdaric ${FUNCTION_DIR}
COPY function_config.yaml ${FUNCTION_DIR}
COPY test.sh ${FUNCTION_DIR}

ENV PATH="${FUNCTION_DIR}:${PATH}"

ENTRYPOINT [ "awslambdaric" ]
CMD [ "faassupervisor.supervisor.main" ]
