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
rm -f "$ADDON/config/example.yaml"
cp "$ROOT/config/example.yaml" "$ADDON/config/example.yaml"
if [ -L "$ADDON/config/example.yaml" ]; then
  echo "ERROR: example.yaml must be a real file, not a symlink" >&2
  exit 1
fi
echo "Synced addon bundle into $ADDON ($(wc -c < "$ADDON/config/example.yaml") bytes example.yaml)"
