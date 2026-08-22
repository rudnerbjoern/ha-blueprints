import re

import pytest

from tests.helpers import BLUEPRINT_ROOT, load_home_assistant_yaml


CONTROL_BLUEPRINT = (
    BLUEPRINT_ROOT
    / "automation"
    / "smart_ventilation_control.yaml"
)


def input_reference_name(value):
    """Return the !input name from the HA-aware YAML test loader."""
    if not isinstance(value, dict):
        return None

    if value.get("__ha_tag__") == "!input":
        return value.get("value")

    return value.get("__input__")


def derive_control_state(
    *,
    floor_state: str,
    opening_states: list[str],
    closing_indices: list[int] | None = None,
    floor_api_version: str = "2",
    closing_subset_valid: bool = True,
) -> tuple[str, list[int], list[int]]:
    """Reference model for Smart Ventilation Control semantics."""
    if closing_indices is None:
        closing_indices = list(range(len(opening_states)))

    valid_floor_states = {
        "ventilate",
        "conditional",
        "keep_closed",
        "neutral",
    }

    valid = (
        len(opening_states) > 0
        and floor_state in valid_floor_states
        and floor_api_version == "2"
        and closing_subset_valid
        and all(state in {"on", "off"} for state in opening_states)
        and all(
            0 <= index < len(opening_states)
            for index in closing_indices
        )
    )

    if not valid:
        return "unavailable", [], []

    open_opening = [
        index
        for index, state in enumerate(opening_states)
        if state == "on"
    ]
    closed_opening = [
        index
        for index, state in enumerate(opening_states)
        if state == "off"
    ]
    open_closing = [
        index
        for index in closing_indices
        if opening_states[index] == "on"
    ]

    if floor_state == "ventilate":
        state = "ok" if open_opening else "open"
    elif floor_state == "keep_closed":
        state = "close" if open_closing else "ok"
    elif floor_state == "conditional":
        state = "conditional"
    else:
        state = "neutral"

    windows_to_open = closed_opening if state == "open" else []
    windows_to_close = open_closing if state == "close" else []

    return state, windows_to_open, windows_to_close


def get_trigger(document, trigger_id):
    return next(
        trigger
        for trigger in document["triggers"]
        if trigger.get("id") == trigger_id
    )


def get_choose(document):
    return next(
        action["choose"]
        for action in document["actions"]
        if "choose" in action
    )


def branches_for_trigger(document, trigger_id):
    result = []

    for branch in get_choose(document):
        for condition in branch["conditions"]:
            if (
                condition.get("condition") == "trigger"
                and condition.get("id") == trigger_id
            ):
                result.append(branch)

    return result


def test_blueprint_contract():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    assert document["blueprint"]["domain"] == "automation"
    assert (
        str(document["blueprint"]["homeassistant"]["min_version"])
        == "2024.11.0"
    )
    assert document["mode"] == "restart"
    assert document["max_exceeded"] == "silent"
    assert "sensor" not in document


def test_source_url_stays_on_main():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]

    assert "/blob/main/" in metadata["source_url"]


def test_required_and_optional_inputs():
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    inputs = metadata["input"]

    assert (
        "default"
        not in inputs["recommendation"]["input"]["floor_sensor"]
    )
    assert (
        "default"
        not in inputs["windows"]["input"]["opening_windows"]
    )
    assert (
        inputs["windows"]["input"]["closing_windows"]["default"]
        == []
    )


def test_timing_defaults():
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
def test_all_action_inputs_are_optional(action_input):
    metadata = load_home_assistant_yaml(CONTROL_BLUEPRINT)["blueprint"]
    inputs = metadata["input"]["actions_section"]["input"]

    assert inputs[action_input]["default"] == []


def test_trigger_set_is_complete():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    assert {
        trigger["id"]
        for trigger in document["triggers"]
    } == {
        "open",
        "close",
        "ok",
        "conditional",
        "neutral",
        "unavailable",
        "window_change",
        "active_start",
    }


@pytest.mark.parametrize(
    "trigger_id",
    [
        "open",
        "close",
        "ok",
        "conditional",
        "neutral",
        "unavailable",
    ],
)
def test_semantic_state_triggers_are_templates(trigger_id):
    trigger = get_trigger(
        load_home_assistant_yaml(CONTROL_BLUEPRINT),
        trigger_id,
    )

    assert trigger["trigger"] == "template"


def test_window_change_is_native_state_trigger():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    trigger = get_trigger(document, "window_change")

    assert trigger["trigger"] == "state"
    assert (
        input_reference_name(trigger["entity_id"])
        == "opening_windows"
    )


