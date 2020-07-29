# architrave
Running a commercial app in a Docker container on Lambda and Batch

You can ignore everything but the private files and those from ##scar/examples/architrave## by creating a `.dockerignore` file in the root of the context with the following content:

```
# Ignore everything
**

# Allow files and directories
!/architrave/**
!/scar/examples/architrave/**

# Ignore unnecessary files inside allowed directories
# This should go after the allowed directories
**/scar-architrave-batch.yaml
**/scar-architrave-lambda.yaml
**/README.md
**/LICENSE
```
