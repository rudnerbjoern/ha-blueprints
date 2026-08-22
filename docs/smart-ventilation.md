# Smart Ventilation

Smart Ventilation is a modular Home Assistant blueprint project for intelligent, room-based ventilation recommendations.

The goal is to determine whether opening a window is currently beneficial by comparing indoor and outdoor climate conditions.

The system is designed to work throughout the year without requiring a fixed summer or winter mode.

---

## Smart Ventilation Sensor

`smart_ventilation_sensor.yaml` is a Home Assistant Template Blueprint.

It is intended to be instantiated once per room.

Each instance evaluates:

* Indoor temperature
* Outdoor temperature
* Indoor water vapor concentration
* Outdoor water vapor concentration
* Optional indoor relative humidity

The generated sensor provides a recommendation state together with diagnostic
attributes that can later be consumed by dashboards and automation blueprints.

The dashboard UI is maintained as the separate
[Smart Ventilation Card](https://github.com/rudnerbjoern/smart-ventilation-card).
This repository defines the sensor API; the card repository contains the UI,
installation instructions, and releases.

---

## Sensor States

The sensor uses stable, language-independent states.

| State         | Meaning                                                 |
| ------------- | ------------------------------------------------------- |
| `ventilate`   | Ventilation is recommended                              |
| `conditional` | Ventilation may be useful, but conditions are not ideal |
| `keep_closed` | Windows should remain closed                            |
| `neutral`     | No meaningful ventilation advantage exists              |
| `unavailable` | One or more required input sensors are unavailable      |

Machine-readable states are intentionally used so that automations do not depend on the user's Home Assistant language.

---

## Drying Potential

The central value used by Smart Ventilation is the difference between indoor and outdoor water vapor concentration.

```text
drying_potential =
indoor_vapor_concentration - outdoor_vapor_concentration
```

Example:

```text
Indoor:  9.2 g/m³
Outdoor: 5.1 g/m³

Drying potential: 4.1 g/m³
```

A positive value means that outdoor air contains less water vapor than indoor air.

The higher the value, the greater the potential for removing indoor moisture through ventilation.

### Default Classification

| Drying potential         | Level               |
| -----------------------: | ------------------- |
| below −2.0 g/m³          | `negative`          |
| −2.0 to below 0 g/m³     | `slightly_negative` |
| 0 to below 0.8 g/m³      | `low`               |
| 0.8–2.0 g/m³             | `moderate`          |
| 2.0–4.0 g/m³             | `high`              |
| 4.0 g/m³ or more         | `very_high`         |

All thresholds are configurable.

The opening and closing thresholds are intentionally asymmetric. By default,
ventilation becomes useful at +0.8 g/m³, while a moisture-related closing
candidate only starts at −2.0 g/m³. The range between them is neutral and
allows fresh-air ventilation to continue without claiming a drying benefit.

## Keep-closed confirmation

Every `keep_closed` candidate must remain present continuously for 15 minutes
before the public state changes to `keep_closed`. While confirmation is
pending, the public state is `neutral` with reason `keep_closed_pending`.

`ventilate`, `conditional`, and ordinary `neutral` candidates are published
immediately. A confirmed closing recommendation is also cleared immediately
when its cause disappears. The pending state is exposed through diagnostic
attributes:

```text
candidate_recommendation
candidate_reason
keep_closed_pending
keep_closed_pending_since
keep_closed_confirmation_minutes
maximum_acceptable_negative_drying_potential
```

---

## Cold Weather Behavior

Cold outdoor air is not automatically considered unsuitable for ventilation.

Cold air often contains substantially less absolute moisture than warm indoor air. Short purge ventilation can therefore remove moisture very effectively during winter.

Example:

```text
Indoor temperature: 21 °C
Outdoor temperature: -5 °C

Indoor vapor concentration: 10.0 g/m³
Outdoor vapor concentration: 4.0 g/m³

Drying potential: 6.0 g/m³
```

Possible result:

```text
state: ventilate
reason: outdoor_air_much_drier_and_cold
recommended_duration_minutes: 3
```

The low suggested duration is intended to limit unnecessary heat loss.

---

## Dry-Air Protection

Ventilation should not continuously dry indoor air during cold weather.

If an indoor relative-humidity sensor is configured, it is used as the preferred dry-air protection input.

Default threshold:

```text
35 % RH
```

If indoor relative humidity falls below this threshold, further drying ventilation is suppressed.

Possible result:

```text
state: keep_closed
reason: indoor_air_already_dry
```

If no relative-humidity sensor is configured, absolute indoor water vapor concentration is used as a fallback.

Default fallback:

```text
5.5 g/m³
```

---

## Warm Weather Behavior

Outdoor temperature is treated mainly as a thermal disadvantage rather than an absolute ventilation prohibition.

### Slightly warmer outdoor air

If outdoor air is somewhat warmer but sufficiently drier than indoor air:

```text
state: conditional
```

This indicates that moisture removal may still be beneficial, but ventilation has a thermal cost.

### Much warmer outdoor air

If outdoor air is significantly warmer, the default recommendation is:

```text
keep_closed
```

However, very strong drying potential can override this to:

```text
conditional
```

This allows short moisture-removal ventilation in exceptional cases.

---

## Default Temperature Thresholds

Temperature difference is calculated as:

```text
outdoor_temperature - indoor_temperature
```

Default thresholds:

```text
Warmer outdoor air:       +1.0 °C
Much warmer outdoor air:  +3.0 °C
```

---

## Suggested Ventilation Duration

Smart Ventilation estimates a suggested purge-ventilation duration.

The calculation uses three components:

1. Outdoor-temperature base duration
2. Drying-potential correction
3. Thermal-disadvantage correction

### Base Durations

| Outdoor temperature | Base duration |
| ------------------- | ------------: |
| below 0 °C          |         4 min |
| 0–5 °C              |         5 min |
| 5–10 °C             |         7 min |
| 10–15 °C            |        10 min |
| 15–20 °C            |        15 min |
| above 20 °C         |        20 min |

### Drying-Potential Correction

Strong drying potential shortens the suggested duration.

Current factors:

```text
very_high drying potential: × 0.70
high drying potential:      × 0.85
moderate drying potential:  × 1.00
```

### Thermal Correction

When outdoor air is warmer than indoor air, the duration is shortened.

```text
warmer:       × 0.65
much warmer:  × 0.50
```

Example:

```text
Outdoor temperature: 28 °C
Base duration: 20 min

Very high drying potential:
20 × 0.70 = 14 min

Outdoor air much warmer:
14 × 0.50 = 7 min
```

Result:

```text
recommended_duration_minutes: 7
```

---

## Important Note About Duration

The suggested duration is an estimate.

It is **not** a calculated air-exchange time.

Actual ventilation efficiency depends on factors that the blueprint currently does not know, including:

* Room volume
* Window size
* Opening angle
* Wind
* Pressure differences
* Cross ventilation
* Number of open windows

The duration should therefore be interpreted as:

> Suggested purge-ventilation duration

rather than:

> Optimal ventilation duration

Future versions may optionally account for room and window characteristics.

---

## Sensor Attributes

The generated sensor exposes the following attributes.

### API

```text
api_version
```

### Recommendation

```text
reason
```

### Temperature

```text
indoor_temperature
outdoor_temperature
temperature_difference
thermal_condition
```

### Moisture

```text
indoor_vapor_concentration
outdoor_vapor_concentration
drying_potential
drying_potential_level
```

### Dry-Air Protection Attributes

```text
indoor_relative_humidity
dry_air_protection_active
dry_air_protection_source
```

### Duration

```text
recommended_duration_minutes
```

Duration values are only provided when the recommendation is:

```text
ventilate
conditional
```

For `neutral` and `keep_closed`, duration values are empty.

---

## Reason Codes

The `reason` attribute uses machine-readable values.

Current values include:

```text
indoor_air_already_dry
outdoor_air_more_humid
strong_drying_benefit_but_much_warmer
outdoor_air_much_warmer
outdoor_air_drier_but_warmer
outdoor_air_much_drier_and_cold
outdoor_air_significantly_drier
outdoor_air_drier
conditions_similar
keep_closed_pending
```

Future automation blueprints can translate these reason codes into localized notification text.

---

## Required Sensors

Every room requires:

* Indoor temperature
* Indoor water vapor concentration
* Outdoor temperature
* Outdoor water vapor concentration

Optional:

* Indoor relative humidity

Outdoor sensors can be shared across all room instances.

Example:

```text
Outdoor temperature ───────────────┐
Outdoor vapor concentration ───────┤
                                   │
Living Room indoor sensors ────────┼─ Smart Ventilation Sensor
                                   │
Bedroom indoor sensors ────────────┼─ Smart Ventilation Sensor
                                   │
Bathroom indoor sensors ───────────┼─ Smart Ventilation Sensor
                                   │
Office indoor sensors ─────────────┘
```

Each room receives its own independent recommendation.

---

## Blueprint Updates

The sensor recalculates when one of the primary climate inputs changes and
additionally every minute.

This periodic update also provides a fallback for:

* Sensor recovery
* Optional relative-humidity changes
* Template reloads
* Home Assistant restarts

The physical measurements still change only when their source sensors deliver
new values. The minute trigger does not invent measurements; it reevaluates
the most recently available valid values.

---

## Architecture

Smart Ventilation is intended to become a modular system.

### Room-Level Sensor

Room-level physical evaluation.

```text
Indoor climate
      +
Outdoor climate
      ↓
Smart Ventilation Sensor
```

### Smart Ventilation Floor

`smart_ventilation_floor.yaml` is the Template Blueprint for aggregating
multiple room recommendations into a floor-level state. The floor publishes
`keep_closed` only when every valid room publishes `keep_closed`. A mixture
of `keep_closed` and `neutral` remains `neutral`, with reason
`mixed_keep_closed_and_neutral`, so one room does not close an otherwise
fresh-air-compatible floor. Explicit `ventilate` versus `keep_closed`
conflicts and all `conditional` recommendations remain visible as
`conditional`. The former thermal Floor override no longer changes the public
state; a possible thermal hint remains available only through the diagnostic
`thermal_override_candidate` attribute.

### Smart Ventilation Control

Planned Automation Blueprint responsible for:

* Window monitoring
* Detecting ventilation start
* Tracking suggested duration
* Close-window reminders
* Persistent notifications
* Mobile notifications
* Optional voice-assistant announcements

This separation keeps physical climate evaluation independent from notification and window-control logic.

---

## Default Configuration

Current defaults:

```text
Minimum drying potential:        0.8 g/m³
Accepted negative potential:     2.0 g/m³
Keep-closed confirmation:        15 min
Strong drying potential:         2.0 g/m³
Very strong drying potential:    4.0 g/m³

Warmer outdoor threshold:        +1.0 °C
Much warmer outdoor threshold:   +3.0 °C

Minimum indoor RH:               35 %
Minimum indoor vapor fallback:   5.5 g/m³

Minimum suggested duration:      2 min
Maximum suggested duration:      30 min
```

Every value is configurable independently for each blueprint instance.

---

## Status

Smart Ventilation is currently under active development.

The initial sensor blueprint should be considered experimental until its behavior has been validated against real-world climate data across different seasons.

---

## Author

Björn Rudner (@rudnerbjoern), with the help of AI 😉
