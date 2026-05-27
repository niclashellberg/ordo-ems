"""Swedish import/export price construction for the MPC."""

from __future__ import annotations

import numpy as np

from .plant import PlantConfig


def ore_per_kwh_to_sek_per_wh(ore_per_kwh: float | np.ndarray) -> float | np.ndarray:
    """Convert Nord Pool style öre/kWh to SEK/Wh."""
    return np.asarray(ore_per_kwh, dtype=float) / 100.0 / 1000.0


def build_prices(cfg: PlantConfig, spot_sek_per_wh: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Asymmetric buy/sell vectors (SEK/Wh), length N.

    Import (all components in SEK/Wh before VAT bundle):
        (spot + grid_fee + energy_tax) * (1 + VAT)

    Export: raw spot only (no VAT, fees, or tax on export).
    """
    spot = np.asarray(spot_sek_per_wh, dtype=float)
    import_before_vat = spot + cfg.grid_fee_per_wh + cfg.energy_tax_per_wh
    price_buy = import_before_vat * (1.0 + cfg.vat)
    price_sell = spot.copy()
    return price_buy, price_sell


def spot_ore_per_kwh_to_sek_per_wh(spot_ore_per_kwh: np.ndarray) -> np.ndarray:
    return ore_per_kwh_to_sek_per_wh(spot_ore_per_kwh)
