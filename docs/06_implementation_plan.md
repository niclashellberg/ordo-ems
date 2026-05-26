# 06 — Implementation Plan

Phased build order. Each phase has acceptance criteria — don't advance until they
pass. The control core (Phase 0) already exists and is validated.

## Phase 0 — Control core ✅ (done, in `energy_mpc.py`)

Validated: LP solves with CVXPY + HiGHS, car deadline override binds, asymmetric
pricing produces self-consumption behavior.

Carry-over hardening (do early in Phase 1):
- [ ] minimum SoC reserve constraint
- [ ] confirm inverter simultaneous import/discharge → LP or MILP
- [ ] real efficiency values
- [ ] populate `SolveResult.duals` for the explanation layer

## Phase 1 — Solidify the core + config

**Why first:** everything depends on a trustworthy controller.

- Move `energy_mpc.py` into `src/control/`.
- Add min-reserve, real config plumbing (VAT, grid fee, efficiencies, limits)
  from a config file / HA add-on options.
- Capture constraint duals in `SolveResult`.
- Unit tests: known-input scenarios with hand-checkable optima (e.g. flat price →
  no cycling; single cheap hour → charge then discharge into peak).

**Acceptance:** core solves all test scenarios with expected qualitative behavior;
duals exposed; min reserve respected.

## Phase 2 — Solar forecast

**Why next:** most physics to exploit, highest profit impact, standalone and
validatable against historic data before any wiring.

- `pvlib` clear-sky baseline from panel geometry.
- LightGBM correction on weather features (see `03_forecasting.md`).
- Validate against historic production; report MAE/RMSE by hour-of-day.

**Acceptance:** forecast beats seasonal-naive baseline on held-out historic data;
`predict()` returns a horizon-aligned vector.

## Phase 3 — Load + price-tail forecasts

- LightGBM load model (lags + weather + calendar).
- Simple price-tail model for the 00:00–13:00 visibility gap.

**Acceptance:** both expose the `predict()` contract; load model beats naive
lag baseline; price tail plugs into the horizon builder with `n_real_prices`.

## Phase 4 — Home Assistant data plumbing

- InfluxDB sink config (HA → InfluxDB), logging the full feature/prediction set.
- WebSocket live-state reader → fills `HorizonInputs` momentary fields.
- Training machine pulls from InfluxDB (offline).

**Acceptance:** months of history queryable from InfluxDB on the training box;
live state reads into a valid `HorizonInputs` in < 1s.

## Phase 5 — Control loop + actuation

- Wire forecasts + live state + prices into the receding-horizon loop.
- Periodic (5–15 min) + 13:01 hard trigger + forecast-update trigger.
- Actuate first-step setpoints to inverter / car charger.

**Acceptance:** loop runs continuously, re-solves on all triggers, actuates only
the first step; 13:01 re-solve observably extends the horizon.

## Phase 6 — Override mechanism

- `Override` JSON schema + validator.
- Compiler: structured override → LP constraint / load injection.
- Infeasibility → warning.

**Acceptance:** the three example overrides (car deadline, house reserve, sauna)
work end-to-end; conflicting overrides surface infeasibility as a warning.

## Phase 7 — LLM layer

- `explain()` and `parse_override()` behind one interface; cloud/local flag.
- Duals fed into explanations.
- Audit log of text → override → result.

**Acceptance:** natural-language override round-trips to a validated `Override`;
explanations correctly reference the binding constraint from duals.

## Phase 8 — Warning system

- Infeasibility, forecast drift, actuation drift, deadline-at-risk, sensor
  sanity. Written back to HA as notifications/sensors.

**Acceptance:** each warning type triggers on an injected fault scenario.

## Phase 9 — Add-on packaging

- HA add-on container (CVXPY + HiGHS), options schema, model loading.

**Acceptance:** installs as an HA add-on, runs the loop on Pi-class hardware,
config editable in the HA UI.

---

## Suggested order rationale

Core → forecasts (solar first) → data plumbing → loop → overrides → LLM →
warnings → packaging. Forecasts come before the loop because the loop is
meaningless without inputs; the LLM and warnings come late because they wrap a
working deterministic system. Packaging is last.
