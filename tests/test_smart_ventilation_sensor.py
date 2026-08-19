import pytest


def recommend_room(
    *,
    indoor_temperature: float,
    outdoor_temperature: float,
    indoor_vapor_concentration: float,
    outdoor_vapor_concentration: float,
    indoor_relative_humidity: float | None = None,
    minimum_drying_potential: float = 0.8,
    strong_drying_potential: float = 2.0,
    very_strong_drying_potential: float = 4.0,
    warmer_threshold: float = 1.0,
    much_warmer_threshold: float = 3.0,
    minimum_indoor_relative_humidity: float = 35.0,
    minimum_indoor_vapor_concentration: float = 5.5,
) -> tuple[str, str]:
    drying_potential = (
        indoor_vapor_concentration
        - outdoor_vapor_concentration
    )

    temperature_difference = (
        outdoor_temperature
        - indoor_temperature
    )

    dry_air_protection_active = (
        indoor_relative_humidity is not None
        and indoor_relative_humidity
        < minimum_indoor_relative_humidity
    )

    if indoor_relative_humidity is None:
        dry_air_protection_active = (
            indoor_vapor_concentration
            < minimum_indoor_vapor_concentration
        )

    if (
        dry_air_protection_active
        and drying_potential >= minimum_drying_potential
    ):
        return (
            "keep_closed",
            "indoor_air_already_dry",
        )

    if drying_potential <= -minimum_drying_potential:
        return (
            "keep_closed",
            "outdoor_air_more_humid",
        )

    if (
        temperature_difference
        >= much_warmer_threshold
        and drying_potential
        >= very_strong_drying_potential
    ):
        return (
            "conditional",
            "strong_drying_benefit_but_much_warmer",
        )

    if temperature_difference >= much_warmer_threshold:
        return (
            "keep_closed",
            "outdoor_air_much_warmer",
        )

    if (
        temperature_difference >= warmer_threshold
        and drying_potential >= minimum_drying_potential
    ):
        return (
            "conditional",
            "outdoor_air_drier_but_warmer",
        )

    if drying_potential >= minimum_drying_potential:
        if (
            drying_potential
            >= very_strong_drying_potential
            and outdoor_temperature < 5.0
        ):
            return (
                "ventilate",
                "outdoor_air_much_drier_and_cold",
            )

        if drying_potential >= strong_drying_potential:
            return (
                "ventilate",
                "outdoor_air_significantly_drier",
            )

        return (
            "ventilate",
            "outdoor_air_drier",
        )

    if temperature_difference >= warmer_threshold:
        return (
            "keep_closed",
            "outdoor_air_warmer_without_drying_benefit",
        )

    return (
        "neutral",
        "conditions_similar",
    )


@pytest.mark.parametrize(
    ("drying_potential", "expected_state"),
    [
        pytest.param(
            0.79,
            "neutral",
            id="minimum-drying-below-threshold",
        ),
        pytest.param(
            0.80,
            "ventilate",
            id="minimum-drying-exact-threshold",
        ),
        pytest.param(
            0.81,
            "ventilate",
            id="minimum-drying-above-threshold",
        ),
    ],
)
def test_minimum_drying_potential_boundary(
    drying_potential,
    expected_state,
):
    state, _ = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=20.0,
        indoor_vapor_concentration=10.0,
        outdoor_vapor_concentration=(
            10.0 - drying_potential
        ),
        indoor_relative_humidity=50.0,
    )

    assert state == expected_state


@pytest.mark.parametrize(
    ("temperature_difference", "expected_state"),
    [
        pytest.param(
            0.99,
            "ventilate",
            id="warmer-below-threshold",
        ),
        pytest.param(
            1.00,
            "conditional",
            id="warmer-exact-threshold",
        ),
        pytest.param(
            1.01,
            "conditional",
            id="warmer-above-threshold",
        ),
    ],
)
def test_warmer_temperature_boundary(
    temperature_difference,
    expected_state,
):
    state, _ = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=(
            22.0 + temperature_difference
        ),
        indoor_vapor_concentration=10.0,
        outdoor_vapor_concentration=9.0,
        indoor_relative_humidity=50.0,
    )

    assert state == expected_state


@pytest.mark.parametrize(
    ("temperature_difference", "expected_state"),
    [
        pytest.param(
            2.99,
            "conditional",
            id="much-warmer-below-threshold",
        ),
        pytest.param(
            3.00,
            "keep_closed",
            id="much-warmer-exact-threshold",
        ),
        pytest.param(
            3.01,
            "keep_closed",
            id="much-warmer-above-threshold",
        ),
    ],
)
def test_much_warmer_temperature_boundary(
    temperature_difference,
    expected_state,
):
    state, _ = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=(
            22.0 + temperature_difference
        ),
        indoor_vapor_concentration=10.0,
        outdoor_vapor_concentration=9.0,
        indoor_relative_humidity=50.0,
    )

    assert state == expected_state


