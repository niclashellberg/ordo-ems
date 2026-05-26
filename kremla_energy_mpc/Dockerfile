ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

WORKDIR /app

RUN apk add --no-cache \
    build-base \
    openblas-dev \
    && pip install --no-cache-dir --upgrade pip

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
COPY config/example.yaml /app/config/example.yaml
COPY energy_mpc.py /app/

ENV PYTHONPATH=/app
ENV CONFIG_PATH=/data/options.yaml

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]
