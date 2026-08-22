import pytest

from tests.helpers import BLUEPRINT_ROOT, load_home_assistant_yaml


FLOOR_BLUEPRINT = (
    BLUEPRINT_ROOT
    / "template"
    / "smart_ventilation_floor.yaml"
)


def aggregate_floor(
    *,
    ventilate: int,
    conditional: int,
    keep_closed: int,
    neutral: int = 0,
    average_temperature_difference: float = 0.0,
    thermal_override_threshold: float = 1.0,
) -> tuple[str, str]:
    """Reference model for the Floor blueprint aggregation contract."""
    if ventilate > 0 and keep_closed > 0:
        return "conditional", "conflicting_room_recommendations"

    if conditional > 0:
        return "conditional", "conditional_room_present"

    if ventilate > 0:
        return "ventilate", "ventilation_recommended"

    room_count = ventilate + conditional + keep_closed + neutral

    if keep_closed > 0 and keep_closed == room_count:
        return "keep_closed", "all_rooms_keep_closed"

    if keep_closed > 0:
        return "neutral", "mixed_keep_closed_and_neutral"

    return "neutral", "all_rooms_neutral"


def test_blueprint_contract_and_api_versions():
    document = load_home_assistant_yaml(FLOOR_BLUEPRINT)

    assert document["blueprint"]["domain"] == "template"
    assert (
        str(document["blueprint"]["homeassistant"]["min_version"])
        == "2024.11.0"
    )

    attributes = document["sensor"]["attributes"]

    assert attributes["api_version"] == "2"
    assert attributes["room_api_version_required"] == "1"


def test_source_url_stays_on_dev():
    metadata = load_home_assistant_yaml(FLOOR_BLUEPRINT)["blueprint"]

    assert "/blob/dev/" in metadata["source_url"]


def test_room_trigger_reacts_to_attribute_only_changes():
    document = load_home_assistant_yaml(FLOOR_BLUEPRINT)

    trigger = next(
        item
        for item in document["triggers"]
        if item.get("id") == "room_change"
    )

    assert trigger["trigger"] == "state"
    assert "from" not in trigger
    assert "to" not in trigger


def test_five_minute_reconciliation_fallback_is_preserved():
    document = load_home_assistant_yaml(FLOOR_BLUEPRINT)

    trigger = next(
        item
        for item in document["triggers"]
        if item.get("id") == "reconcile"
    )

    assert trigger["trigger"] == "time_pattern"
    assert trigger["minutes"] == "/5"


@pytest.mark.parametrize(
    (
        "ventilate",
        "conditional",
        "keep_closed",
        "neutral",
        "temperature_difference",
        "expected_state",
        "expected_reason",
    ),
    [
        pytest.param(
            0, 0, 0, 3, 0.0,
            "neutral", "all_rooms_neutral",
            id="all-neutral",
        ),
        pytest.param(
            1, 0, 0, 2, 0.0,
            "ventilate", "ventilation_recommended",
            id="single-ventilate",
        ),
        pytest.param(
            2, 0, 0, 1, 5.0,
            "ventilate", "ventilation_recommended",
            id="multiple-ventilate-even-when-warm",
        ),
        pytest.param(
            0, 1, 0, 2, 0.0,
            "conditional", "conditional_room_present",
            id="single-conditional",
        ),
        pytest.param(
            0, 0, 1, 2, 0.0,
            "neutral", "mixed_keep_closed_and_neutral",
            id="single-keep-closed-with-neutral-rooms",
        ),
        pytest.param(
            1, 0, 1, 1, 0.0,
            "conditional", "conflicting_room_recommendations",
            id="ventilate-plus-keep-closed-conflict",
        ),
        pytest.param(
            1, 1, 1, 0, 5.0,
            "conditional", "conflicting_room_recommendations",
            id="direct-conflict-outranks-thermal-override",
        ),
        pytest.param(
            0, 1, 1, 0, 0.9,
            "conditional", "conditional_room_present",
            id="conditional-plus-closed-below-thermal-threshold",
        ),
        pytest.param(
            0, 1, 1, 0, 1.0,
            "conditional", "conditional_room_present",
            id="thermal-diagnostic-does-not-override-at-threshold",
        ),
        pytest.param(
            0, 2, 1, 0, 3.0,
            "conditional", "conditional_room_present",
            id="thermal-diagnostic-does-not-override-conditionals",
        ),
        pytest.param(
            1, 1, 0, 0, 5.0,
            "conditional", "conditional_room_present",
            id="conditional-outranks-ventilate",
        ),
        pytest.param(
            0, 0, 2, 1, 5.0,
            "neutral", "mixed_keep_closed_and_neutral",
            id="keep-closed-plus-neutral",
        ),
        pytest.param(
            0, 0, 3, 0, 5.0,
            "keep_closed", "all_rooms_keep_closed",
            id="unanimous-keep-closed",
        ),
    ],
)
def test_floor_aggregation_regression_matrix(
    ventilate,
    conditional,
    keep_closed,
    neutral,
    temperature_difference,
    expected_state,
    expected_reason,
):
    assert aggregate_floor(
        ventilate=ventilate,
        conditional=conditional,
        keep_closed=keep_closed,
        neutral=neutral,
        average_temperature_difference=temperature_difference,
    ) == (
        expected_state,
        expected_reason,
    )


