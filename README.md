# SCAR - Serverless Container-aware ARchitectures

[![Build Status](https://travis-ci.org/grycap/scar.svg?branch=master)](https://travis-ci.org/grycap/scar)
[![License](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# ![SCAR](scar-logo.png)

A complete usage manual can be found in the [main branch of the project](https://github.com/grycap/scar).

## WARNING !!
> This branch is experimental. Use it with caution.
> The ssh functionality was created with the intention of debugging lambda functions.

## Usage

The following commands will create a lambda function that connects to the specified host using a reverse ssh connection:
```
SSH_HOST=ec2-user@25.16.235.145
SSH_PORT=7022
SSH_KEY_PATH=~/.ssh/id_rsa
CONTAINER_IMAGE=bitnami/minideb
scar init -n sshl -sh $SSH_HOST -sp $SSH_PORT -sk $SSH_KEY_PATH $CONTAINER_IMAGE
scar run sshl sleep 50000
```
* In this example we are using an ec2 machine but you can use any machine with the `SSH_PORT` open and an ssh server running.
* The `SSH_KEY_PATH` is the path to the key that lambda is going to be used to create the reverse connection to your machine.
* The lambda function is launched executing an sleep command so the function doesn't finish, but you can execute any script or container allowed by scar. For more information check the [scar webpage](https://grycap.github.io/scar/).

To connect to lambda (in our case from the ec2 machine), you have to execute:
```
ssh -p 7022 scar@localhost
scar@localhost's password:
Welcome to Lambda Shell!
λ >
```
* The ssh user is `scar` and the password is `lambda`.
* The shell and the ssh server are created using the [faassh](https://github.com/smithclay/faassh) library.


## Licensing

SCAR is licensed under the Apache License, Version 2.0. See
[LICENSE](https://github.com/grycap/scar/blob/master/LICENSE) for the full
license text.

## Acknowledgements

* [udocker](https://github.com/indigo-dc/udocker)
* [faassh](https://github.com/smithclay/faassh)
