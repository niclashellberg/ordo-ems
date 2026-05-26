# Supervisor passes BUILD_FROM per architecture (see build.yaml).
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /app

# cvxpy + highspy need a glibc toolchain (Alpine/musl builds often fail on Pi).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        build-essential \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages --upgrade pip \
    && pip3 install --no-cache-dir --break-system-packages numpy \
    && pip3 install --no-cache-dir --break-system-packages -r /app/requirements.txt

COPY src/ /app/src/
COPY config/example.yaml /app/config/example.yaml
COPY energy_mpc.py /app/energy_mpc.py
COPY run.sh /run.sh
RUN chmod +x /run.sh

ENV PYTHONPATH=/app
ENV CONFIG_PATH=/data/options.yaml

CMD ["/run.sh"]