@pytest.mark.parametrize(
    ("drying_potential", "expected_reason"),
    [
        pytest.param(
            1.99,
            "outdoor_air_drier",
            id="strong-drying-below-threshold",
        ),
        pytest.param(
            2.00,
            "outdoor_air_significantly_drier",
            id="strong-drying-exact-threshold",
        ),
        pytest.param(
            2.01,
            "outdoor_air_significantly_drier",
            id="strong-drying-above-threshold",
        ),
    ],
)
def test_strong_drying_reason_boundary(
    drying_potential,
    expected_reason,
):
    state, reason = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=15.0,
        indoor_vapor_concentration=10.0,
        outdoor_vapor_concentration=(
            10.0 - drying_potential
        ),
        indoor_relative_humidity=50.0,
    )

    assert state == "ventilate"
    assert reason == expected_reason


@pytest.mark.parametrize(
    ("drying_potential", "expected_reason"),
    [
        pytest.param(
            3.99,
            "outdoor_air_significantly_drier",
            id="very-strong-below-threshold",
        ),
        pytest.param(
            4.00,
            "outdoor_air_much_drier_and_cold",
            id="very-strong-exact-threshold",
        ),
        pytest.param(
            4.01,
            "outdoor_air_much_drier_and_cold",
            id="very-strong-above-threshold",
        ),
    ],
)
def test_very_strong_drying_reason_boundary(
    drying_potential,
    expected_reason,
):
    state, reason = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=4.0,
        indoor_vapor_concentration=10.0,
        outdoor_vapor_concentration=(
            10.0 - drying_potential
        ),
        indoor_relative_humidity=50.0,
    )

    assert state == "ventilate"
    assert reason == expected_reason


@pytest.mark.parametrize(
    ("relative_humidity", "expected_state"),
    [
        pytest.param(
            34.9,
            "keep_closed",
            id="dry-air-protection-active",
        ),
        pytest.param(
            35.0,
            "ventilate",
            id="dry-air-protection-boundary",
        ),
        pytest.param(
            35.1,
            "ventilate",
            id="dry-air-protection-inactive",
        ),
    ],
)
def test_dry_air_protection_relative_humidity(
    relative_humidity,
    expected_state,
):
    state, _ = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=18.0,
        indoor_vapor_concentration=8.0,
        outdoor_vapor_concentration=6.0,
        indoor_relative_humidity=relative_humidity,
    )

    assert state == expected_state


@pytest.mark.parametrize(
    ("indoor_vapor", "expected_state"),
    [
        pytest.param(
            5.49,
            "keep_closed",
            id="fallback-dry-air-protection-active",
        ),
        pytest.param(
            5.50,
            "ventilate",
            id="fallback-dry-air-protection-boundary",
        ),
        pytest.param(
            5.51,
            "ventilate",
            id="fallback-dry-air-protection-inactive",
        ),
    ],
)
def test_dry_air_protection_vapor_fallback(
    indoor_vapor,
    expected_state,
):
    state, _ = recommend_room(
        indoor_temperature=22.0,
        outdoor_temperature=18.0,
        indoor_vapor_concentration=indoor_vapor,
        outdoor_vapor_concentration=(
            indoor_vapor - 1.0
        ),
        indoor_relative_humidity=None,
    )

    assert state == expected_state


@pytest.mark.parametrize(
    (
        "indoor_temperature",
        "outdoor_temperature",
        "indoor_vapor",
        "outdoor_vapor",
        "expected_state",
        "expected_reason",
    ),
    [
        pytest.param(
            22.0,
            20.0,
            10.0,
            11.0,
            "keep_closed",
            "outdoor_air_more_humid",
            id="outdoor-air-more-humid",
        ),
        pytest.param(
            22.0,
            26.0,
            10.0,
            6.0,
            "conditional",
            "strong_drying_benefit_but_much_warmer",
            id="very-strong-drying-despite-heat",
        ),
        pytest.param(
            22.0,
            26.0,
            10.0,
            9.0,
            "keep_closed",
            "outdoor_air_much_warmer",
            id="much-warmer-without-strong-benefit",
        ),
        pytest.param(
            22.0,
            24.0,
            10.0,
            9.0,
            "conditional",
            "outdoor_air_drier_but_warmer",
            id="drier-but-warmer",
        ),
        pytest.param(
            22.0,
            20.0,
            10.0,
            9.0,
            "ventilate",
            "outdoor_air_drier",
            id="normal-ventilation",
        ),
        pytest.param(
            22.0,
            23.5,
            10.0,
            9.5,
            "keep_closed",
            "outdoor_air_warmer_without_drying_benefit",
            id="warmer-without-drying-benefit",
        ),
        pytest.param(
            22.0,
            22.2,
            10.0,
            9.7,
            "neutral",
            "conditions_similar",
            id="similar-conditions",
        ),
    ],
)
def test_room_truth_table(
    indoor_temperature,
    outdoor_temperature,
    indoor_vapor,
    outdoor_vapor,
    expected_state,
    expected_reason,
):
    state, reason = recommend_room(
        indoor_temperature=indoor_temperature,
        outdoor_temperature=outdoor_temperature,
        indoor_vapor_concentration=indoor_vapor,
        outdoor_vapor_concentration=outdoor_vapor,
        indoor_relative_humidity=50.0,
    )

    assert state == expected_state
    assert reason == expected_reason
