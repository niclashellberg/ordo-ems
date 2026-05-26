# 03 — Forecasting Layer

Three forecasts feed the control core: **solar production**, **house load**, and
the **price tail** (beyond Nord Pool visibility). All are fit offline on the
training machine and serialized; the control loop only loads and evaluates them.

General principle: **gradient-boosted trees (LightGBM/XGBoost) beat fancier
models here** and are cheap to retrain. Reach for sequence models only if GBMs
plateau.

## Solar production forecast

The input with the most physics to exploit, and high profit impact. Two-stage:

1. **Clear-sky baseline (deterministic, physics-based).** From panel geometry
   (tilt, azimuth, rated kW), latitude/longitude, and time, compute the
   theoretical clear-sky production. Use `pvlib` for the solar position and
   clear-sky irradiance model.
2. **Weather-derived correction (ML).** Train a GBM to predict the ratio
   `actual / clear_sky` from weather features. Multiply baseline × predicted
   ratio.

Features:
- GHI / irradiance from the weather API (best single predictor if available)
- cloud cover, temperature
- hour-of-day, day-of-year (seasonality)
- the clear-sky baseline itself

Validate against historic production before wiring into the loop. Report MAE/RMSE
by hour-of-day — errors cluster around sunrise/sunset and partial-cloud days.

## House load forecast

GBM on:
- historic load (lags: same hour yesterday, same hour last week)
- weather (temperature is the big driver — heating/cooling)
- calendar: hour-of-day, day-of-week, holiday flag, school-term flag if relevant
- known recurring loads can be added as features

Note: **deterministic known loads (sauna, etc.) are NOT forecast** — they're
injected as `extra_load` overrides into the load vector before solving (see
`05_llm_and_overrides.md`). The forecast covers the stochastic baseline only.

## Price tail forecast

Only needed for the horizon window **beyond** Nord Pool visibility (the
00:00–13:00 gap, see `02_control_core.md`). A simple model suffices:
- GBM or even a seasonal-naive baseline on historic spot prices
- features: hour-of-day, day-of-week, recent price levels, season
- the controller's terminal-value term absorbs much of the residual error, so
  don't over-engineer this

## Retraining cadence

- Solar / load: retrain periodically (weekly/monthly) as seasons shift. Automate
  on the training machine.
- Always **store predictions alongside measurements** in InfluxDB so you can
  backtest "predicted vs actual" — this is both your model-quality signal and the
  forecast-drift warning input.

## Interface contract

Each forecaster exposes:

```python
def predict(timestamps, features) -> np.ndarray   # length-N vector over horizon
```

returning W (solar, load) or price-per-Wh (price), aligned to the control
horizon's timestep grid (`HorizonInputs.dt_h`).