@pytest.mark.parametrize(
    ("temperature_difference", "threshold", "expected_state"),
    [
        pytest.param(0.99, 1.0, "conditional", id="just-below-threshold"),
        pytest.param(1.00, 1.0, "conditional", id="exact-threshold"),
        pytest.param(1.01, 1.0, "conditional", id="just-above-threshold"),
        pytest.param(2.99, 3.0, "conditional", id="custom-threshold-below"),
        pytest.param(3.00, 3.0, "conditional", id="custom-threshold-exact"),
    ],
)
def test_thermal_diagnostic_never_overrides_room_recommendations(
    temperature_difference,
    threshold,
    expected_state,
):
    state, _ = aggregate_floor(
        ventilate=0,
        conditional=1,
        keep_closed=1,
        average_temperature_difference=temperature_difference,
        thermal_override_threshold=threshold,
    )

    assert state == expected_state


@pytest.mark.parametrize(
    ("ventilate", "conditional", "keep_closed", "temperature_difference"),
    [
        pytest.param(1, 0, 1, 10.0, id="direct-conflict"),
        pytest.param(1, 1, 1, 10.0, id="direct-conflict-with-conditional"),
    ],
)
def test_explicit_ventilate_is_never_hidden_by_thermal_override(
    ventilate,
    conditional,
    keep_closed,
    temperature_difference,
):
    state, reason = aggregate_floor(
        ventilate=ventilate,
        conditional=conditional,
        keep_closed=keep_closed,
        average_temperature_difference=temperature_difference,
    )

    assert state == "conditional"
    assert reason == "conflicting_room_recommendations"


def test_floor_exposes_room_buckets_and_thermal_diagnostics():
    attributes = load_home_assistant_yaml(
        FLOOR_BLUEPRINT
    )["sensor"]["attributes"]

    expected = {
        "room_count",
        "invalid_rooms",
        "ventilate_count",
        "conditional_count",
        "keep_closed_count",
        "neutral_count",
        "ventilate_rooms",
        "conditional_rooms",
        "keep_closed_rooms",
        "neutral_rooms",
        "average_indoor_temperature",
        "minimum_indoor_temperature",
        "maximum_indoor_temperature",
        "average_outdoor_temperature",
        "minimum_outdoor_temperature",
        "maximum_outdoor_temperature",
        "outdoor_temperature_spread",
        "average_temperature_difference",
        "minimum_temperature_difference",
        "maximum_temperature_difference",
        "average_drying_potential",
        "maximum_drying_potential",
        "outside_warmer_than_floor",
        "outside_warmer_than_all_rooms",
        "thermal_override_active",
        "thermal_override_candidate",
    }

    assert expected <= set(attributes)


def test_availability_fails_closed_for_invalid_rooms():
    availability = load_home_assistant_yaml(
        FLOOR_BLUEPRINT
    )["sensor"]["availability"]

    assert "room_entities | count > 0" in availability
    assert "invalid_rooms_value | count == 0" in availability
