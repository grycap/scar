Limitations
===========

Unfortunately the AWS environment imposes several hard limits that are impossible to bypass:

* The Docker container must fit within the current `AWS Lambda limits <http://docs.aws.amazon.com/lambda/latest/dg/limits.html>`_:

  * **Compressed + uncompressed** Docker image under **512 MB** (udocker needs to download the image before uncompressing it).
  * Maximum **execution time of 300 seconds** (5 minutes).

* The following Docker images cannot be currently used:

  * Those based on Alpine Linux (due to the use of MUSL instead of GLIBC, which is not supported by Fakechroot).

* Installation of packages in the user-defined script (i.e. using `yum`, `apt-get`, etc.) is currently not possible.