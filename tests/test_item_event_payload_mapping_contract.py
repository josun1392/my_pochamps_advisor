from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import (
    EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES,
    build_battle_state_context_from_ui_selected_state,
    build_item_event_context_from_confirmations,
)
from tests.test_advisor_payload_contract import (
    _move,
    _opponent_move_ui_advice_flow_payload,
    _panel,
    _window,
)
from ui.main_window import MainWindow


_FORBIDDEN_ITEM_EVENT_FIELDS = frozenset(
    {
        "berry_recovered_exact_hp",
        "exact_damage",
        "exact_hp",
        "focus_sash_post_hit_hp_1",
        "item_damage_modifier_applied",
        "item_speed_modifier_applied",
        "post_turn_hp_from_item",
        "post_turn_item_state",
        "quick_claw_activated_by_rng",
        "resolved_effects",
        "resolved_item_effect",
        "rng_roll",
        "speed_order_override",
    }
)

_FORBIDDEN_PROMPT_CLAIMS = (
    "focus sash left the target at exactly 1 hp",
    "quick claw rng succeeded",
    "berry restored exactly x hp",
    "post-turn item state is consumed",
    "resolved item effect",
    "exact damage changed",
    "resolved speed order",
)


def _valid_event(**overrides: Any) -> dict[str, Any]:
    event = {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": 5,
        "note": "User saw Focus Sash activation text.",
    }
    event.update(overrides)
    return event


def _event_missing(field_name: str) -> dict[str, Any]:
    event = _valid_event()
    event.pop(field_name)
    return event


