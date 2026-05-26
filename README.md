# Kremla Energy AI

An energy controller that schedules **house battery** charge/discharge and **EV
charging** to optimize profit, using **Model Predictive Control (MPC)**. Forecasts
solar production, house load, and price tails; re-plans on a receding horizon;
runs as a **Home Assistant add-on**. An LLM layer explains decisions and parses
natural-language overrides — but is **never in the control loop**.

---

## For the Claude Code instance picking this up

Read these docs in order before writing code:

1. `docs/01_architecture.md` — the system design and *why* MPC. Read first.
2. `docs/02_control_core.md` — the LP/MPC formulation. The math you implement.
3. `docs/03_forecasting.md` — solar / load / price-tail models.
4. `docs/04_home_assistant.md` — data retrieval, InfluxDB sink, live loop, add-on.
5. `docs/05_llm_and_overrides.md` — explanation layer + override-as-constraint.
6. `docs/06_implementation_plan.md` — phased build order with acceptance criteria.

`energy_mpc.py` at the repo root is a **working, validated** control core
(solves with CVXPY + HiGHS). It is the seed everything else wraps around. Run it
to confirm your environment: `python energy_mpc.py`.

### Working principles for this project

- **The optimizer is the single source of truth for hardware actions.** The LLM
  proposes structured intent; it never emits setpoints.
- **Overrides compile to LP constraints**, never to `if`-statement code paths.
  Keep them composable and schema-validated.
- **Keep it an LP, not a MILP**, unless a specific requirement forces integers
  (see `docs/02`). LPs solve in milliseconds on a Raspberry Pi.
- **Receding horizon:** compute a long plan, actuate only the first timestep,
  re-solve next cycle.
- **Training is offline, control is online.** Heavy historical queries hit
  InfluxDB on a separate machine; the control loop only talks to HA live state.

### Resolved design decisions (do not re-litigate)

- Car charging is **single-phase**: `P_car_max = 13 A × 230 V ≈ 2990 W`.
- Export is **paid at raw spot price**. Import price = `spot × (1 + VAT) + grid_fee`.
  VAT + grid fee apply to **import only** — buy and sell prices are asymmetric.
- **Car may charge from the house battery** (no constraint forbidding it).
- The car is a **deferrable load with a deadline**, not an arbitrage asset
  (no V2G/V2H assumed).

### Open items to confirm with the user before/while building

- House battery **minimum SoC reserve** (don't deplete to 0 — health + buffer).
- Whether the hybrid inverter can **simultaneously import from grid AND discharge
  battery**. If it cannot, that becomes a MILP-requiring mutual-exclusion
  constraint (see `docs/02`).
- Exact **VAT rate** and **grid fee** (per-Wh) values.
- Round-trip **efficiencies** (measure on real hardware; defaults are 0.95 each).

---

## Repo layout (target)

```
kremla_energy_ai/
├── README.md                 # this file
├── energy_mpc.py             # validated control core (seed)
├── docs/
│   ├── 01_architecture.md
│   ├── 02_control_core.md
│   ├── 03_forecasting.md
│   ├── 04_home_assistant.md
│   ├── 05_llm_and_overrides.md
│   └── 06_implementation_plan.md
├── src/                      # to be built
│   ├── control/              # MPC core (from energy_mpc.py)
│   ├── forecasting/          # solar, load, price models
│   ├── ha/                   # Home Assistant I/O + InfluxDB
│   ├── llm/                  # explanation + override parsing
│   └── overrides/            # override schema + compiler
├── training/                 # offline model fitting (separate machine)
└── kremla_energy_mpc/        # Home Assistant add-on
```

## Tech stack

- **Optimization:** CVXPY + HiGHS (open-source, fast for LPs this size).
- **Forecasting:** LightGBM/XGBoost; clear-sky physics for solar baseline.
- **Time-series store:** InfluxDB (or TimescaleDB) fed by HA.
- **LLM:** pluggable — cloud API or local (Ollama) behind one interface.
- **Runtime:** Python; packaged as a Home Assistant add-on.

## Home Assistant add-on install

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**
2. Add: `https://github.com/niclashellberg/ordo-ems`
3. Install **Kremla Energy MPC**, configure entity IDs in `/data/options.yaml`, start.
4. API / ingress on port **8765** (`docs/API.md`).
