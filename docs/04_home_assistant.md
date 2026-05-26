# 04 — Home Assistant Integration

Two distinct data paths — keep them separate:

- **Live state** for the control loop (low latency, current values).
- **Historical data** for training (months of history, queried offline).

## Live state (control loop)

Read entity states via the HA **WebSocket API** (preferred) or REST API. Subscribe
to / poll the entities the loop needs each cycle:

- solar production (W)
- house load (W)
- house battery SoC
- car SoC and charge limit
- car availability (plugged in / present)

These map to `HorizonInputs.soc_house_0`, `soc_car_0`, `car_available[0]`, and the
momentary solar/load used to anchor forecasts.

The loop also **actuates** back to HA: write the first-step setpoints
(`P_hc[0]`, `P_hd[0]`, `P_car[0]`) to the inverter / car-charger control entities.

## Historical data (training) — do NOT use HA's SQLite

HA's default `recorder` (SQLite) is tuned for recent-history UI, purges old data
by default, and is painful to query over months. Instead:

1. Configure HA's **InfluxDB integration** to stream sensor history into InfluxDB
   (or TimescaleDB/Postgres). Configure once.
2. The **training machine queries InfluxDB**, never HA's SQLite.

### Logging resolution
- power / load / solar: **1–5 min**
- prices: hourly is fine
- Avoid 1s resolution — disk fills fast and the models don't need it.

### Log these or regret it later
- outdoor temperature, GHI / cloud cover from the weather source
- calendar / holiday flags
- **the controller's own past decisions and the forecasts it made** — so you can
  backtest predicted-vs-actual. Store predictions, not just measurements.

## Data flow summary

```
HA (live + InfluxDB sink)
   → training machine pulls from InfluxDB
   → fits solar / load / price models
   → serializes models
   → control add-on loads them
```

The control loop only ever talks to HA **live**; never heavy historical queries.

## The control loop (every cycle)

1. Read live state from HA (WebSocket) → fill `soc_house_0`, `soc_car_0`,
   `car_available`.
2. Pull latest forecasts + Nord Pool prices; build `spot` as **real prices for
   the known window + forecast tail**, set `n_real_prices` to the boundary.
3. Call `solve_mpc(cfg, horizon, overrides)`.
4. Actuate **only the first timestep** to inverter / charger.
5. Discard the rest; re-solve next cycle (receding horizon).

### Triggers
- periodic: every **5–15 min**
- hard event: **13:01** daily (new Nord Pool prices → `n_real_prices` jumps)
- event: significant forecast update

## Packaging as a Home Assistant add-on

- Python app in a container, packaged per the HA add-on spec (`config.yaml`,
  `Dockerfile`, `run.sh`).
- Bundles CVXPY + HiGHS — both pip-installable, run fine on Pi-class hardware
  (a 36-step LP solves in milliseconds).
- Loads serialized forecast models produced by the training machine (ship them
  with the add-on or fetch on update).
- Exposes config (limits, VAT, grid fee, efficiencies, min reserve) via the
  add-on options schema so the user sets them in the HA UI.

## Warning surfaces (write back to HA as notifications / sensors)

- **Infeasibility** — `solve_mpc` returns `feasible == False` (conflicting
  overrides). Highest-value warning.
- **Forecast-vs-reality drift** — measured solar/load diverging from forecast
  (computable because forecasts are stored).
- **Plan-vs-actuation drift** — commanded `P_*[0]` vs next cycle's sensor reading;
  hardware/comms fault.
- **Deadline-at-risk** — car can't hit target by deadline even at `P_car_max`
  given availability; detect at solve time.
- **Sensor staleness / sanity** — SoC outside range, negative load, stale prices
  past 13:00.
