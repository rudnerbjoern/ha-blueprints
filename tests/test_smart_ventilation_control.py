import pytest

from tests.helpers import BLUEPRINT_ROOT, load_home_assistant_yaml


CONTROL_BLUEPRINT = (
    BLUEPRINT_ROOT
    / "automation"
    / "smart_ventilation_control.yaml"
)


def input_reference_name(value):
    if not isinstance(value, dict):
        return None

    if value.get("__ha_tag__") == "!input":
        return value.get("value")

    return value.get("__input__")


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


def get_choose_action(document):
    return next(
        action
        for action in document["actions"]
        if "choose" in action
    )


def get_choose_branch(document, trigger_id):
    choose_action = get_choose_action(document)

    for branch in choose_action["choose"]:
        conditions = branch["conditions"]
        trigger_conditions = [
            condition
            for condition in conditions
            if condition.get("condition") == "trigger"
        ]
        if trigger_conditions and trigger_conditions[0]["id"] == trigger_id:
            return branch

    raise AssertionError(
        f"No choose branch found for trigger id {trigger_id!r}"
    )


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


def test_control_blueprint_minimum_home_assistant_version():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]

    assert str(metadata["homeassistant"]["min_version"]) == "2024.11.0"


def test_control_blueprint_required_inputs():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    inputs = metadata["input"]

    floor_input = inputs["recommendation"]["input"]["floor_sensor"]
    opening_input = inputs["windows"]["input"]["opening_windows"]

    assert "default" not in floor_input
    assert "default" not in opening_input


def test_control_blueprint_closing_windows_default_empty():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    closing_input = metadata["input"]["windows"]["input"]["closing_windows"]

    assert closing_input["default"] == []


def test_control_timing_defaults_preserve_legacy_behavior():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    timing = metadata["input"]["timing"]["input"]

    assert timing["demand_delay_seconds"]["default"] == 120
    assert timing["window_update_delay_seconds"]["default"] == 1
    assert timing["active_after"]["default"] == "07:00:00"
    assert timing["active_before"]["default"] == "23:00:00"


@pytest.mark.parametrize(
    "action_input",
    [
        "open_actions",
        "close_actions",
        "clear_actions",
        "unavailable_actions",
        "window_update_actions",
    ],
)
def test_control_action_inputs_are_optional(action_input):
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    actions = metadata["input"]["actions_section"]["input"]

    assert actions[action_input]["default"] == []


def test_control_blueprint_uses_expected_triggers():
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
        "window_change",
    }


def test_control_semantic_triggers_are_templates():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    semantic_triggers = [
        trigger
        for trigger in document["triggers"]
        if trigger["id"] != "window_change"
    ]

    assert all(
        trigger["trigger"] == "template"
        for trigger in semantic_triggers
    )


def test_control_window_change_trigger_is_native_state_trigger():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    window_trigger = next(
        trigger
        for trigger in document["triggers"]
        if trigger["id"] == "window_change"
    )

    assert window_trigger["trigger"] == "state"
    assert input_reference_name(window_trigger["entity_id"]) == "opening_windows"


def test_open_and_close_triggers_have_stability_delay():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    demand_triggers = {
        trigger["id"]: trigger
        for trigger in document["triggers"]
        if trigger["id"] in {"open", "close"}
    }

    assert set(demand_triggers) == {"open", "close"}

    for trigger in demand_triggers.values():
        assert "for" in trigger
        assert (
            input_reference_name(trigger["for"]["seconds"])
            == "demand_delay_seconds"
        )


def test_control_window_update_delay_uses_input():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    first_action = document["actions"][0]

    assert first_action["if"] == [
        {
            "condition": "trigger",
            "id": "window_change",
        }
    ]

    delay_action = first_action["then"][0]

    assert (
        input_reference_name(delay_action["delay"]["seconds"])
        == "window_update_delay_seconds"
    )


def test_open_branch_is_time_gated():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    branch = get_choose_branch(document, "open")

    time_condition = next(
        condition
        for condition in branch["conditions"]
        if condition.get("condition") == "time"
    )

    assert input_reference_name(time_condition["after"]) == "active_after"
    assert input_reference_name(time_condition["before"]) == "active_before"
    assert input_reference_name(branch["sequence"]) == "open_actions"


def test_close_branch_is_time_gated():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    branch = get_choose_branch(document, "close")

    time_condition = next(
        condition
        for condition in branch["conditions"]
        if condition.get("condition") == "time"
    )

    assert input_reference_name(time_condition["after"]) == "active_after"
    assert input_reference_name(time_condition["before"]) == "active_before"
    assert input_reference_name(branch["sequence"]) == "close_actions"


@pytest.mark.parametrize(
    ("trigger_id", "action_input"),
    [
        ("unavailable", "unavailable_actions"),
        ("window_change", "window_update_actions"),
    ],
)
def test_single_trigger_action_branches_are_dispatched(
    trigger_id,
    action_input,
):
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    branch = get_choose_branch(document, trigger_id)

    assert input_reference_name(branch["sequence"]) == action_input


def test_clear_actions_handle_non_demand_states():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    branch = get_choose_branch(
        document,
        ["ok", "conditional", "neutral"],
    )

    assert input_reference_name(branch["sequence"]) == "clear_actions"
    assert not any(
        condition.get("condition") == "time"
        for condition in branch["conditions"]
    )


def test_unavailable_and_window_updates_are_not_time_gated():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    for trigger_id in ("unavailable", "window_change"):
        branch = get_choose_branch(document, trigger_id)

        assert not any(
            condition.get("condition") == "time"
            for condition in branch["conditions"]
        )


def test_control_blueprint_preserves_restart_mode():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    assert document["mode"] == "restart"
    assert document["max_exceeded"] == "silent"


def test_control_recomputes_state_for_window_changes():
    source = CONTROL_BLUEPRINT.read_text(encoding="utf-8")

    assert "control_state:" in source
    assert "floor_state == 'ventilate'" in source
    assert "floor_state == 'keep_closed'" in source
    assert 'control_state: "{{ trigger.id }}"' not in source


def test_control_exposes_expected_runtime_variables():
    source = CONTROL_BLUEPRINT.read_text(encoding="utf-8")

    expected_variables = {
        "control_state:",
        "floor_state:",
        "floor_reason:",
        "invalid_closing_windows:",
        "invalid_windows:",
        "open_opening_windows:",
        "closed_opening_windows:",
        "open_closing_windows:",
        "windows_to_open:",
        "windows_to_close:",
        "windows_to_open_names:",
        "windows_to_close_names:",
    }

    for variable in expected_variables:
        assert variable in source


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
    [
        "unknown",
        "unavailable",
        "invalid",
    ],
)
def test_control_unavailable_with_invalid_floor_state(
    floor_state,
):
    assert control_state(
        floor_state=floor_state,
        opening_states=["off"],
    ) == "unavailable"


@pytest.mark.parametrize(
    "window_state",
    [
        "unknown",
        "unavailable",
        "invalid",
    ],
)
def test_control_unavailable_with_invalid_window_state(
    window_state,
):
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
        opening_states=[
            "off",
            "on",
            "off",
            "off",
        ],
        closing_states=[
            "off",
            "off",
            "off",
        ],
    ) == "ok"


def test_eg_terrace_door_satisfies_ventilation():
    assert control_state(
        floor_state="ventilate",
        opening_states=[
            "off",
            "on",
            "off",
            "off",
        ],
        closing_states=[
            "off",
            "off",
            "off",
        ],
    ) == "ok"
