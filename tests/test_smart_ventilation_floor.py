import pytest

from tests.helpers import TEMPLATE_BLUEPRINT_ROOT

FLOOR_BLUEPRINT = (
    TEMPLATE_BLUEPRINT_ROOT
    / "smart_ventilation_floor.yaml"
)


def aggregate_floor(
    *,
    ventilate: int,
    conditional: int,
    keep_closed: int,
    neutral: int,
    average_temperature_difference: float,
    thermal_override_threshold: float = 1.0,
) -> str:
    """Reference implementation of floor aggregation semantics."""

    thermal_override = (
        ventilate == 0
        and conditional > 0
        and keep_closed > 0
        and average_temperature_difference
        >= thermal_override_threshold
    )

    if ventilate > 0 and keep_closed > 0:
        return "conditional"

    if thermal_override:
        return "keep_closed"

    if conditional > 0:
        return "conditional"

    if ventilate > 0:
        return "ventilate"

    if keep_closed > 0:
        return "keep_closed"

    return "neutral"


@pytest.mark.parametrize(
    (
        "ventilate",
        "conditional",
        "keep_closed",
        "neutral",
        "temperature_difference",
        "expected",
    ),
    [
        pytest.param(
            0, 0, 0, 3, 0.0, "neutral",
            id="all-neutral",
        ),
        pytest.param(
            2, 0, 0, 1, -2.0, "ventilate",
            id="ventilate-only",
        ),
        pytest.param(
            0, 0, 2, 1, 2.0, "keep_closed",
            id="keep-closed-only",
        ),
        pytest.param(
            0, 2, 0, 1, 2.0, "conditional",
            id="conditional-only",
        ),
        pytest.param(
            1, 0, 1, 1, 0.0, "conditional",
            id="ventilate-conflicts-with-keep-closed",
        ),
        pytest.param(
            0, 1, 2, 0, 2.1, "keep_closed",
            id="thermal-override",
        ),
        pytest.param(
            0, 1, 2, 0, 0.5, "conditional",
            id="thermal-override-below-threshold",
        ),
        pytest.param(
            1, 1, 0, 1, 1.5, "conditional",
            id="ventilate-plus-conditional",
        ),
        pytest.param(
            1, 1, 1, 0, 2.0, "conditional",
            id="direct-conflict-dominates-thermal-override",
        ),
    ],
)
def test_floor_aggregation(
    ventilate,
    conditional,
    keep_closed,
    neutral,
    temperature_difference,
    expected,
):
    assert (
        aggregate_floor(
            ventilate=ventilate,
            conditional=conditional,
            keep_closed=keep_closed,
            neutral=neutral,
            average_temperature_difference=(
                temperature_difference
            ),
        )
        == expected
    )


@pytest.mark.parametrize(
    ("difference", "expected"),
    [
        pytest.param(
            0.99,
            "conditional",
            id="below-threshold",
        ),
        pytest.param(
            1.00,
            "keep_closed",
            id="exact-threshold",
        ),
        pytest.param(
            1.01,
            "keep_closed",
            id="above-threshold",
        ),
    ],
)
def test_thermal_override_boundary(
    difference,
    expected,
):
    assert (
        aggregate_floor(
            ventilate=0,
            conditional=1,
            keep_closed=1,
            neutral=0,
            average_temperature_difference=difference,
        )
        == expected
    )


def test_floor_blueprint_api_version(
    load_blueprint,
):
    document = load_blueprint(FLOOR_BLUEPRINT)

    attributes = document["sensor"]["attributes"]

    assert attributes["api_version"] == "2"


def test_floor_requires_room_api_version_one(
    load_blueprint,
):
    document = load_blueprint(FLOOR_BLUEPRINT)

    attributes = document["sensor"]["attributes"]

    assert attributes["room_api_version_required"] == "1"


@pytest.mark.parametrize(
    "attribute",
    [
        "reason",
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
        "average_temperature_difference",
        "maximum_drying_potential",
        "outside_warmer_than_floor",
        "outside_warmer_than_all_rooms",
        "thermal_override_active",
    ],
)
def test_floor_api_contains_expected_attribute(
    attribute,
    load_blueprint,
):
    document = load_blueprint(FLOOR_BLUEPRINT)

    assert attribute in document["sensor"]["attributes"]
