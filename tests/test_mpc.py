"""Unit tests for MPC core and Swedish pricing."""

import numpy as np

from src.control.mpc import HorizonInputs, Override, PlantConfig, apply_extra_loads, solve_mpc
from src.control.pricing import build_prices, ore_per_kwh_to_sek_per_wh


def test_pricing_import_bundle_before_vat():
    cfg = PlantConfig()
    spot = ore_per_kwh_to_sek_per_wh(np.array([100.0]))  # 1 SEK/kWh
    buy, sell = build_prices(cfg, spot)
    expected_before_vat = spot[0] + cfg.grid_fee_per_wh + cfg.energy_tax_per_wh
    assert np.isclose(buy[0], expected_before_vat * 1.25)
    assert np.isclose(sell[0], spot[0])


def test_min_soc_reserve():
    cfg = PlantConfig(e_house_max=51_400, min_soc_fraction=0.05)
    n = 24
    spot = ore_per_kwh_to_sek_per_wh(np.full(n, 50.0))
    h = HorizonInputs(
        dt_h=1.0,
        spot=spot,
        n_real_prices=n,
        load=np.full(n, 400.0),
        solar=np.zeros(n),
        car_available=np.zeros(n, dtype=bool),
        soc_house_0=cfg.soc_house_min_wh,
        soc_car_0=0.0,
        e_car_max=100_000.0,
    )
    res = solve_mpc(cfg, h)
    assert res.feasible
    assert res.soc_house[1:].min() >= cfg.soc_house_min_wh - 1e-3


def test_car_deadline_binds():
    cfg = PlantConfig()
    n = 36
    spot = ore_per_kwh_to_sek_per_wh(np.full(n, 30.0))
    car_avail = np.ones(n, dtype=bool)
    h = HorizonInputs(
        dt_h=1.0,
        spot=spot,
        n_real_prices=n,
        load=np.full(n, 500.0),
        solar=np.zeros(n),
        car_available=car_avail,
        soc_house_0=20_000.0,
        soc_car_0=10_000.0,
        e_car_max=100_000.0,
    )
    target = 90_000.0
    ov = Override(kind="car_deadline", target_wh=target, deadline_step=30, hard=True)
    res = solve_mpc(cfg, h, [ov])
    assert res.feasible
    assert res.soc_car[30] >= target - 50


def test_sauna_extra_load():
    load = np.full(10, 400.0)
    ovs = [
        Override(kind="extra_load", start_step=2, end_step=3, power_w=6000.0),
    ]
    out = apply_extra_loads(load, ovs)
    assert out[2] == 6400.0
    assert out[3] == 400.0
