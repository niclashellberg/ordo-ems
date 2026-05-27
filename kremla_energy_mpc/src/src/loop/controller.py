"""Receding-horizon MPC loop."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.control.mpc import Override, SolveResult, apply_extra_loads, solve_mpc
from src.forecasting.predict import ForecastBundle, load_bundle
from src.ha.client import HomeAssistantClient
from src.loop.horizon import HorizonBuilder, build_step_starts
from src.overrides.schema import validate_override

logger = logging.getLogger(__name__)
STOCKHOLM = ZoneInfo("Europe/Stockholm")


@dataclass
class ControllerState:
    last_solve: Optional[SolveResult] = None
    last_horizon: Optional[dict[str, Any]] = None
    pending_overrides: list[Override] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EnergyController:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.state = ControllerState()
        self._bundle = load_bundle(cfg.models.local_path / "bundle.pkl")
        self._builder = HorizonBuilder(cfg, self._bundle)
        self._ha: Optional[HomeAssistantClient] = None

    def entity_ids(self) -> list[str]:
        e = self.cfg.entities
        return [
            e.solar_power,
            e.house_load,
            e.house_soc,
            e.house_soc_energy,
            e.car_soc,
            e.car_energy,
            e.car_plugged,
            e.nordpool,
        ]

    async def start(self) -> None:
        self._ha = HomeAssistantClient(self.cfg.homeassistant_url, self.cfg.homeassistant_token)
        await self._ha.connect()
        asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        assert self._ha
        interval = self.cfg.loop.interval_minutes * 60
        while True:
            try:
                await self.run_once()
            except Exception:
                logger.exception("control cycle failed")
            await asyncio.sleep(interval)

    async def run_once(self, extra_overrides: Optional[list[Override]] = None) -> SolveResult:
        assert self._ha
        states = await self._ha.get_states(self.entity_ids())
        now = datetime.now(STOCKHOLM)
        lc = self.cfg.loop
        n = int(lc.horizon_hours * 60 / lc.timestep_minutes)
        step_starts = build_step_starts(now, n, lc.timestep_minutes)

        horizon = self._builder.build(states, now)
        overrides = list(self.state.pending_overrides)
        overrides.append(self._builder.car_deadline_override(step_starts, now))
        if extra_overrides:
            overrides.extend(extra_overrides)

        horizon.load = apply_extra_loads(horizon.load, overrides)
        res = solve_mpc(self.cfg.plant, horizon, overrides)
        self.state.last_solve = res
        self.state.last_horizon = {
            "spot": horizon.spot.tolist(),
            "load": horizon.load.tolist(),
            "solar": horizon.solar.tolist(),
            "n_real_prices": horizon.n_real_prices,
            "step_count": len(horizon.spot),
        }
        self.state.warnings = []
        if not res.feasible:
            self.state.warnings.append("MPC infeasible — check overrides")
        else:
            await self._actuate(res)
        return res

    async def _actuate(self, res: SolveResult) -> None:
        assert self._ha
        e = self.cfg.entities
        await self._ha.set_number(e.battery_charge_power, float(res.p_hc[0]))
        await self._ha.set_number(e.battery_discharge_power, float(res.p_hd[0]))
        await self._ha.set_number(e.car_charge_power, float(res.p_car[0]))

    def add_override(self, data: dict[str, Any]) -> Override:
        ov = validate_override(data)
        self.state.pending_overrides.append(ov)
        return ov

    def clear_overrides(self) -> None:
        self.state.pending_overrides.clear()

    def explain_context(self) -> dict[str, Any]:
        res = self.state.last_solve
        if not res or not res.feasible:
            return {"feasible": False, "warnings": self.state.warnings}
        return {
            "feasible": True,
            "cost": res.cost,
            "first_step": {
                "p_hc_w": float(res.p_hc[0]),
                "p_hd_w": float(res.p_hd[0]),
                "p_car_w": float(res.p_car[0]),
                "p_import_w": float(res.p_import[0]),
                "p_export_w": float(res.p_export[0]),
            },
            "soc_house_wh": res.soc_house.tolist()[:24],
            "soc_car_wh": res.soc_car.tolist()[:24],
            "duals": res.duals,
            "horizon": self.state.last_horizon,
            "warnings": self.state.warnings,
            "plant": {
                "e_house_max_wh": self.cfg.plant.e_house_max,
                "min_reserve_wh": self.cfg.plant.soc_house_min_wh,
            },
        }
