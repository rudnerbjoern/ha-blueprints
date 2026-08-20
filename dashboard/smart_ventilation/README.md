# Smart Ventilation Dashboard

Reusable `custom:button-card` components for the Smart Ventilation blueprints.

The dashboard package contains three templates:

- `vent_room` — detailed Room API v1 card
- `vent_floor` — Floor API v2 summary card with window-state validation
- `vent_floor_header` — compact header for a floor detail block

The templates are intentionally separate from the blueprints. The blueprints provide
the data and automation logic; these cards only visualize that public API.

## Requirement

Install [`custom:button-card`](https://github.com/custom-cards/button-card) before using these templates.

No Mushroom card, card-mod or other Lovelace dependency is required by these three templates.

## Installation

Copy the contents of the three template files into the dashboard's top-level
`button_card_templates:` mapping:

```yaml
button_card_templates:
  vent_room:
    # content below `vent_room:` from vent_room.yaml

  vent_floor:
    # content below `vent_floor:` from vent_floor.yaml

  vent_floor_header:
    # content below `vent_floor_header:` from vent_floor_header.yaml
```

If the dashboard already contains `button_card_templates:`, merge these entries
into the existing mapping. Do not create a second top-level `button_card_templates:` key.

Then copy one of the examples and replace the example entity IDs with entities from
your installation.

## Files

| File                     | Purpose                                                                                                         |
| ------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `vent_room.yaml`         | Detailed room recommendation, indoor/outdoor climate, heating, window chip and touch-friendly More-Info actions |
| `vent_floor.yaml`        | Floor recommendation, current window compliance, Room duration range and icon status badge                      |
| `vent_floor_header.yaml` | Compact floor heading with window count                                                                         |
| `example_room_card.yaml` | Minimal standalone room example                                                                                 |
| `example_floor.yaml`     | Full floor summary + header + two room cards                                                                    |

## Public API expectations

### Room card

The card's `entity:` must be a **Smart Ventilation Room API v1** sensor.

Supported Room states:

- `ventilate`
- `conditional`
- `keep_closed`
- `neutral`

The card reads `recommended_duration_minutes` and shows it only when ventilation
is actually recommended.

### Floor card

The card's `entity:` must be a **Smart Ventilation Floor API v2** sensor.

The Floor card reads these room-bucket attributes when available:

- `ventilate_rooms`
- `conditional_rooms`
- `keep_closed_rooms`
- `neutral_rooms`

It does **not** invent a Floor duration. Instead it reads each listed Room sensor's
`recommended_duration_minutes` and displays either one value or a range.

## `vent_room` variables

| Variable       | Required | Description                                            |
| -------------- | -------: | ------------------------------------------------------ |
| `accent`       |      yes | Accent color for the room/card                         |
| `temp`         |      yes | Indoor temperature sensor                              |
| `hum`          |      yes | Indoor relative humidity sensor                        |
| `abs`          |      yes | Indoor absolute humidity / vapor concentration sensor  |
| `outside_temp` |      yes | Outdoor temperature sensor                             |
| `outside_hum`  |      yes | Outdoor relative humidity sensor                       |
| `outside_abs`  |      yes | Outdoor absolute humidity / vapor concentration sensor |
| `windows`      |      yes | List of window / door `binary_sensor` entities         |
| `heating`      |      yes | Room `climate` entity                                  |
| `valves`       |       no | List of valve-opening sensors; defaults to `[]`        |

### Room interaction

The outer card opens the Room sensor. Climate rows open the corresponding indoor
or outdoor sensor. The heating panel opens the configured `climate` entity. The
window chip opens the single configured window, or the single currently open
window when multiple windows are configured; otherwise it falls back to the Room sensor.

### Room responsive behavior

The climate and heating panels are stacked on narrow room cards. At a card width
of 560 px or more they switch to a two-column layout. This intentionally uses a
container query instead of the browser viewport.

## `vent_floor` variables

| Variable          | Required | Description                                                      |
| ----------------- | -------: | ---------------------------------------------------------------- |
| `accent`          |      yes | Accent color for the floor/card                                  |
| `opening_windows` |      yes | Windows/doors that may be opened for ventilation                 |
| `closing_windows` |       no | Subset to close for `keep_closed`; defaults to `opening_windows` |
| `windows`         |       no | Compatibility alias/fallback for `opening_windows`               |

The Floor card validates the Floor API version, the configured closing-window
subset and the current binary on/off states before displaying window compliance.

Its icon badge is attached directly to the icon cell:

- green `✓` — current window state matches the recommendation
- red `!` — open/close action required
- orange `?` — conditional recommendation
- gray `−` — neutral
- gray `!` — unavailable/invalid data

## `vent_floor_header` variables

| Variable  | Required | Description                                         |
| --------- | -------: | --------------------------------------------------- |
| `accent`  |      yes | Accent color for the floor                          |
| `windows` |      yes | Windows/doors represented by the floor detail block |

## Example

See `example_floor.yaml` for the recommended composition.
