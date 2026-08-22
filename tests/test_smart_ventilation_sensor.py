import pytest

from tests.helpers import BLUEPRINT_ROOT, load_home_assistant_yaml


ROOM_BLUEPRINT = (
    BLUEPRINT_ROOT
    / "template"
    / "smart_ventilation_sensor.yaml"
)


def recommend_room(
    *,
    indoor_temperature: float,
    outdoor_temperature: float,
    indoor_vapor_concentration: float,
    outdoor_vapor_concentration: float,
    indoor_relative_humidity: float | None = None,
    minimum_drying_potential: float = 0.8,
    maximum_acceptable_negative_drying_potential: float = 2.0,
    strong_drying_potential: float = 2.0,
    very_strong_drying_potential: float = 4.0,
    warmer_threshold: float = 1.0,
    much_warmer_threshold: float = 3.0,
    minimum_indoor_relative_humidity: float = 35.0,
    minimum_indoor_vapor: float = 5.5,
) -> tuple[str, str]:
    """Reference model for the Room blueprint candidate recommendation."""
    drying = indoor_vapor_concentration - outdoor_vapor_concentration
    delta_t = outdoor_temperature - indoor_temperature

    if indoor_relative_humidity is not None:
        dry_air = (
            indoor_relative_humidity
            < minimum_indoor_relative_humidity
        )
    else:
        dry_air = indoor_vapor_concentration < minimum_indoor_vapor

    if dry_air and drying >= minimum_drying_potential:
        return "keep_closed", "indoor_air_already_dry"

    if drying <= -maximum_acceptable_negative_drying_potential:
        return "keep_closed", "outdoor_air_more_humid"

    if (
        delta_t >= much_warmer_threshold
        and drying >= very_strong_drying_potential
    ):
        return "conditional", "strong_drying_benefit_but_much_warmer"

    if delta_t >= much_warmer_threshold:
        return "keep_closed", "outdoor_air_much_warmer"

    if (
        drying >= minimum_drying_potential
        and delta_t >= warmer_threshold
    ):
        return "conditional", "outdoor_air_drier_but_warmer"

    if drying >= minimum_drying_potential:
        if (
            drying >= very_strong_drying_potential
            and outdoor_temperature < 5
        ):
            return "ventilate", "outdoor_air_much_drier_and_cold"

        if drying >= strong_drying_potential:
            return "ventilate", "outdoor_air_significantly_drier"

        return "ventilate", "outdoor_air_drier"

    if delta_t >= warmer_threshold:
        return "keep_closed", "outdoor_air_warmer_without_drying_benefit"

    return "neutral", "conditions_similar"


def configuration_errors(
    *,
    minimum_drying: float = 0.8,
    strong_drying: float = 2.0,
    very_strong_drying: float = 4.0,
    warmer: float = 1.0,
    much_warmer: float = 3.0,
    minimum_duration: float = 2.0,
    maximum_duration: float = 30.0,
) -> list[str]:
    errors = []

    if minimum_drying > strong_drying:
        errors.append("minimum_drying_exceeds_strong_drying")

    if strong_drying > very_strong_drying:
        errors.append("strong_drying_exceeds_very_strong_drying")

    if warmer > much_warmer:
        errors.append("warmer_threshold_exceeds_much_warmer_threshold")

    if minimum_duration > maximum_duration:
        errors.append("minimum_duration_exceeds_maximum_duration")

    return errors


def test_blueprint_contract_and_api_version():
    document = load_home_assistant_yaml(ROOM_BLUEPRINT)

    assert document["blueprint"]["domain"] == "template"
    assert (
        str(document["blueprint"]["homeassistant"]["min_version"])
        == "2024.11.0"
    )
    assert document["sensor"]["attributes"]["api_version"] == "1"


def test_source_url_stays_on_dev():
    metadata = load_home_assistant_yaml(ROOM_BLUEPRINT)["blueprint"]

    assert "/blob/dev/" in metadata["source_url"]