def test_active_start_is_native_time_trigger():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    trigger = get_trigger(document, "active_start")

    assert trigger["trigger"] == "time"
    assert input_reference_name(trigger["at"]) == "active_after"


@pytest.mark.parametrize("trigger_id", ["open", "close"])
def test_open_close_triggers_use_demand_stability_delay(trigger_id):
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    trigger = get_trigger(document, trigger_id)

    assert (
        input_reference_name(trigger["for"]["seconds"])
        == "demand_delay_seconds"
    )


def test_active_start_waits_demand_delay_before_recompute():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    delay_index = next(
        index
        for index, action in enumerate(document["actions"])
        if action.get("if") == [
            {
                "condition": "trigger",
                "id": "active_start",
            }
        ]
    )

    control_state_index = next(
        index
        for index, action in enumerate(document["actions"])
        if "control_state" in action.get("variables", {})
    )

    delay = document["actions"][delay_index]["then"][0]["delay"]

    assert (
        input_reference_name(delay["seconds"])
        == "demand_delay_seconds"
    )
    assert delay_index < control_state_index


def test_window_change_uses_settle_delay_before_recompute():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    delay_index = next(
        index
        for index, action in enumerate(document["actions"])
        if action.get("if") == [
            {
                "condition": "trigger",
                "id": "window_change",
            }
        ]
    )

    control_state_index = next(
        index
        for index, action in enumerate(document["actions"])
        if "control_state" in action.get("variables", {})
    )

    delay = document["actions"][delay_index]["then"][0]["delay"]

    assert (
        input_reference_name(delay["seconds"])
        == "window_update_delay_seconds"
    )
    assert delay_index < control_state_index


def test_closing_fallback_is_not_templated_in_trigger_variables():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    trigger_variables = document["trigger_variables"]

    assert "closing_entities" not in trigger_variables


def test_closing_fallback_is_calculated_in_action_context():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    variables = next(
        action["variables"]
        for action in document["actions"]
        if "closing_entities" in action.get("variables", {})
    )

    assert "closing_entities" in variables


def test_regular_open_and_close_dispatch_remain_time_gated():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    for trigger_id, action_input in (
        ("open", "open_actions"),
        ("close", "close_actions"),
    ):
        branches = branches_for_trigger(document, trigger_id)

        assert len(branches) == 1

        branch = branches[0]
        time_condition = next(
            condition
            for condition in branch["conditions"]
            if condition.get("condition") == "time"
        )

        assert (
            input_reference_name(time_condition["after"])
            == "active_after"
        )
        assert (
            input_reference_name(time_condition["before"])
            == "active_before"
        )
        assert (
            input_reference_name(branch["sequence"])
            == action_input
        )


def test_active_start_dispatches_only_current_open_or_close_demand():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    branches = branches_for_trigger(document, "active_start")

    assert len(branches) == 2

    assert {
        input_reference_name(branch["sequence"])
        for branch in branches
    } == {
        "open_actions",
        "close_actions",
    }

    assert {
        condition["value_template"]
        for branch in branches
        for condition in branch["conditions"]
        if condition.get("condition") == "template"
    } == {
        "{{ control_state == 'open' }}",
        "{{ control_state == 'close' }}",
    }


@pytest.mark.parametrize(
    (
        "floor_state",
        "opening_states",
        "closing_indices",
        "expected_state",
        "expected_open",
        "expected_close",
    ),
    [
        pytest.param(
            "ventilate",
            ["off"],
            None,
            "open",
            [0],
            [],
            id="ventilate-single-closed-opening",
        ),
        pytest.param(
            "ventilate",
            ["off", "off", "off"],
            None,
            "open",
            [0, 1, 2],
            [],
            id="ventilate-all-openings-closed",
        ),
        pytest.param(
            "ventilate",
            ["on", "off"],
            None,
            "ok",
            [],
            [],
            id="ventilate-one-opening-already-open",
        ),
        pytest.param(
            "keep_closed",
            ["off", "off"],
            None,
            "ok",
            [],
            [],
            id="keep-closed-all-closed",
        ),
        pytest.param(
            "keep_closed",
            ["on", "off"],
            None,
            "close",
            [],
            [0],
            id="keep-closed-one-warning-opening-open",
        ),
        pytest.param(
            "conditional",
            ["off"],
            None,
            "conditional",
            [],
            [],
            id="conditional-independent-of-window-state",
        ),
        pytest.param(
            "neutral",
            ["on"],
            None,
            "neutral",
            [],
            [],
            id="neutral-independent-of-window-state",
        ),
    ],
)
def test_control_state_regression_matrix(
    floor_state,
    opening_states,
    closing_indices,
    expected_state,
    expected_open,
    expected_close,
):
    assert derive_control_state(
        floor_state=floor_state,
        opening_states=opening_states,
        closing_indices=closing_indices,
    ) == (
        expected_state,
        expected_open,
        expected_close,
    )


