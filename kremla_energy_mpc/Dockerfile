FROM ghcr.io/home-assistant/base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /app

# Wheels only — no gfortran compile (Pi-friendly, ~3–8 min build).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --no-cache-dir --upgrade pip \
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
    io.hass.version="0.1.4" \
    org.opencontainers.image.source="https://github.com/niclashellberg/ordo-ems"

CMD ["/run.sh"]
