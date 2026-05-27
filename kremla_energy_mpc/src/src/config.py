"""Application configuration (add-on options / YAML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from src.control.plant import PlantConfig


@dataclass
class EntityConfig:
    """Home Assistant entity IDs — fill in via add-on options."""

    solar_power: str = "sensor.sungrow_solar_power"
    house_load: str = "sensor.house_load_power"
    house_soc: str = "sensor.sungrow_battery_soc"
    house_soc_energy: str = "sensor.sungrow_battery_energy"
    car_soc: str = "sensor.tesla_battery_level"
    car_energy: str = "sensor.tesla_battery"
    car_plugged: str = "binary_sensor.tesla_plugged_in"
    car_charge_limit: str = "number.tesla_charge_limit"
    nordpool: str = "sensor.nord_pool_se3_prices"
    # Actuation (vendor-specific — set to your Sungrow / Tesla control entities)
    battery_charge_power: str = "number.sungrow_battery_charge_power"
    battery_discharge_power: str = "number.sungrow_battery_discharge_power"
    car_charge_power: str = "number.tesla_charging_amps"


@dataclass
class ScheduleConfig:
    """Default car availability pattern (weekday unplug 07:00–17:00)."""

    unplug_start_hour: int = 7
    unplug_end_hour: int = 17
    workdays: tuple[int, ...] = (0, 1, 2, 3, 4)  # Mon–Fri (datetime.weekday())


@dataclass
class ModelConfig:
    """Forecast model bundle on NAS (HTTP or local mount)."""

    bundle_url: str = "http://nas.local/kremla/models/latest.tar.gz"
    local_path: Path = Path("/data/models")
    refresh_hours: int = 168  # weekly


@dataclass
class InfluxConfig:
    """Training host only — not used by the Pi control loop."""

    url: str = "http://nas.local:8086"
    org: str = "home"
    bucket: str = "homeassistant"
    token: str = ""


@dataclass
class ApiConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"


@dataclass
class LoopConfig:
    timestep_minutes: int = 15
    horizon_hours: int = 48
    interval_minutes: int = 15
    nordpool_publish_hour: int = 13
    nordpool_publish_minute: int = 1


@dataclass
class SaunaConfig:
    """Typical sauna session (~10 kWh per run) as extra_load override."""

    power_w: float = 6000.0
    duration_steps: int = 1  # one 15-min step at 6 kW ≈ 1.5 kWh; tune or stack steps
    energy_wh_per_run: float = 10_000.0


@dataclass
class AppConfig:
    homeassistant_url: str = "http://supervisor/core"
    homeassistant_token: str = ""
    plant: PlantConfig = field(default_factory=PlantConfig)
    entities: EntityConfig = field(default_factory=EntityConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    influx: InfluxConfig = field(default_factory=InfluxConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    loop: LoopConfig = field(default_factory=LoopConfig)
    sauna: SaunaConfig = field(default_factory=SaunaConfig)
    e_car_max_wh: float = 100_000.0
    car_target_soc_fraction: float = 0.90
    car_deadline_hour: int = 7  # must reach target by 07:00 next morning


def _merge_plant(data: dict[str, Any]) -> PlantConfig:
    plant = PlantConfig()
    if "plant" not in data:
        return plant
    p = data["plant"]
    for key, val in p.items():
        if hasattr(plant, key):
            setattr(plant, key, val)
    return plant


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig()
    raw = yaml.safe_load(path.read_text()) or {}
    cfg = AppConfig()
    cfg.plant = _merge_plant(raw)
    if "homeassistant" in raw:
        cfg.homeassistant_url = raw["homeassistant"].get("url", cfg.homeassistant_url)
        cfg.homeassistant_token = raw["homeassistant"].get("token", "")
    if "entities" in raw:
        for k, v in raw["entities"].items():
            if hasattr(cfg.entities, k):
                setattr(cfg.entities, k, v)
    if "loop" in raw:
        for k, v in raw["loop"].items():
            if hasattr(cfg.loop, k):
                setattr(cfg.loop, k, v)
    if "models" in raw:
        m = raw["models"]
        if "bundle_url" in m:
            cfg.models.bundle_url = m["bundle_url"]
        if "local_path" in m:
            cfg.models.local_path = Path(m["local_path"])
    if "api" in raw:
        for k, v in raw["api"].items():
            if hasattr(cfg.api, k):
                setattr(cfg.api, k, v)
    return cfg


def plant_from_config(cfg: AppConfig) -> PlantConfig:
    p = cfg.plant
    p.e_house_max = 51_400.0
    p.min_soc_fraction = 0.05
    return p
