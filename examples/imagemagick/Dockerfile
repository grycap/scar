FROM bitnami/minideb:jessie

RUN install_packages imagemagick

#Required to avoid relying on symlinks, which fails when using udocker and the F1 execution mode on AWS Lambda.
ENV PATH /usr/lib/x86_64-linux-gnu/ImageMagick-6.8.9/bin-Q16/:$PATH