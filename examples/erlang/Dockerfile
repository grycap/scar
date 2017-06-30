# Original Dockerfile from https://github.com/c0b/docker-erlang-otp/blob/8128be859f47c39473be9fa2c2ae33af28f74279/20/Dockerfile
# Slightly adapted by @gmolto for reduced footprint to be run on AWS Lambda via SCAR
FROM bitnami/minideb:jessie

ENV OTP_VERSION="20.0"

# We'll install the build dependencies, and purge them on the last step to make
# sure our final image contains only what we've just built:
RUN set -xe \
    && OTP_DOWNLOAD_URL="https://github.com/erlang/otp/archive/OTP-${OTP_VERSION}.tar.gz" \
    && OTP_DOWNLOAD_SHA256="548815fe08f5b661d38334ffa480e9e0614db5c505da7cb0dc260e729697f2ab" \
    && fetchDeps=' \
        curl \
        ca-certificates' \
    && apt-get update \
    && apt-get install -y --no-install-recommends $fetchDeps \
    && curl -fSL -o otp-src.tar.gz "$OTP_DOWNLOAD_URL" \
    && echo "$OTP_DOWNLOAD_SHA256  otp-src.tar.gz" | sha256sum -c - \
    && runtimeDeps=' \
        libodbc1 \
        libssl1.0.0 \
        libsctp1 \
        libwxgtk3.0-0 \
    ' \
    && buildDeps=' \
        autoconf \
        gcc \
        make \
        libncurses-dev \
        unixodbc-dev \
        libssl-dev \
        libsctp-dev \
        libwxgtk3.0-dev \
    ' \
    && apt-get install -y --no-install-recommends $runtimeDeps \
    && apt-get install -y --no-install-recommends $buildDeps \
    && curl -fSL -o otp-src.tar.gz "$OTP_DOWNLOAD_URL" \
    && echo "$OTP_DOWNLOAD_SHA256  otp-src.tar.gz" | sha256sum -c - \
    && export ERL_TOP="/usr/src/otp_src_${OTP_VERSION%%@*}" \
    && mkdir -vp $ERL_TOP \
    && tar -xzf otp-src.tar.gz -C $ERL_TOP --strip-components=1 \
    && rm otp-src.tar.gz \
    && ( cd $ERL_TOP \
      && ./otp_build autoconf \
      && ./configure \
        --enable-dirty-schedulers \
      && make -j$(nproc) \
      && make install ) \
    && find /usr/local -name examples | xargs rm -rf \
    && apt-get purge -y --auto-remove $buildDeps $fetchDeps \
    && rm -rf $ERL_TOP /var/lib/apt/lists/*

CMD ["/bin/sh","/usr/local/bin/erl"]
