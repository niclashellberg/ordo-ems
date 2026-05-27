"""
Energy MPC control core.

Deterministic LP scheduling house battery, EV charge, and grid import/export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cvxpy as cp
import numpy as np

from .plant import PlantConfig
from .pricing import build_prices


@dataclass
class HorizonInputs:
    dt_h: float
    spot: np.ndarray  # SEK/Wh, length N
    n_real_prices: int
    load: np.ndarray
    solar: np.ndarray
    car_available: np.ndarray
    soc_house_0: float
    soc_car_0: float
    e_car_max: float
    terminal_value: Optional[float] = None


@dataclass
class Override:
    kind: str  # car_deadline | house_reserve | extra_load
    target_wh: float = 0.0
    deadline_step: int = 0
    start_step: int = 0
    end_step: int = 0
    power_w: float = 0.0
    hard: bool = True


@dataclass
class SolveResult:
    status: str
    feasible: bool
    p_hc: np.ndarray = field(default_factory=lambda: np.array([]))
    p_hd: np.ndarray = field(default_factory=lambda: np.array([]))
    p_car: np.ndarray = field(default_factory=lambda: np.array([]))
    p_import: np.ndarray = field(default_factory=lambda: np.array([]))
    p_export: np.ndarray = field(default_factory=lambda: np.array([]))
    soc_house: np.ndarray = field(default_factory=lambda: np.array([]))
    soc_car: np.ndarray = field(default_factory=lambda: np.array([]))
    cost: float = float("nan")
    duals: dict = field(default_factory=dict)


def _solve_lp(prob: cp.Problem) -> None:
    """Prefer solvers with reliable aarch64 wheels (no HiGHS compile on Pi)."""
    for solver in ("CLARABEL", "OSQP", "SCS"):
        try:
            prob.solve(solver=solver)
            if prob.status in ("optimal", "optimal_inaccurate"):
                return
        except Exception:
            continue
    prob.solve()


def apply_extra_loads(load: np.ndarray, overrides: list[Override]) -> np.ndarray:
    load = load.copy()
    for ov in overrides:
        if ov.kind == "extra_load":
            load[ov.start_step : ov.end_step] += ov.power_w
    return load


def solve_mpc(
    cfg: PlantConfig,
    h: HorizonInputs,
    overrides: Optional[list[Override]] = None,
) -> SolveResult:
    overrides = overrides or []
    n = len(h.spot)
    dt = h.dt_h
    reserve = cfg.soc_house_min_wh

    price_buy, price_sell = build_prices(cfg, h.spot)
    tv = h.terminal_value if h.terminal_value is not None else float(np.mean(price_buy))

    p_hc = cp.Variable(n, nonneg=True)
    p_hd = cp.Variable(n, nonneg=True)
    p_car = cp.Variable(n, nonneg=True)
    p_imp = cp.Variable(n, nonneg=True)
    p_exp = cp.Variable(n, nonneg=True)
    soc_h = cp.Variable(n + 1)
    soc_c = cp.Variable(n + 1)

    cons: list = [
        soc_h[0] == h.soc_house_0,
        soc_c[0] == h.soc_car_0,
    ]

    for k in range(n):
        cons += [
            soc_h[k + 1]
            == soc_h[k] + cfg.eta_c * p_hc[k] * dt - (1.0 / cfg.eta_d) * p_hd[k] * dt,
            soc_c[k + 1] == soc_c[k] + cfg.eta_car * p_car[k] * dt,
            h.load[k] + p_hc[k] + p_car[k] + p_exp[k] == h.solar[k] + p_hd[k] + p_imp[k],
        ]

    cons += [
        p_hc <= cfg.p_hc_max,
        p_hd <= cfg.p_hd_max,
        p_exp <= cfg.p_exp_max,
        soc_h[1:] >= reserve,
        soc_h[1:] <= cfg.e_house_max,
        soc_c[1:] >= 0,
        soc_c[1:] <= h.e_car_max,
    ]

    for k in range(n):
        cap = cfg.p_car_max if bool(h.car_available[k]) else 0.0
        cons += [p_car[k] <= cap]

    cost = (
        cp.sum(cp.multiply(price_buy, p_imp) * dt - cp.multiply(price_sell, p_exp) * dt)
        - tv * soc_h[n]
    )

    soft_penalty = 0
    for ov in overrides:
        if ov.kind == "car_deadline":
            if ov.hard:
                cons += [soc_c[ov.deadline_step] >= ov.target_wh]
            else:
                slack = cp.Variable(nonneg=True)
                cons += [soc_c[ov.deadline_step] + slack >= ov.target_wh]
                soft_penalty += 1e3 * slack
        elif ov.kind == "house_reserve":
            if ov.hard:
                cons += [soc_h[ov.deadline_step] >= ov.target_wh]
            else:
                slack = cp.Variable(nonneg=True)
                cons += [soc_h[ov.deadline_step] + slack >= ov.target_wh]
                soft_penalty += 1e3 * slack

    prob = cp.Problem(cp.Minimize(cost + soft_penalty), cons)
    _solve_lp(prob)

    feasible = prob.status in ("optimal", "optimal_inaccurate")
    if not feasible:
        return SolveResult(status=prob.status, feasible=False)

    duals = {}
    if prob.constraints:
        for i, c in enumerate(prob.constraints[: min(8, len(prob.constraints))]):
            try:
                duals[f"constraint_{i}"] = float(c.dual_value) if c.dual_value is not None else None
            except Exception:
                duals[f"constraint_{i}"] = None

    return SolveResult(
        status=prob.status,
        feasible=True,
        p_hc=np.asarray(p_hc.value).flatten(),
        p_hd=np.asarray(p_hd.value).flatten(),
        p_car=np.asarray(p_car.value).flatten(),
        p_import=np.asarray(p_imp.value).flatten(),
        p_export=np.asarray(p_exp.value).flatten(),
        soc_house=np.asarray(soc_h.value).flatten(),
        soc_car=np.asarray(soc_c.value).flatten(),
        cost=float(prob.value),
        duals=duals,
    )
