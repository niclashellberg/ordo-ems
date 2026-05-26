#!/usr/bin/env bash
# Copy runtime files into kremla_energy_mpc/ before commit or HA build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADDON="$ROOT/kremla_energy_mpc"

rm -rf "$ADDON/src"
cp "$ROOT/requirements.txt" "$ADDON/"
cp "$ROOT/energy_mpc.py" "$ADDON/"
cp -r "$ROOT/src" "$ADDON/src"
mkdir -p "$ADDON/config"
cp "$ROOT/config/example.yaml" "$ADDON/config/example.yaml"
echo "Synced addon bundle into $ADDON"
