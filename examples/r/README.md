# Running R on AWS Lambda

You can run the software environment for statistical computing [R](https://www.r-project.org/) in AWS Lambda via [SCAR](https://github.com/grycap/scar) using the [grycap/r-base-lambda](https://hub.docker.com/r/grycap/r-base-lambda/) Docker image, based on the [debian:stretch-slim](https://hub.docker.com/_/debian/) one.

## Usage on AWS Lambda via SCAR

You can run a container out of this image on AWS Lambda via SCAR using the following procedure:

1. Create the Lambda function

```sh
scar init -i grycap/r-base-lambda
```

2. Execute the Lambda function with an script to compile and run R commands

```sh
scar run -s examples/r/r-demo.sh -n scar-grycap-r-base-lambda
```

The first invocation will take considerably longer than the subsequent ones, where the container will be cached. You can modify the script and perform another `scar run`.

You can also run multiple concurrent invocations of this Lambda function to perform highly-parallel event-driven processing. See the [SCAR Programming Model](https://github.com/grycap/scar/blob/master/README.md#programming-model).

## Appendix. How to create a minimalistic package for R

TL;DR;

R will be installed on a debian:stretch-slim Docker container. The R executable together with the dependent dynamic libraries will be packaged as a compressed file, that later will be deployed in a new container (when building the image in Docker Hub).

### Step-by-step procedure

The installation is inspired on [this one]( https://aws.amazon.com/es/blogs/compute/analyzing-genomics-data-at-scale-using-r-aws-lambda-and-amazon-api-gateway/), with the following changes:

* Adapted to Python 3.
* Debian-based installation.
* Changes in R script to use the R_HOME environment variable.

1. Deploy a Docker container out of the debian:stretch-slim image:

```sh
docker run -ti --name rlang-deb-slim debian:stretch-slim bash
```

2. Install the required packages inside the container

```sh
apt-get install -y python3 gcc gcc  libgfortran3 python3-pip r-base wget liblapack3 zip
````

3. Install virtualenv and the Survival R package

```sh
pip3 install virtualenv
wget https://cran.r-project.org/src/contrib/Archive/survival/survival_2.39-4.tar.gz
R CMD INSTALL survival_2.39-4.tar.gz
```

4. Create a virtualenv and install [rpy2](https://rpy2.bitbucket.io/), to use R from python (not strictly necessary for SCAR).

```sh
cd
virtualenv ~/env && source ~/env/bin/activate
pip3 install rpy2
```

5. Create the package that includes the executable together with the libraries.

You can use `ldd` to find out the dynamic libraries required by the R executable file:

```sh
ldd /usr/lib/R/bin/exec/R
    linux-vdso.so.1 (0x00007ffdd39fc000)
    libR.so => /usr/lib/libR.so (0x00007fe713e62000)
    libgomp.so.1 => /usr/lib/x86_64-linux-gnu/libgomp.so.1 (0x00007fe713c35000)
    libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007fe713a18000)
    libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007fe713679000)
    libblas.so.3 => /usr/lib/libblas.so.3 (0x00007fe71340c000)
    libgfortran.so.3 => /usr/lib/x86_64-linux-gnu/libgfortran.so.3 (0x00007fe7130e6000)
    libm.so.6 => /lib/x86_64-linux-gnu/libm.so.6 (0x00007fe712de2000)
    libquadmath.so.0 => /usr/lib/x86_64-linux-gnu/libquadmath.so.0 (0x00007fe712ba3000)
    libreadline.so.7 => /lib/x86_64-linux-gnu/libreadline.so.7 (0x00007fe712956000)
    libpcre.so.3 => /lib/x86_64-linux-gnu/libpcre.so.3 (0x00007fe7126e3000)
    liblzma.so.5 => /lib/x86_64-linux-gnu/liblzma.so.5 (0x00007fe7124bd000)
    libbz2.so.1.0 => /lib/x86_64-linux-gnu/libbz2.so.1.0 (0x00007fe7122ad000)
    libz.so.1 => /lib/x86_64-linux-gnu/libz.so.1 (0x00007fe712093000)
    librt.so.1 => /lib/x86_64-linux-gnu/librt.so.1 (0x00007fe711e8b000)
    libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2 (0x00007fe711c87000)
    libicuuc.so.57 => /usr/lib/x86_64-linux-gnu/libicuuc.so.57 (0x00007fe7118df000)
    libicui18n.so.57 => /usr/lib/x86_64-linux-gnu/libicui18n.so.57 (0x00007fe711465000)
    /lib64/ld-linux-x86-64.so.2 (0x00007fe714684000)
    libgcc_s.so.1 => /lib/x86_64-linux-gnu/libgcc_s.so.1 (0x00007fe71124e000)
    libtinfo.so.5 => /lib/x86_64-linux-gnu/libtinfo.so.5 (0x00007fe711024000)
    libicudata.so.57 => /usr/lib/x86_64-linux-gnu/libicudata.so.57 (0x00007fe70f5a7000)
    libstdc++.so.6 => /usr/lib/x86_64-linux-gnu/libstdc++.so.6 (0x00007fe70f225000)
```

Create a directory for the files and copy R inside:

```sh
mkdir $HOME/lambda && cd $HOME/lambda
cp -Lr /usr/lib/R/* $HOME/lambda/
cp $HOME/lambda/bin/exec/R $HOME/lambda
```

Do not forget the `-L` options in order to follow the symlinks when copying the files.

Copy the required libraries:

```sh
cp  /usr/lib/R/lib/libR.so $HOME/lambda/lib/
cp  /usr/lib/x86_64-linux-gnu/libgomp.so.1 $HOME/lambda/lib
cp  /lib/x86_64-linux-gnu/libpthread.so.0 $HOME/lambda/lib
cp  /usr/lib/libblas.so.3 $HOME/lambda/lib 
cp /usr/lib/x86_64-linux-gnu/libgfortran.so.3 $HOME/lambda/lib
cp  /usr/lib/x86_64-linux-gnu/libquadmath.so.0 $HOME/lambda/lib 
cp /lib/x86_64-linux-gnu/libreadline.so.7 $HOME/lambda/lib 
cp /lib/x86_64-linux-gnu/libpcre.so.3 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/liblzma.so.5 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/libbz2.so.1.0 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/libz.so.1 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/librt.so.1 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/libdl.so.2 $HOME/lambda/lib
cp /usr/lib/x86_64-linux-gnu/libicuuc.so.57 $HOME/lambda/lib
cp /usr/lib/x86_64-linux-gnu/libicui18n.so.57 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/libgcc_s.so.1 $HOME/lambda/lib
cp /lib/x86_64-linux-gnu/libtinfo.so.5 $HOME/lambda/lib
cp /usr/lib/x86_64-linux-gnu/libicudata.so.57 $HOME/lambda/lib
cp /usr/lib/x86_64-linux-gnu/libstdc++.so.6 $HOME/lambda/lib
cp /usr/lib/lapack/liblapack.so.3 $HOME/lambda/lib
```

Add the Python libraries to that folder

```sh
cp -r /root/env/lib/python3.5/site-packages/ $HOME/lambda
```

Modify the `/root/lambda/bin/R` shell-script file so that:

```sh
R_HOME_DIR=$R_HOME
```

This is required in order to later be able to start R from that folder.

6. Create the deployment package

```sh
cd $HOME/lambda
tar czvf /tmp/rlang-debslim.tgz *
```

7. (Optional) Test the application

Once the `rlang-debslim.tgz` file has been decompressed in another machine, you can run the application by defining the appropriate environment variables and then executing R, as follows:

```sh
export R_HOME=$HOME
export LD_LIBRARY_PATH=$HOME/lib
export PATH=$PATH:$HOME/bin
R
```
