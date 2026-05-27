"""Load offline-trained models and predict over the MPC horizon."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class ForecastBundle:
    """Placeholder until training pipeline ships real LightGBM artifacts."""

    version: str = "placeholder"
    load_baseline_w: float = 500.0
    solar_baseline_w: float = 0.0
    price_tail_ore_per_kwh: float = 50.0


def load_bundle(path: Path) -> ForecastBundle:
    if not path.exists():
        return ForecastBundle()
  # TODO: load joblib/pkl from NAS bundle
    return ForecastBundle()


def predict_horizon(
    bundle: ForecastBundle,
    step_starts: list[datetime],
    n_real_prices: int,
    spot_tail_ore: Optional[np.ndarray] = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (load_w, solar_w, spot_tail_sek_per_wh) length N.

    Placeholder: flat load, zero solar, mean price tail for unknown hours.
    """
    n = len(step_starts)
    load = np.full(n, bundle.load_baseline_w)
    solar = np.full(n, bundle.solar_baseline_w)
    if spot_tail_ore is not None and len(spot_tail_ore) >= n:
        from src.control.pricing import ore_per_kwh_to_sek_per_wh

        tail = ore_per_kwh_to_sek_per_wh(spot_tail_ore[:n])
    else:
        from src.control.pricing import ore_per_kwh_to_sek_per_wh

        tail = np.full(n, float(ore_per_kwh_to_sek_per_wh(bundle.price_tail_ore_per_kwh)))
    return load, solar, tail
