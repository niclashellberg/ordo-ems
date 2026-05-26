# Supervisor 2026.04+ no longer injects BUILD_FROM / build.yaml — pin base explicitly.
# Multi-arch image: https://github.com/home-assistant/docker-base
FROM ghcr.io/home-assistant/base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /app/venv/bin/pip install --no-cache-dir numpy \
    && /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

ENV PATH="/app/venv/bin:${PATH}"
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/data/options.yaml

COPY src/ /app/src/
COPY config/example.yaml /app/config/example.yaml
COPY energy_mpc.py /app/energy_mpc.py
COPY run.sh /run.sh
RUN chmod +x /run.sh

LABEL \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64" \
    org.opencontainers.image.source="https://github.com/niclashellberg/ordo-ems"

CMD ["/run.sh"]