def test_public_duration_is_minutes_only():
    document = load_home_assistant_yaml(ROOM_BLUEPRINT)
    attributes = document["sensor"]["attributes"]
    source = ROOM_BLUEPRINT.read_text(encoding="utf-8")

    assert "recommended_duration_minutes" in attributes
    assert "recommended_duration_seconds" not in attributes
    assert "recommended_duration_seconds_value" not in source


def test_configuration_diagnostics_are_public():
    attributes = load_home_assistant_yaml(
        ROOM_BLUEPRINT
    )["sensor"]["attributes"]

    assert "configuration_valid" in attributes
    assert "configuration_errors" in attributes


def test_keep_closed_stability_diagnostics_are_public():
    document = load_home_assistant_yaml(ROOM_BLUEPRINT)
    inputs = document["blueprint"]["input"]["thresholds"]["input"]
    attributes = document["sensor"]["attributes"]

    assert inputs[
        "maximum_acceptable_negative_drying_potential"
    ]["default"] == 2.0
    assert inputs["keep_closed_confirmation_minutes"]["default"] == 15
    assert {
        "candidate_recommendation",
        "candidate_reason",
        "keep_closed_pending",
        "keep_closed_pending_since",
        "keep_closed_confirmation_minutes",
        "maximum_acceptable_negative_drying_potential",
    } <= attributes.keys()


def test_optional_humidity_reconciliation_is_one_minute():
    document = load_home_assistant_yaml(ROOM_BLUEPRINT)

    trigger = next(
        item
        for item in document["triggers"]
        if item.get("id") == "reconcile"
    )

    assert trigger["trigger"] == "time_pattern"
    assert trigger["minutes"] == "/1"


@pytest.mark.parametrize(
    ("kwargs", "expected_state", "expected_reason"),
    [
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=15.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=9.2,
            ),
            "ventilate",
            "outdoor_air_drier",
            id="minimum-drying-threshold",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=15.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=8.0,
            ),
            "ventilate",
            "outdoor_air_significantly_drier",
            id="strong-drying-threshold",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=4.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=6.0,
            ),
            "ventilate",
            "outdoor_air_much_drier_and_cold",
            id="very-strong-drying-cold",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=23.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=9.2,
            ),
            "conditional",
            "outdoor_air_drier_but_warmer",
            id="warmer-at-threshold-with-useful-drying",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=25.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=6.0,
            ),
            "conditional",
            "strong_drying_benefit_but_much_warmer",
            id="much-warmer-but-very-strong-drying",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=25.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=8.0,
            ),
            "keep_closed",
            "outdoor_air_much_warmer",
            id="much-warmer-without-very-strong-drying",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=23.0,
                indoor_vapor_concentration=10.0,
                outdoor_vapor_concentration=9.5,
            ),
            "keep_closed",
            "outdoor_air_warmer_without_drying_benefit",
            id="warmer-without-useful-drying",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=20.0,
                indoor_vapor_concentration=8.0,
                outdoor_vapor_concentration=8.8,
            ),
            "neutral",
            "conditions_similar",
            id="small-moisture-disadvantage-remains-neutral",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=20.0,
                indoor_vapor_concentration=8.0,
                outdoor_vapor_concentration=10.0,
            ),
            "keep_closed",
            "outdoor_air_more_humid",
            id="outside-wetter-at-close-threshold",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=21.0,
                indoor_vapor_concentration=8.0,
                outdoor_vapor_concentration=7.5,
            ),
            "neutral",
            "conditions_similar",
            id="small-drying-benefit-below-threshold",
        ),
        pytest.param(
            dict(
                indoor_temperature=22.0,
                outdoor_temperature=22.0,
                indoor_vapor_concentration=8.0,
                outdoor_vapor_concentration=8.0,
            ),
            "neutral",
            "conditions_similar",
            id="identical-conditions",
        ),
    ],
)
def test_recommendation_regression_matrix(
    kwargs,
    expected_state,
    expected_reason,
):
    assert recommend_room(**kwargs) == (
        expected_state,
        expected_reason,
    )


