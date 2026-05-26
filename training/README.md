# Offline training (NAS / workstation — not on the Pi)

The Raspberry Pi only **loads** serialized models and runs MPC inference.
Retrain on a machine with access to InfluxDB.

## How often to refresh models

| Model | Suggested cadence | Why |
|-------|-------------------|-----|
| Solar | **Weekly** in spring/autumn, monthly in stable seasons | Cloud cover and sun angle shift |
| Load | **Weekly** | Weekday/weekend patterns change slowly |
| Price tail | **Monthly** | Terminal value absorbs much error; Nord Pool shape is stable |

Ship a new `latest.tar.gz` to the NAS; the add-on downloads it when
`models.refresh_hours` elapses (default **168 h = weekly**).

## InfluxDB on NAS (Docker / Portainer)

1. Deploy `training/docker-compose.influx.yaml` on the NAS.
2. In Home Assistant: **Settings → Devices & services → Add integration → InfluxDB**
   - URL: `http://<nas-ip>:8086`
   - Org / bucket / token as in the compose file
3. Log at **1–5 min** for power sensors; hourly for prices is enough.

### Tags to log (minimum)

- `sensor.sungrow_*` production, battery SoC/energy, grid power
- House load (computed or sensor)
- Tesla SoC, plugged-in state
- `sensor.nord_pool_se3_prices`
- Weather: outdoor temp, cloud cover / GHI if available
- **Controller predictions** each solve cycle (for backtest / drift warnings)

## Training scripts (to implement)

```
training/
  fit_solar.py    → clear-sky (pvlib) + LightGBM ratio model
  fit_load.py     → LightGBM on lags + weather + calendar
  fit_price.py    → price tail for 00:00–13:00 gap
  export_bundle.py → tar.gz for NAS
```

Bundle layout expected by the add-on:

```
models/
  bundle.pkl      # or versioned joblib artifacts + manifest.json
  manifest.json   # version, trained_at, metrics
```

## Manual workflow

```bash
cd training
pip install -r requirements-train.txt
export INFLUX_URL=http://nas.local:8086 INFLUX_TOKEN=... INFLUX_ORG=home INFLUX_BUCKET=homeassistant
python fit_solar.py && python fit_load.py && python fit_price.py
python export_bundle.py -o /path/on/nas/kremla/models/latest.tar.gz
```

The Pi add-on pulls from `models.bundle_url` in `config/example.yaml`.
