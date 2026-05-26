"""Default car plug-in schedule (weekday away 07:00–17:00)."""

from __future__ import annotations

from datetime import datetime

import numpy as np

from src.config import ScheduleConfig


def default_car_available(
    step_starts: list[datetime],
    cfg: ScheduleConfig,
    plugged_in_now: bool | None = None,
) -> np.ndarray:
    """
    Build car_available[] for the horizon.

    Weekdays 07:00–17:00: unavailable unless plugged_in_now overrides
    (Tesla sensor wins when provided).
  Weekends: available whenever plugged (default True if unknown).
    """
    avail = np.ones(len(step_starts), dtype=bool)
    for i, t in enumerate(step_starts):
        wd = t.weekday() in cfg.workdays
        h = t.hour + t.minute / 60.0
        if wd and cfg.unplug_start_hour <= h < cfg.unplug_end_hour:
            avail[i] = False
        else:
            avail[i] = True
    if plugged_in_now is not None:
        avail[0] = plugged_in_now
    return avail
