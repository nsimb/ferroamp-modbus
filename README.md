# Ferroamp Modbus — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/danielolsson100/ferroamp-modbus.svg)](https://github.com/danielolsson100/ferroamp-modbus/releases)
[![License](https://img.shields.io/github/license/danielolsson100/ferroamp-modbus.svg)](LICENSE)

A Home Assistant custom integration for the **Ferroamp Energy Hub** using Modbus TCP. Provides real-time monitoring of solar production, battery state, grid power, and control of battery mode and grid import/export limits.

> **Prerequisite:** Modbus TCP must be enabled on your Ferroamp Energy Hub. If it is not, contact [Ferroamp support](https://support.ferroamp.com/sv-SE/support/tickets/new) to have it activated.
> 
> **Prerequisite:** The system's Operation Settings in portal.ferroamp.com must be set to "PEAK SHAVING".
> 
> **Security note:** Modbus TCP communicates without authentication, so do not expose the Ferroamp Energy Hub directly to the Internet without a proper firewall in place.

> **Disclaimer:** This integration can affect your energy system and network. Only use it if you understand what you are doing; if you are unsure, do not continue and do not hold the author responsible for unintended consequences.

---

## Features

- **Sensors** — solar power, battery state of charge, grid power, inverter data, energy totals, and more
- **Binary sensors** — import/export limit active states
- **Switches** — enable/disable the grid import and export limits with a single toggle
- **Number controls** — set grid import and export thresholds (W)
- **Two poll intervals** — fast (5 s) for control registers, standard (30 s) for all others
- **Config flow** — set up entirely from the Home Assistant UI, no YAML required

---

## Installation

### Via HACS (recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `danielolsson100/ferroamp-modbus` with category **Integration**
4. Search for **Ferroamp Modbus** and click **Download**
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/ferroamp_modbus/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Ferroamp Modbus**
3. Enter the **IP address** and **port** (default: `502`) of your Ferroamp Energy Hub
4. Click **Submit**

---

## Entities

### Sensors

| Entity | Unit | Description |
|--------|------|-------------|
| Solar Power | kW | Total DC solar input power |
| Energy Produced | kWh | Lifetime solar energy produced |
| Battery Power | kW | Battery charge (+) / discharge (−) power |
| State of Charge | % | Battery state of charge |
| State of Health | % | Battery state of health |
| Rated Capacity | kWh | Battery rated energy capacity |
| Grid Active Power | kW | Grid import (+) / export (−) power |
| Inverter Active Power | kW | Inverter AC output power |
| Grid Voltage L1/L2/L3 | V | Per-phase grid voltage |
| Grid Frequency | Hz | Grid frequency |
| Energy Imported From Grid | kWh | Lifetime grid import energy |
| Energy Exported To Grid | kWh | Lifetime grid export energy |
| Energy From Battery | kWh | Lifetime energy discharged from battery |
| Energy To Battery | kWh | Lifetime energy charged to battery |
| Battery Mode System Value | — | Active battery operating mode |
| Battery Power Reference | kW | Active battery power setpoint |
| Import Threshold System Value | W | Active grid import limit |
| Export Threshold System Value | W | Active grid export limit |
| Running / Idle / Faulty Batteries | — | Battery unit status counts |
| Running / Idle / Faulty SSOs | — | Solar string optimizer status counts |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| Limit Import Active | Whether a grid import limit is currently enforced |
| Limit Export Active | Whether a grid export limit is currently enforced |

### Switches

| Entity | Description |
|--------|-------------|
| Limit Import | Toggle the grid import limit on or off |
| Limit Export | Toggle the grid export limit on or off |

> **Tip:** Use the switches for quick on/off control of the limits. The Number controls above still let you set the exact threshold values independently.

### Number Controls

| Entity | Unit | Range | Description |
|--------|------|-------|-------------|
| Import Threshold | W | Configurable to match house fuse | Set the grid import power limit |
| Export Threshold | W | Configurable to match house fuse | Set the grid export power limit |

> **Import/Export Guardrail:** The **Import value must always be equal to or greater than the Export value**. This constraint is enforced in the configuration UI — if you enter an Import value lower than the Export value, the form will show an error and prevent saving. Ensure both thresholds are set consistently when using automations.

### Example Use Cases

1. Charging the EV while protecting the house fuse
   - Set Import = -11000 and Export = 11000
   - This forces the system to use battery energy for peak shaving and avoids blowing the house fuse.
2. Use PV energy or store excess in the battery
   - Set Import = 0 and Export = 0
   - This allows the system to use only local generation and battery storage without drawing or exporting power.
3. High electricity price while the sun is shining
   - Set thresholds to sell excess PV energy and use battery power before importing from the grid.
   - Example: Import = 0, Export = 11000.

### Automation Example

Use a Home Assistant automation to set import/export values with the number entities:

> **Control note:** Do not mix Modbus and MQTT for battery control — that is the way to the dark side. Prefer MQTT only for sensor data and use Modbus for battery control.

```yaml
alias: Set Ferroamp Import/Export Thresholds
description: Set import/export thresholds for battery and PV control
trigger:
  - platform: time
    at: '18:00:00'
condition: []
action:
  - action: number.set_value
    target:
      entity_id: number.ferroamp_energy_hub_import_threshold
    data:
      value: -11000
  - action: number.set_value
    target:
      entity_id: number.ferroamp_energy_hub_export_threshold
    data:
      value: 11000
mode: single
```

---

## Changelog

### 0.1.0
- Added **Limit Import** and **Limit Export** switches for easier one-tap control of import/export limiting
- Fixed a bug introduced in 0.0.5 where the import/export threshold controls failed on a clean Home Assistant installation (coordinators were missing their register-list initialisation — a classic "works on my computer" mistake)

---

## Requirements

- Home Assistant 2024.1 or newer
- Ferroamp Energy Hub with **Modbus TCP enabled**
- Network access from HA to the Energy Hub on TCP port 502

---

## Contributing

Issues and pull requests are welcome at [github.com/danielolsson100/ferroamp-modbus](https://github.com/danielolsson100/ferroamp-modbus/issues).
