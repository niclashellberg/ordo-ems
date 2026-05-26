"""Entry point for the Home Assistant add-on."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn

from src.api.app import app
from src.config import load_config

logging.basicConfig(level=logging.INFO)


def main() -> None:
    cfg_path = Path(os.environ.get("CONFIG_PATH", "/data/options.yaml"))
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parents[1] / "config" / "example.yaml"
    os.environ.setdefault("CONFIG_PATH", str(cfg_path))
    cfg = load_config(cfg_path)
    uvicorn.run(
        app,
        host=cfg.api.host,
        port=int(os.environ.get("API_PORT", cfg.api.port)),
        log_level="info",
    )


if __name__ == "__main__":
    main()
