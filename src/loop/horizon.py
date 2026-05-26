"""Build HorizonInputs from HA live state + forecasts + Nord Pool."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import numpy as np

from src.config import AppConfig
from src.control.mpc import HorizonInputs
from src.control.pricing import ore_per_kwh_to_sek_per_wh
from src.forecasting.predict import ForecastBundle, predict_horizon
from src.ha.car_schedule import default_car_available
from src.ha.client import HomeAssistantClient
from src.ha.nordpool import (
    build_step_starts,
    hourly_prices_to_timesteps,
    parse_nordpool_attributes,
)

STOCKHOLM = ZoneInfo("Europe/Stockholm")


def _deadline_step(step_starts: list[datetime], deadline: datetime) -> int:
    for i, t in enumerate(step_starts):
        if t >= deadline:
            return max(0, i)
    return len(step_starts) - 1


def next_car_deadline(now: datetime, hour: int = 7) -> datetime:
    """Next occurrence of deadline hour (e.g. 07:00) in local time."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=STOCKHOLM)
    local = now.astimezone(STOCKHOLM)
    target = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if local >= target:
        target += timedelta(days=1)
    return target


class HorizonBuilder:
    def __init__(self, cfg: AppConfig, bundle: ForecastBundle):
        self.cfg = cfg
        self.bundle = bundle

    def build(
        self,
        states: dict[str, Any],
        now: Optional[datetime] = None,
    ) -> HorizonInputs:
        now = now or datetime.now(STOCKHOLM)
        lc = self.cfg.loop
        n = int(lc.horizon_hours * 60 / lc.timestep_minutes)
        dt_h = lc.timestep_minutes / 60.0
        step_starts = build_step_starts(now, n, lc.timestep_minutes)

        ent = self.cfg.entities
        soc_house = HomeAssistantClient.state_float(states.get(ent.house_soc_energy, {}))
        if soc_house <= 100:  # percent fallback
            pct = soc_house
            soc_house = pct / 100.0 * self.cfg.plant.e_house_max
        soc_car_pct = HomeAssistantClient.state_float(states.get(ent.car_soc, {}), 50.0)
        soc_car = soc_car_pct / 100.0 * self.cfg.e_car_max_wh
        plugged = HomeAssistantClient.state_bool(states.get(ent.car_plugged, {}))

        np_state = states.get(ent.nordpool, {})
        attrs = np_state.get("attributes", {})
        hourly = parse_nordpool_attributes(attrs)
        spot, n_real = hourly_prices_to_timesteps(hourly, step_starts)

        load_fc, solar_fc, tail = predict_horizon(self.bundle, step_starts, n_real)
        if len(spot) < n:
            spot = np.resize(spot, n)
        if n_real < n:
            spot[n_real:] = tail[n_real:]

        car_avail = default_car_available(step_starts, self.cfg.schedule, plugged_in_now=plugged)

        return HorizonInputs(
            dt_h=dt_h,
            spot=spot,
            n_real_prices=n_real,
            load=load_fc,
            solar=solar_fc,
            car_available=car_avail,
            soc_house_0=soc_house,
            soc_car_0=soc_car,
            e_car_max=self.cfg.e_car_max_wh,
        )

    def car_deadline_override(self, step_starts: list[datetime], now: datetime):
        from src.control.mpc import Override

        deadline = next_car_deadline(now, self.cfg.car_deadline_hour)
        step = _deadline_step(step_starts, deadline.astimezone(STOCKHOLM))
        target = self.cfg.car_target_soc_fraction * self.cfg.e_car_max_wh
        return Override(kind="car_deadline", target_wh=target, deadline_step=step, hard=True)
