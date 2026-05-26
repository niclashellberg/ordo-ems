# Ordo EMS

**Ordo EMS** brings order to home energy: a Home Assistant add-on that schedules
**house battery** charge/discharge and **EV charging** with **Model Predictive
Control (MPC)** — using Nord Pool prices, forecasts, and hard constraints (SoC,
power limits, car deadlines).

Repository: https://github.com/niclashellberg/ordo-ems

---

## Home Assistant add-on install

### 1. Add the repository (HTTPS only)

**Settings → Add-ons → Add-on store → ⋮ → Repositories**

Paste **exactly** (no `git@`, no `.git` suffix):

```text
https://github.com/niclashellberg/ordo-ems
```

Or open this link on a device logged into Home Assistant:

[Add Ordo EMS repository](https://my.home-assistant.io/redirect/supervisor/addon/store/?repository_url=https%3A%2F%2Fgithub.com%2Fniclashellberg%2Fordo-ems)

Then click **Add**, wait a few seconds, and **Check for updates**.

If you see `GitHub returned 404`, see **[docs/HA_INSTALL.md](docs/HA_INSTALL.md)** (network test, local add-on fallback). Do not use `git@github.com:...`.

### 2. Install the add-on

Under the new **Ordo EMS** section, install **Kremla Energy MPC** (v0.1.1+).

First build on a Pi can take **15–25 minutes** (installing cvxpy). Use **Rebuild** after repo updates.

### 3. Configure

- **Add-on → Configuration**: Nord Pool entity, NAS model URL, API key.
- **`/data/options.yaml`**: full entity list — template in `config/example.yaml`.

Before publishing add-on changes, run `./scripts/sync_addon.sh` so `kremla_energy_mpc/` contains real copies of `src/`.
4. API / ingress on port **8765** — see `docs/API.md`.

---

## For developers

Read these docs in order:

1. `docs/01_architecture.md` — system design
2. `docs/02_control_core.md` — LP/MPC formulation
3. `docs/03_forecasting.md` — solar / load / price models
4. `docs/04_home_assistant.md` — HA + InfluxDB
5. `docs/05_llm_and_overrides.md` — explanation layer
6. `docs/06_implementation_plan.md` — phased build

Run the control core: `PYTHONPATH=. python energy_mpc.py`

### Principles

- Optimizer is the **only** source of hardware setpoints; LLM explains and parses overrides.
- **Overrides → LP constraints**, not `if` branches.
- **LP on Pi** (CVXPY + HiGHS); training offline on NAS/InfluxDB.
- **15 min receding horizon**; actuate first step only.

---

## Repo layout

```
ordo-ems/
├── repository.yaml           # HA add-on repository manifest
├── kremla_energy_mpc/        # Home Assistant add-on
├── src/                      # Runtime application
├── config/example.yaml       # Entity IDs & plant config template
├── training/                 # Offline model fitting + Influx compose
├── docs/
├── tests/
└── energy_mpc.py             # MPC demo entry point
```

## Tech stack

- **Optimization:** CVXPY + HiGHS
- **Forecasting:** LightGBM (training machine)
- **Time-series:** InfluxDB on NAS
- **Runtime:** Python add-on on HAOS (Pi 5)

## License

See [LICENSE](LICENSE).

## Disclaimer

Ordo EMS influences battery and EV charging. Validate in a safe setup before relying on it for live control.
