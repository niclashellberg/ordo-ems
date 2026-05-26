# 01 — Architecture

## Why MPC (and not the alternatives)

Battery arbitrage is a **constrained, finite-horizon optimization over a system
with memory** (state of charge). That is the textbook fit for MPC:

- **Hard constraints** — SoC limits, charge/discharge power caps, grid import/
  export caps, car deadline.
- **Forecastable disturbances** — prices, solar, load over a receding horizon.
- **Linear dynamics** — the battery is essentially an integrator of power.
- **Continuous re-planning** — re-solve as forecasts and prices update.

Rejected alternatives:
- **Rule-based** ("charge when cheap") cannot handle the coupling between future
  solar surplus, future price peaks, and finite storage.
- **Reinforcement learning** can solve it but is hard to constrain safely and
  hard to explain. MPC gives provable constraint satisfaction and a transparent
  objective — which matters with real money and real hardware.

## Four decoupled layers

This maps directly onto "train on a separate machine, control in Home Assistant."

### 1. Forecasting layer (the *estimator*)
Predicts the disturbances the controller needs over the horizon:
- **Load forecast** — from historic usage + weather + calendar features.
- **Solar forecast** — clear-sky physics × weather-derived cloud factor, then an
  ML correction.
- **Price tail forecast** — for the horizon window beyond Nord Pool visibility.

See `03_forecasting.md`.

### 2. Optimization layer (the *controller*) — the MPC core
- Takes forecasts over the horizon, solves the LP, outputs charge/discharge/
  car schedule.
- **Receding horizon:** solve 24–48h, **apply only the first step**, re-solve.

See `02_control_core.md`. Implemented and validated in `energy_mpc.py`.

### 3. Explanation layer (the *LLM*)
- **Not in the control loop.** Explains decisions *post-hoc* and parses natural-
  language overrides into structured constraints.
- Reads the optimizer's output + shadow prices (duals) + forecasts, and narrates
  e.g. "charging now because prices peak at 18:00 and solar won't cover evening
  load."

See `05_llm_and_overrides.md`.

### 4. Execution layer (Home Assistant)
- Lightweight. Reads the current setpoint and commands the inverter / charger.
- Reads live state (SoC, solar, load, car availability) back into the loop.

See `04_home_assistant.md`.

## Data flow

```
                 ┌─────────────────────────── separate machine ──┐
   HA history ──▶│ InfluxDB ──▶ training ──▶ serialized models    │
                 └───────────────────────────────────┬───────────┘
                                                      │ models
                                                      ▼
  HA live state ──▶ ┌──────────── HA add-on ──────────────────────┐
  (WebSocket)       │ forecasts ─▶ build horizon ─▶ solve LP ─────┐│
  Nord Pool ───────▶│                                    │        ││
  prices            │  actuate first step ◀──────────────┘        ││
                    │  (inverter / car charger)                   ││
                    │  optional: LLM explain(result) ─────────────┘│
                    └──────────────────────────────────────────────┘
```

The control loop **only** talks to HA live state. It never runs heavy historical
queries — those happen offline against InfluxDB on the training machine.

## The two storage assets have different physics

- **House battery** — bidirectional. Charge and discharge to house/grid. The
  arbitrage asset.
- **Car** — charge-only from the controller's perspective (no V2G assumed). A
  **deferrable load with a deadline**: meet target SoC by a time, at lowest cost.

Same LP, two different roles. The car objective is "hit the deadline cheaply";
the house objective is "maximize profit."

## Robustness principles

- **Re-solve frequently** (5–15 min) — naturally corrects forecast error.
- **Event-trigger** a re-solve on every new Nord Pool publication (13:01) and
  significant forecast update, on top of the periodic cadence.
- **Terminal value** on leftover battery energy — stops the battery emptying
  itself at the horizon edge (approximates the cost-to-go).
- **Minimum SoC reserve** — never deplete fully; health + forecast-error buffer.
- Defer **stochastic / scenario MPC** until the deterministic version is solid.
