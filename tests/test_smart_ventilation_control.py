import pytest

from tests.helpers import BLUEPRINT_ROOT, load_home_assistant_yaml


CONTROL_BLUEPRINT = (
    BLUEPRINT_ROOT
    / "automation"
    / "smart_ventilation_control.yaml"
)


def control_state(
    *,
    floor_state: str,
    opening_states: list[str],
    closing_states: list[str] | None = None,
    floor_api_version: str = "2",
    closing_subset_valid: bool = True,
) -> str:
    closing_states = (
        opening_states
        if closing_states is None
        else closing_states
    )

    valid = (
        len(opening_states) > 0
        and floor_state in {
            "ventilate",
            "conditional",
            "keep_closed",
            "neutral",
        }
        and floor_api_version == "2"
        and closing_subset_valid
        and all(
            state in {"on", "off"}
            for state in opening_states
        )
    )

    if not valid:
        return "unavailable"

    if floor_state == "ventilate":
        return "ok" if "on" in opening_states else "open"

    if floor_state == "keep_closed":
        return "close" if "on" in closing_states else "ok"

    if floor_state == "conditional":
        return "conditional"

    return "neutral"


def test_control_blueprint_exists():
    assert CONTROL_BLUEPRINT.exists()


def test_control_blueprint_is_automation_blueprint():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    assert document["blueprint"]["domain"] == "automation"
    assert "triggers" in document
    assert "actions" in document
    assert "sensor" not in document


def test_control_blueprint_source_url_matches_location():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]

    assert metadata["source_url"] == (
        "https://github.com/rudnerbjoern/ha-blueprints/"
        "blob/main/blueprints/automation/"
        "smart_ventilation_control.yaml"
    )


def test_control_blueprint_required_inputs():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    inputs = metadata["input"]

    floor_input = inputs["recommendation"]["input"]["floor_sensor"]
    opening_input = inputs["windows"]["input"]["opening_windows"]

    assert "default" not in floor_input
    assert "default" not in opening_input


def test_control_blueprint_closing_windows_default_empty():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    closing_input = (
        metadata["input"]["windows"]["input"]["closing_windows"]
    )

    assert closing_input["default"] == []


@pytest.mark.parametrize(
    "action_input",
    [
        "open_actions",
        "close_actions",
        "clear_actions",
        "unavailable_actions",
    ],
)
def test_control_action_inputs_are_optional(action_input):
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    actions = metadata["input"]["actions_section"]["input"]

    assert actions[action_input]["default"] == []


def test_control_blueprint_uses_derived_transition_triggers():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    trigger_ids = {
        trigger["id"]
        for trigger in document["triggers"]
    }

    assert trigger_ids == {
        "open",
        "close",
        "ok",
        "conditional",
        "neutral",
        "unavailable",
    }

    assert all(
        trigger["trigger"] == "template"
        for trigger in document["triggers"]
    )


def test_control_blueprint_is_restart_mode():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    assert document["mode"] == "restart"
    assert document["max_exceeded"] == "silent"


@pytest.mark.parametrize(
    ("floor_state", "opening_states", "expected"),
    [
        ("ventilate", ["off"], "open"),
        ("ventilate", ["off", "off"], "open"),
        ("ventilate", ["on"], "ok"),
        ("ventilate", ["off", "on"], "ok"),
        ("keep_closed", ["off"], "ok"),
        ("keep_closed", ["on"], "close"),
        ("conditional", ["off"], "conditional"),
        ("neutral", ["off"], "neutral"),
    ],
)
def test_control_truth_table(
    floor_state,
    opening_states,
    expected,
):
    assert control_state(
        floor_state=floor_state,
        opening_states=opening_states,
    ) == expected


def test_control_uses_explicit_closing_subset():
    assert control_state(
        floor_state="keep_closed",
        opening_states=["off", "on"],
        closing_states=["off"],
    ) == "ok"


def test_control_close_when_explicit_closing_window_open():
    assert control_state(
        floor_state="keep_closed",
        opening_states=["off", "on"],
        closing_states=["on"],
    ) == "close"


def test_control_unavailable_with_empty_opening_list():
    assert control_state(
        floor_state="ventilate",
        opening_states=[],
    ) == "unavailable"


@pytest.mark.parametrize(
    "floor_state",
    ["unknown", "unavailable", "invalid"],
)
def test_control_unavailable_with_invalid_floor_state(floor_state):
    assert control_state(
        floor_state=floor_state,
        opening_states=["off"],
    ) == "unavailable"


@pytest.mark.parametrize(
    "window_state",
    ["unknown", "unavailable", "invalid"],
)
def test_control_unavailable_with_invalid_window_state(window_state):
    assert control_state(
        floor_state="ventilate",
        opening_states=[window_state],
    ) == "unavailable"


def test_control_unavailable_with_wrong_floor_api():
    assert control_state(
        floor_state="ventilate",
        opening_states=["off"],
        floor_api_version="1",
    ) == "unavailable"


def test_control_unavailable_with_invalid_closing_subset():
    assert control_state(
        floor_state="keep_closed",
        opening_states=["off"],
        closing_states=["off"],
        closing_subset_valid=False,
    ) == "unavailable"


def test_eg_terrace_door_does_not_create_close_warning():
    assert control_state(
        floor_state="keep_closed",
        opening_states=["off", "on", "off", "off"],
        closing_states=["off", "off", "off"],
    ) == "ok"


def test_eg_terrace_door_satisfies_ventilation():
    assert control_state(
        floor_state="ventilate",
        opening_states=["off", "on", "off", "off"],
        closing_states=["off", "off", "off"],
    ) == "ok"
