"""Parse Nord Pool prices from Home Assistant (SE3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import numpy as np

from src.control.pricing import ore_per_kwh_to_sek_per_wh

STOCKHOLM = ZoneInfo("Europe/Stockholm")


def parse_nordpool_attributes(attributes: dict[str, Any]) -> list[tuple[datetime, float]]:
    """
    Parse sensor.nord_pool_se3_prices attributes.data (list of hourly slots).

    Each item is typically {"start": ISO, "end": ISO, "value": float} in öre/kWh.
    Returns sorted (start_utc, ore_per_kwh) pairs.
    """
    data = attributes.get("data") or attributes.get("raw_today") or []
    if not data and "today" in attributes:
        data = attributes["today"]
    rows: list[tuple[datetime, float]] = []
    for item in data:
        if isinstance(item, dict):
            start = item.get("start") or item.get("from")
            value = item.get("value") or item.get("price")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            start, value = item[0], item[1]
        else:
            continue
        if start is None or value is None:
            continue
        if isinstance(start, str):
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        else:
            start_dt = start
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=STOCKHOLM)
        rows.append((start_dt.astimezone(timezone.utc), float(value)))
    rows.sort(key=lambda r: r[0])
    return rows


def hourly_prices_to_timesteps(
    hourly: list[tuple[datetime, float]],
    step_starts: list[datetime],
) -> tuple[np.ndarray, int]:
    """
    Map hourly öre/kWh to 15-min SEK/Wh vector aligned to step_starts.

    Returns (spot_sek_per_wh, n_real_prices).
    """
    if not hourly or not step_starts:
        n = len(step_starts)
        return np.zeros(n), 0

    ore = np.zeros(len(step_starts))
    hi = 0
    for i, t0 in enumerate(step_starts):
        t0_utc = t0.astimezone(timezone.utc) if t0.tzinfo else t0.replace(tzinfo=STOCKHOLM).astimezone(timezone.utc)
        while hi + 1 < len(hourly) and hourly[hi + 1][0] <= t0_utc:
            hi += 1
        ore[i] = hourly[min(hi, len(hourly) - 1)][1]

    n_real = sum(1 for t in step_starts if t.astimezone(timezone.utc) <= hourly[-1][0] + timedelta(hours=1))
    return ore_per_kwh_to_sek_per_wh(ore), max(n_real, 1)


def build_step_starts(
    now: datetime,
    n_steps: int,
    dt_minutes: int,
) -> list[datetime]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=STOCKHOLM)
    minute = (now.minute // dt_minutes) * dt_minutes
    t0 = now.replace(minute=minute, second=0, microsecond=0)
    delta = timedelta(minutes=dt_minutes)
    return [t0 + i * delta for i in range(n_steps)]
