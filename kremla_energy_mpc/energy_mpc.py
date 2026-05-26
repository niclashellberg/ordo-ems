"""
Backward-compatible entry point.

Prefer: from src.control import solve_mpc, PlantConfig, ...
"""

from src.control.mpc import HorizonInputs, Override, SolveResult, apply_extra_loads, solve_mpc  # noqa: F401
from src.control.plant import PlantConfig  # noqa: F401
from src.control.pricing import build_prices  # noqa: F401

if __name__ == "__main__":
    import numpy as np

    from src.control.pricing import ore_per_kwh_to_sek_per_wh

    cfg = PlantConfig()
    n = 36
    dt = 1.0
    hours = np.arange(n)
    spot_ore = 12.0 + 10.0 * np.sin((hours - 6) / 24 * 2 * np.pi) ** 2
    spot_ore[17:21] += 12.0
    spot = ore_per_kwh_to_sek_per_wh(spot_ore)
    load = 400 + 600 * np.exp(-((hours % 24 - 8) ** 2) / 6) + 900 * np.exp(
        -((hours % 24 - 19) ** 2) / 6
    )
    solar = np.maximum(0, 5000 * np.sin((hours % 24 - 6) / 12 * np.pi))
    solar[(hours % 24 < 6) | (hours % 24 > 18)] = 0
    car_avail = np.ones(n, dtype=bool)
    car_avail[8:17] = False

    h = HorizonInputs(
        dt_h=dt,
        spot=spot,
        n_real_prices=n,
        load=load,
        solar=solar,
        car_available=car_avail,
        soc_house_0=10_000.0,
        soc_car_0=8_000.0,
        e_car_max=100_000.0,
    )
    overrides = [
        Override(kind="car_deadline", target_wh=58_000.0, deadline_step=31, hard=True),
        Override(kind="extra_load", start_step=19, end_step=20, power_w=6000.0),
    ]
    h.load = apply_extra_loads(h.load, overrides)
    res = solve_mpc(cfg, h, overrides)
    print(f"status   : {res.status}")
    print(f"feasible : {res.feasible}")
    if res.feasible:
        print(f"cost     : {res.cost:.2f}")
        print(f"house SoC min: {res.soc_house.min():.0f} (reserve {cfg.soc_house_min_wh:.0f})")
