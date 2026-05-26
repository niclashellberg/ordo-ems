"""Static plant configuration."""

from dataclasses import dataclass


@dataclass
class PlantConfig:
    """Sungrow SH10 + Tesla Model S defaults (overridable via add-on config)."""

    p_hc_max: float = 10_000.0
    p_hd_max: float = 10_000.0
    p_car_max: float = 13 * 230.0
    p_exp_max: float = 12_000.0
    e_house_max: float = 51_400.0
    min_soc_fraction: float = 0.05

    eta_c: float = 0.95
    eta_d: float = 0.95
    eta_car: float = 0.95

    vat: float = 0.25
    grid_fee_per_wh: float = 17.2 / 100.0 / 1000.0
    energy_tax_per_wh: float = 36.0 / 100.0 / 1000.0

    @property
    def soc_house_min_wh(self) -> float:
        return self.e_house_max * self.min_soc_fraction
