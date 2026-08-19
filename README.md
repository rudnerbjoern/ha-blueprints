# Home Assistant Blueprints

Reusable Home Assistant blueprints by **Björn Rudner (@rudnerbjoern)**.

## Smart Ventilation

The first project in this repository is a modular ventilation system for Home Assistant.

It is designed to make room-level ventilation recommendations based on:

* Indoor temperature
* Outdoor temperature
* Indoor absolute water vapor concentration
* Outdoor absolute water vapor concentration
* Optional indoor relative humidity

The system is designed to work throughout the year and does not rely on fixed summer/winter modes.

### Components

#### Smart Ventilation Sensor

Template Blueprint for room-level ventilation evaluation.

It creates a sensor with one of these stable states:

* `ventilate`
* `conditional`
* `keep_closed`
* `neutral`

It also provides attributes including:

* Drying potential
* Temperature difference
* Recommendation reason
* Suggested purge-ventilation duration
* Dry-air protection status

Blueprint:

`blueprints/template/smart_ventilation_sensor.yaml`

Detailed documentation:

`docs/smart-ventilation.md`

### Planned Components

Additional blueprints are planned for:

* Floor-level aggregation
* Window monitoring
* Ventilation timing
* Close-window reminders
* Persistent notifications
* Mobile notifications
* Optional voice-assistant announcements

## Repository Structure

```text
ha-blueprints/
├── blueprints/
│   ├── template/
│   │   └── smart_ventilation_sensor.yaml
│   └── automation/
├── docs/
│   └── smart-ventilation.md
└── README.md
```

## Status

This repository is under active development.

The Smart Ventilation project is currently in its first testing phase and should be considered experimental until it has been validated against real-world climate data over a longer period.

## Author

Björn Rudner (@rudnerbjoern)
