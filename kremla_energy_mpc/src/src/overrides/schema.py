"""Override JSON schema validation."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.control.mpc import Override

ALLOWED_KINDS = frozenset({"car_deadline", "house_reserve", "extra_load"})


def validate_override(data: dict[str, Any]) -> Override:
    kind = data.get("kind")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"unknown override kind: {kind}")
    return Override(
        kind=kind,
        target_wh=float(data.get("target_wh", 0)),
        deadline_step=int(data.get("deadline_step", 0)),
        start_step=int(data.get("start_step", 0)),
        end_step=int(data.get("end_step", 0)),
        power_w=float(data.get("power_w", 0)),
        hard=bool(data.get("hard", True)),
    )


def sauna_override(
    start_step: int,
    energy_wh: float,
    dt_h: float,
    power_w: float = 6000.0,
) -> list[Override]:
    """
    Spread ~10 kWh sauna load across 15-min steps at `power_w`.

    Example: 10_000 Wh at 6 kW → ceil(10000/1500) ≈ 7 steps.
    """
    wh_per_step = power_w * dt_h
    n_steps = max(1, int(np.ceil(energy_wh / wh_per_step)))
    return [
        Override(
            kind="extra_load",
            start_step=start_step + k,
            end_step=start_step + k + 1,
            power_w=power_w,
            hard=True,
        )
        for k in range(n_steps)
    ]
