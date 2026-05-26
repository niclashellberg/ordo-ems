#!/bin/sh
set -e
cd /app
export PYTHONPATH=/app
export CONFIG_PATH="${CONFIG_PATH:-/data/options.yaml}"

if [ -z "$CONFIG_PATH" ] || [ ! -f "$CONFIG_PATH" ]; then
  cp /app/config/example.yaml /data/options.yaml 2>/dev/null || true
  export CONFIG_PATH=/data/options.yaml
fi

exec python -m src.main