@pytest.mark.parametrize(
    ("relative_humidity", "indoor_vapor", "expected"),
    [
        pytest.param(
            34.0,
            8.0,
            ("keep_closed", "indoor_air_already_dry"),
            id="rh-below-threshold",
        ),
        pytest.param(
            35.0,
            8.0,
            ("ventilate", "outdoor_air_significantly_drier"),
            id="rh-exactly-threshold-not-protected",
        ),
        pytest.param(
            None,
            5.4,
            ("keep_closed", "indoor_air_already_dry"),
            id="absolute-vapor-fallback-below-threshold",
        ),
        pytest.param(
            None,
            5.5,
            ("ventilate", "outdoor_air_significantly_drier"),
            id="absolute-vapor-exact-threshold-not-protected",
        ),
    ],
)
def test_dry_air_protection_regression(
    relative_humidity,
    indoor_vapor,
    expected,
):
    result = recommend_room(
        indoor_temperature=21.0,
        outdoor_temperature=10.0,
        indoor_vapor_concentration=indoor_vapor,
        outdoor_vapor_concentration=3.0,
        indoor_relative_humidity=relative_humidity,
    )

    assert result == expected


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param(
            dict(minimum_drying=2.1, strong_drying=2.0),
            ["minimum_drying_exceeds_strong_drying"],
            id="minimum-greater-than-strong",
        ),
        pytest.param(
            dict(strong_drying=4.1, very_strong_drying=4.0),
            ["strong_drying_exceeds_very_strong_drying"],
            id="strong-greater-than-very-strong",
        ),
        pytest.param(
            dict(warmer=3.1, much_warmer=3.0),
            ["warmer_threshold_exceeds_much_warmer_threshold"],
            id="warmer-greater-than-much-warmer",
        ),
        pytest.param(
            dict(minimum_duration=31.0, maximum_duration=30.0),
            ["minimum_duration_exceeds_maximum_duration"],
            id="minimum-duration-greater-than-maximum",
        ),
    ],
)
def test_invalid_configuration_regressions(kwargs, expected):
    assert configuration_errors(**kwargs) == expected


def test_equal_threshold_boundaries_are_valid():
    assert configuration_errors(
        minimum_drying=2.0,
        strong_drying=2.0,
        very_strong_drying=2.0,
        warmer=3.0,
        much_warmer=3.0,
        minimum_duration=10.0,
        maximum_duration=10.0,
    ) == []


def test_multiple_configuration_errors_are_reported_together():
    assert set(
        configuration_errors(
            minimum_drying=5.0,
            strong_drying=4.0,
            very_strong_drying=3.0,
            warmer=5.0,
            much_warmer=2.0,
            minimum_duration=40.0,
            maximum_duration=30.0,
        )
    ) == {
        "minimum_drying_exceeds_strong_drying",
        "strong_drying_exceeds_very_strong_drying",
        "warmer_threshold_exceeds_much_warmer_threshold",
        "minimum_duration_exceeds_maximum_duration",
    }


def test_availability_contains_required_sensor_and_config_checks():
    availability = load_home_assistant_yaml(
        ROOM_BLUEPRINT
    )["sensor"]["availability"]

    assert "required_sensors_valid" in availability
    assert "configuration_valid" in availability


def test_keep_closed_confirmation_uses_restored_state_and_pending_timestamp():
    source = ROOM_BLUEPRINT.read_text(encoding="utf-8")

    assert "this.attributes.get('candidate_recommendation', '')" in source
    assert "this.attributes.get('keep_closed_pending_since', none)" in source
    assert "keep_closed_confirmation_minutes_value | float * 60" in source
    assert "this.state == 'keep_closed'" in source


def test_pending_close_is_neutral_and_non_close_candidates_publish_immediately():
    source = ROOM_BLUEPRINT.read_text(encoding="utf-8")

    assert "candidate_recommendation == 'keep_closed'" in source
    assert "and keep_closed_confirmation_elapsed | bool" in source
    assert "elif candidate_recommendation == 'keep_closed'" in source
    assert "{{ candidate_recommendation }}" in source
    assert "keep_closed_pending" in source
