# Ordo EMS

**Ordo EMS** is a Home Assistant integration for residential energy management, built around a **Model Predictive Control (MPC)** controller.  
Its primary goal is to optimize battery charging and discharging by planning ahead using electricity prices, load forecasts, and local generation such as solar PV.

Ordo brings *order to home energy*.

---

## Key Concepts

Ordo EMS treats the home as an energy system rather than a collection of devices.  
At regular intervals, an MPC controller solves an optimization problem over a future horizon and determines the optimal battery power trajectory while respecting system constraints.

High-level goals typically include:
- Minimizing electricity cost
- Maximizing self-consumption
- Avoiding peak power usage
- Preserving battery health

---

## Features (Planned / In Progress)

- Model Predictive Control (MPC) for battery optimization
- Native Home Assistant integration
- Support for dynamic electricity pricing
- Load and production forecasting
- Configurable optimization objectives
- System constraints (SOC, power limits, efficiency)
- Exposed sensors and entities for dashboards and automations
- Manual override and fallback control modes

---

## Architecture Overview

Home Assistant
│
├── Sensors
│ ├── Electricity price
│ ├── Household load
│ ├── Solar production
│ └── Battery state
│
├── Ordo EMS Integration
│ ├── Data aggregation
│ ├── Forecast handling
│ ├── MPC controller
│ └── Control output
│
└── Battery / Inverter



The MPC controller periodically:
1. Collects current state and forecasts
2. Solves an optimization problem over a finite horizon
3. Outputs a battery charge/discharge setpoint
4. Exposes results to Home Assistant

---

## Requirements

- Home Assistant (Core or OS)
- A controllable home battery system
- Electricity price data (e.g. Nord Pool, Tibber, etc.)
- Python 3.11+ (for development)
- Optimization backend (e.g. cvxpy, casadi, or similar)

Exact requirements may evolve as the project matures.

---

## Installation

> ⚠️ Not yet released

Planned installation methods:
- HACS (recommended)
- Manual installation via `custom_components/ordo_ems`

Detailed installation steps will be added later.

---

## Configuration

Initial configuration will likely include:
- Battery capacity and limits
- Charge/discharge power limits
- Efficiency parameters
- Optimization horizon
- Objective weighting (cost vs self-consumption)

Configuration will be handled via:
- `configuration.yaml`
- UI-based config flow (planned)

---

## Entities

Expected entities exposed to Home Assistant:
- Battery charge/discharge setpoint
- Optimization status
- Forecasted SOC
- Current control mode
- Optimization cost / objective value

Entity list is subject to change.

---

## Control Modes

- **Automatic (MPC)** – Fully predictive control
- **Manual** – User-defined charge/discharge
- **Disabled** – Read-only monitoring

---

## Roadmap

- [ ] Initial Home Assistant integration
- [ ] Basic MPC controller
- [ ] Price-based optimization
- [ ] Solar + load forecasting
- [ ] UI configuration flow
- [ ] Battery vendor adapters
- [ ] Documentation and examples

---

## Development

This project is under active development.

Contributions are welcome, especially in:
- MPC modeling
- Forecasting methods
- Home Assistant integration patterns
- Documentation and testing

---

## Disclaimer

Ordo EMS directly influences energy storage behavior.  
Use at your own risk. Always validate control logic in a safe environment before deploying to a live system.

---

## License

TBD
