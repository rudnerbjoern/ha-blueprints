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
* Candidate recommendation and pending close diagnostics
* Suggested purge-ventilation duration
* Dry-air protection status

Closing recommendations use a fresh-air-friendly comfort band by default:
small moisture disadvantages remain neutral, and a closing condition must stay
present for 15 minutes before `keep_closed` is published.

Blueprint:

`blueprints/template/smart_ventilation_sensor.yaml`

Detailed documentation:

* [English documentation](docs/smart-ventilation.md)
* [Deutsche Dokumentation](docs/smart-ventilation.de.md)

### Dashboard Card

The Home Assistant dashboard is maintained separately as a custom Lovelace
card:

[Smart Ventilation Card](https://github.com/rudnerbjoern/smart-ventilation-card)

The card consumes the stable sensor API provided by these blueprints. Dashboard
source code and installation instructions therefore live in the card
repository rather than this blueprint repository.

#### Smart Ventilation Floor

Template Blueprint for aggregating room recommendations into a floor-level
state.

It keeps the fresh-air-friendly behavior at floor level: `keep_closed` is only
published when all valid rooms agree. Mixed `keep_closed` and `neutral`
recommendations remain `neutral`.

Blueprint:

`blueprints/template/smart_ventilation_floor.yaml`

### Planned Components

Additional blueprints are planned for:

* Window monitoring
* Ventilation timing
* Close-window reminders
* Persistent notifications
* Mobile notifications
* Optional voice-assistant announcements

## Status

This repository is under active development.

The Smart Ventilation project is currently in its first testing phase and should be considered experimental until it has been validated against real-world climate data over a longer period.

## Author

Björn Rudner (@rudnerbjoern), with the help of AI 😉
