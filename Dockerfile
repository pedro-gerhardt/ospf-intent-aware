FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    python3 \
    ca-certificates \
    sudo \
    lsb-release \
    iputils-ping && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/mininet/mininet /tmp/mininet && \
    /tmp/mininet/util/install.sh -a && \
    rm -rf /tmp/mininet

ENV SHELL /bin/bash

WORKDIR /app
COPY . .

CMD ["python3", "test_mininet.py"]