@pytest.mark.parametrize(
    (
        "floor_state",
        "opening_states",
        "closing_indices",
        "expected_state",
        "expected_close",
    ),
    [
        pytest.param(
            "keep_closed",
            ["off", "on", "off", "off"],
            [0, 2, 3],
            "ok",
            [],
            id="terrace-door-excluded-from-close-warning",
        ),
        pytest.param(
            "keep_closed",
            ["on", "on", "off", "off"],
            [0, 2, 3],
            "close",
            [0],
            id="terrace-door-open-plus-real-close-window",
        ),
        pytest.param(
            "ventilate",
            ["off", "on", "off", "off"],
            [0, 2, 3],
            "ok",
            [],
            id="terrace-door-still-satisfies-ventilation",
        ),
    ],
)
def test_explicit_closing_subset_regressions(
    floor_state,
    opening_states,
    closing_indices,
    expected_state,
    expected_close,
):
    state, _, windows_to_close = derive_control_state(
        floor_state=floor_state,
        opening_states=opening_states,
        closing_indices=closing_indices,
    )

    assert state == expected_state
    assert windows_to_close == expected_close


@pytest.mark.parametrize(
    (
        "floor_state",
        "opening_states",
        "floor_api_version",
        "closing_subset_valid",
    ),
    [
        pytest.param(
            "ventilate",
            [],
            "2",
            True,
            id="empty-opening-list",
        ),
        pytest.param(
            "unknown",
            ["off"],
            "2",
            True,
            id="unsupported-floor-state",
        ),
        pytest.param(
            "unavailable",
            ["off"],
            "2",
            True,
            id="unavailable-floor-state",
        ),
        pytest.param(
            "ventilate",
            ["unknown"],
            "2",
            True,
            id="unknown-window-state",
        ),
        pytest.param(
            "ventilate",
            ["unavailable"],
            "2",
            True,
            id="unavailable-window-state",
        ),
        pytest.param(
            "ventilate",
            ["off"],
            "1",
            True,
            id="wrong-floor-api-version",
        ),
        pytest.param(
            "keep_closed",
            ["off"],
            "2",
            False,
            id="closing-list-not-subset",
        ),
    ],
)
def test_fail_closed_regression_matrix(
    floor_state,
    opening_states,
    floor_api_version,
    closing_subset_valid,
):
    state, windows_to_open, windows_to_close = derive_control_state(
        floor_state=floor_state,
        opening_states=opening_states,
        floor_api_version=floor_api_version,
        closing_subset_valid=closing_subset_valid,
    )

    assert state == "unavailable"
    assert windows_to_open == []
    assert windows_to_close == []


def test_runtime_variable_contract_is_preserved():
    source = CONTROL_BLUEPRINT.read_text(encoding="utf-8")

    for name in (
        "control_state",
        "floor_state",
        "floor_reason",
        "windows_to_open",
        "windows_to_close",
        "windows_to_open_names",
        "windows_to_close_names",
        "invalid_windows",
        "invalid_closing_windows",
        "open_opening_windows",
        "closed_opening_windows",
        "open_closing_windows",
    ):
        assert f"{name}:" in source

def _template_trigger(document, trigger_id):
    return next(
        trigger
        for trigger in document["triggers"]
        if trigger.get("id") == trigger_id
    )


@pytest.mark.parametrize("trigger_id", ["close", "ok"])
def test_closing_entities_is_bound_inside_trigger_scope(trigger_id):
    """Trigger templates cannot see variables created later in actions."""
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)
    template = _template_trigger(document, trigger_id)["value_template"]

    assert "{% set closing_entities =" in template
    assert "configured_closing_entities" in template
    assert "opening_entities" in template


def test_no_template_trigger_uses_closing_entities_without_local_binding():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    for trigger in document["triggers"]:
        template = trigger.get("value_template")

        if not template:
            continue

        # Match the standalone variable, not configured_closing_entities.
        if not re.search(r"(?<!configured_)\bclosing_entities\b", template):
            continue

        assert "{% set closing_entities =" in template, (
            f"trigger {trigger.get('id')} uses closing_entities "
            "without defining it in trigger scope"
        )


def test_closing_entities_is_not_exposed_as_templated_trigger_variable():
    document = load_home_assistant_yaml(CONTROL_BLUEPRINT)

    assert "closing_entities" not in document["trigger_variables"]