def _safe_candidate_serialization(context: dict[str, Any]) -> str:
    return (
        "User confirmed an observed item event.\n"
        "source: explicit_user_event_confirmation\n"
        "confidence: observed\n"
        "This does not resolve exact HP, damage, RNG, or turn order.\n"
        f"candidate: {json.dumps(context, sort_keys=True)}"
    )


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _assert_forbidden_fields_absent(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in _FORBIDDEN_ITEM_EVENT_FIELDS
            _assert_forbidden_fields_absent(child)
    elif isinstance(value, list):
        for child in value:
            _assert_forbidden_fields_absent(child)


def _assert_forbidden_prompt_claims_absent(text: str) -> None:
    lower_text = text.lower()
    for phrase in _FORBIDDEN_PROMPT_CLAIMS:
        assert phrase not in lower_text


def test_checkbox_off_omits_future_item_event_context_candidate() -> None:
    events = [_valid_event()]

    context = None

    assert context is None


@pytest.mark.parametrize("event_type", sorted(EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES))
def test_checkbox_on_normalizes_only_allowed_observed_event_types(event_type: str) -> None:
    event = _valid_event(event_type=event_type)

    context = build_item_event_context_from_confirmations([event])

    assert context == {
        "observed_events": [
            {
                **event,
                "confidence": "observed",
            }
        ]
    }
    _assert_forbidden_fields_absent(context)


def test_checkbox_on_preserves_source_status_turn_note_and_adds_observed_confidence() -> None:
    events = [
        _valid_event(item="sitrus-berry", event_type="item_consumption_observed", turn=6),
        _valid_event(item="leftovers", event_type="item_recovery_observed", turn=None, note=None),
        _valid_event(item="focus-sash", event_type="item_prevention_observed", turn=7),
        _valid_event(item="choice-scarf", event_type="item_reveal_observed", turn=8),
    ]

    context = build_item_event_context_from_confirmations(events)

    assert context is not None
    assert [event["event_type"] for event in context["observed_events"]] == [
        "item_consumption_observed",
        "item_recovery_observed",
        "item_prevention_observed",
        "item_reveal_observed",
    ]
    for original, normalized in zip(events, context["observed_events"], strict=True):
        assert normalized["source"] == "explicit_user_event_confirmation"
        assert normalized["status"] == "user_confirmed"
        assert normalized["confidence"] == "observed"
        assert normalized["turn"] == original["turn"]
        assert normalized["note"] == original["note"]
    _assert_forbidden_fields_absent(context)


@pytest.mark.parametrize(
    "invalid_event",
    [
        _event_missing("side"),
        _event_missing("item"),
        _event_missing("event_type"),
        _event_missing("status"),
        _event_missing("source"),
        _valid_event(source="battle_log_observed"),
        _valid_event(status="inferred"),
        _valid_event(event_type="resolved_item_effect"),
        _valid_event(event_type="post_turn_item_state"),
        _valid_event(exact_hp=1),
        _valid_event(exact_damage=100),
        _valid_event(rng_roll=42),
        _valid_event(speed_order_override=True),
    ],
)
def test_checkbox_on_omits_invalid_item_events(invalid_event: dict[str, Any]) -> None:
    assert build_item_event_context_from_confirmations([invalid_event]) is None


def test_checkbox_on_omits_invalid_events_but_keeps_valid_observed_events() -> None:
    context = build_item_event_context_from_confirmations(
        [
            _valid_event(),
            _valid_event(event_type="resolved_item_effect"),
            _valid_event(item="leftovers", event_type="item_recovery_observed", turn=6),
        ]
    )

    assert context is not None
    assert [event["item"] for event in context["observed_events"]] == ["focus-sash", "leftovers"]
    _assert_forbidden_fields_absent(context)


def test_checkbox_gate_controls_runtime_item_event_payload_mapping() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["item_event_confirmations"] = [_valid_event()]

    off_prompt = advisor_client._build_ui_selected_prompt(
        battle_input,
        enable_turn_pipeline=False,
        enable_turn_order_context=False,
        enable_opponent_move_context=False,
        enable_battle_state_context=False,
    )
    on_prompt = advisor_client._build_ui_selected_prompt(
        battle_input,
        enable_turn_pipeline=True,
        enable_turn_order_context=True,
        enable_opponent_move_context=True,
        enable_battle_state_context=True,
    )
    off_payload = _prompt_payload(off_prompt)
    on_payload = _prompt_payload(on_prompt)

    for prompt, payload in ((off_prompt, off_payload), (on_prompt, on_payload)):
        assert "item_event_confirmations" not in payload
        _assert_forbidden_fields_absent(payload)
        _assert_forbidden_prompt_claims_absent(prompt)

    assert "item_event_context" not in off_payload
    assert "observed_events" not in off_payload
    assert "item_event_context" in on_payload
    assert on_payload["item_event_context"] == {
        "observed_events": [{**_valid_event(), "confidence": "observed"}]
    }
    assert "item_event_context" in on_prompt


def test_main_window_battle_input_includes_session_events_only_when_limited_context_is_enabled() -> None:
    my_panel = _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")])
    opponent_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    window = _window(my_panel, opponent_panel)
    window._item_event_confirmations = [_valid_event(), _valid_event(exact_hp=1)]

    off_input = window._build_llm_battle_input(include_item_event_confirmations=False)
    on_input = window._build_llm_battle_input(include_item_event_confirmations=True)

    assert "item_event_confirmations" not in off_input
    assert on_input["item_event_confirmations"] == [_valid_event()]
    _assert_forbidden_fields_absent(off_input)
    _assert_forbidden_fields_absent(on_input)


@pytest.mark.parametrize("limited_context_enabled", [False, True])
def test_main_window_advice_start_passes_limited_context_gate_to_battle_input(
    limited_context_enabled: bool,
) -> None:
    captured: dict[str, bool] = {}
    panel = SimpleNamespace(
        turn_pipeline_enabled=lambda: limited_context_enabled,
        set_error=lambda message: None,
        set_turn_pipeline_status_enabled=lambda enabled: None,
    )
    window = MainWindow.__new__(MainWindow)
    window._llm_thread = None
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    window.statusBar = lambda: SimpleNamespace(showMessage=lambda message: None)

    def fail_after_capturing_battle_input(*, include_item_event_confirmations: bool) -> dict[str, Any]:
        captured["include_item_event_confirmations"] = include_item_event_confirmations
        raise ValueError("test stop")

    window._build_llm_battle_input = fail_after_capturing_battle_input

    window._start_llm_advice()

    assert captured["include_item_event_confirmations"] is limited_context_enabled


def test_known_item_and_field_state_behavior_remain_separate_from_item_events() -> None:
    battle_input = {
        "pokemon": {
            "my_active": {"name_en": "Garchomp", "hp_percent": 100},
            "opponent_active": {"name_en": "Charizard", "hp_percent": 87},
        },
        "item_profiles": {
            "my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "leftovers"},
            "opponent_active": {
                "status": "user_confirmed",
                "source": "user_input",
                "item_id": "focus-sash",
            },
        },
        "field_profiles": {
            "weather": {"status": "user_confirmed", "source": "user_input", "value": "rain"},
        },
        "item_event_confirmations": [_valid_event()],
    }

    context = build_battle_state_context_from_ui_selected_state(
        battle_input,
        include_user_confirmed_items=True,
        include_user_confirmed_fields=True,
    )

    assert context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert context["opponent_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "focus-sash",
    }
    assert context["field"]["weather"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "rain",
    }
    assert "item_event_context" not in context
    assert "observed_events" not in context
    _assert_forbidden_fields_absent(context)


def test_future_candidate_safe_serialization_has_only_observed_boundary_wording() -> None:
    context = build_item_event_context_from_confirmations([_valid_event()])
    assert context is not None

    serialization = _safe_candidate_serialization(context)

    assert "User confirmed an observed item event." in serialization
    assert "source: explicit_user_event_confirmation" in serialization
    assert "confidence: observed" in serialization
    assert "This does not resolve exact HP, damage, RNG, or turn order." in serialization
    _assert_forbidden_prompt_claims_absent(serialization)
    _assert_forbidden_fields_absent(context)
