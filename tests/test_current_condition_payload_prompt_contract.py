from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import build_current_condition_context_from_confirmations
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


_FORBIDDEN_CONDITION_FIELDS = frozenset(
    {
        "condition_applied_this_turn",
        "condition_triggered_this_turn",
        "exact_post_turn_hp",
        "exact_status_damage",
        "final_speed_order",
        "freeze_thaw_roll",
        "full_paralysis_occurred",
        "post_turn_condition_state",
        "resolved_condition_effect",
        "rng_roll",
        "sleep_turns_remaining",
        "wake_up_turn",
    }
)


def _condition(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "side": "self",
        "condition_type": "burn",
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
        "confidence": "known",
    }
    candidate.update(overrides)
    return candidate


def _event() -> dict[str, Any]:
    return {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
    }


def _battle_input(*, conditions: list[dict[str, Any]] | None) -> dict[str, Any]:
    payload = deepcopy(_opponent_move_ui_advice_flow_payload())
    if conditions is not None:
        payload["current_condition_confirmations"] = conditions
    return payload


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _assert_forbidden_fields_absent(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in _FORBIDDEN_CONDITION_FIELDS
            _assert_forbidden_fields_absent(child)
    elif isinstance(value, list):
        for child in value:
            _assert_forbidden_fields_absent(child)


def _capture_offline_prompt(
    monkeypatch: pytest.MonkeyPatch,
    battle_input: dict[str, Any],
    *,
    limited_context_enabled: bool,
) -> str:
    prompts: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v12-59-current-condition"
        prompts.append(prompt)
        return "offline fixture", {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})
    advisor_client.run_ui_selected_advice(
        battle_input,
        model="offline-v12-59-current-condition",
        enable_battle_state_context=limited_context_enabled,
    )
    assert len(prompts) == 1
    return prompts[0]


def test_limited_context_maps_valid_self_and_opponent_current_conditions() -> None:
    conditions = [_condition(), _condition(side="opponent", condition_type="unknown")]
    prompt = advisor_client._build_ui_selected_prompt(
        _battle_input(conditions=conditions), enable_battle_state_context=True
    )
    payload = _prompt_payload(prompt)

    assert payload["condition_context"] == {"current_conditions": conditions}
    assert "current_condition_confirmations" not in payload
    assert "If condition_context is present" in prompt
    assert "Briefly acknowledge each current condition by side and condition type" in prompt
    assert "none (user-confirmed no current major status) versus unknown" in prompt
    _assert_forbidden_fields_absent(payload)


def test_none_is_preserved_as_current_no_major_status_not_a_removal_event() -> None:
    prompt = advisor_client._build_ui_selected_prompt(
        _battle_input(conditions=[_condition(condition_type="none")]),
        enable_battle_state_context=True,
    )
    payload = _prompt_payload(prompt)

    assert payload["condition_context"]["current_conditions"] == [_condition(condition_type="none")]
    assert "condition removal" not in prompt.lower()


def test_limited_context_off_omits_condition_context_and_guard_but_retains_candidate_input() -> None:
    battle_input = _battle_input(conditions=[_condition(), _condition(side="opponent", condition_type="unknown")])
    off_prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=False)
    on_prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)

    assert "current_condition_confirmations" in battle_input
    assert "condition_context" not in _prompt_payload(off_prompt)
    assert "If condition_context is present" not in off_prompt
    assert "condition_context" in _prompt_payload(on_prompt)
    assert "If condition_context is present" in on_prompt


@pytest.mark.parametrize(
    "invalid",
    [
        _condition(side="ally"),
        _condition(condition_type="confusion"),
        _condition(status="observed"),
        _condition(source="battle_log"),
        _condition(exact_status_damage=1),
        _condition(nested={"rng_roll": 1}),
    ],
)
def test_invalid_conditions_are_omitted_and_all_invalid_omits_context(invalid: dict[str, Any]) -> None:
    prompt = advisor_client._build_ui_selected_prompt(
        _battle_input(conditions=[invalid]), enable_battle_state_context=True
    )
    payload = _prompt_payload(prompt)

    assert build_current_condition_context_from_confirmations([invalid]) is None
    assert "condition_context" not in payload
    assert "If condition_context is present" not in prompt
    _assert_forbidden_fields_absent(payload)


def test_invalid_condition_is_omitted_without_hiding_another_valid_side() -> None:
    prompt = advisor_client._build_ui_selected_prompt(
        _battle_input(
            conditions=[
                _condition(),
                _condition(side="opponent", condition_type="confusion"),
            ]
        ),
        enable_battle_state_context=True,
    )
    payload = _prompt_payload(prompt)

    assert payload["condition_context"] == {"current_conditions": [_condition()]}
    _assert_forbidden_fields_absent(payload)


def test_valid_conditions_coexist_with_item_events_and_offline_production_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    battle_input = _battle_input(conditions=[_condition(), _condition(side="opponent", condition_type="unknown")])
    battle_input["item_event_confirmations"] = [_event()]
    prompt = _capture_offline_prompt(monkeypatch, battle_input, limited_context_enabled=True)
    payload = _prompt_payload(prompt)

    assert payload["condition_context"]["current_conditions"] == [
        _condition(),
        _condition(side="opponent", condition_type="unknown"),
    ]
    assert payload["item_event_context"]["observed_events"] == [{**_event(), "confidence": "observed"}]
    assert "If condition_context is present" in prompt
    assert "If item_event_context is present" in prompt
    assert "Do not infer when a condition was applied" in prompt
    assert "Trusted context attribution:" in prompt
    assert "Current condition - self: burn (user-confirmed current state)." in prompt
    assert "Current condition - opponent: unknown (user-confirmed current state)." in prompt
    assert (
        "Observed item event - opponent: focus-sash / item_activation_observed "
        "(explicitly user-confirmed observation)."
    ) in prompt
    assert "Briefly acknowledge each listed category and identity" in prompt
    assert "Do not merge current conditions with observed item events" in prompt
    _assert_forbidden_fields_absent(payload)


def test_item_event_only_does_not_add_condition_specific_guard() -> None:
    battle_input = _battle_input(conditions=None)
    battle_input["item_event_confirmations"] = [_event()]

    prompt = advisor_client._build_ui_selected_prompt(
        battle_input,
        enable_battle_state_context=True,
    )

    assert "item_event_context" in _prompt_payload(prompt)
    assert "If item_event_context is present" in prompt
    assert "If condition_context is present" not in prompt
    assert "Briefly acknowledge each current condition by side and condition type" not in prompt
    assert "Trusted context attribution:" in prompt
    assert "Observed item event - opponent: focus-sash / item_activation_observed" in prompt
    assert "Current condition -" not in prompt


def test_condition_only_attribution_has_no_observed_item_event_wording() -> None:
    prompt = advisor_client._build_ui_selected_prompt(
        _battle_input(conditions=[_condition(condition_type="none")]),
        enable_battle_state_context=True,
    )

    assert "Trusted context attribution:" in prompt
    assert "Current condition - self: none (user-confirmed current state)." in prompt
    assert "Observed item event -" not in prompt


def test_disabled_or_invalid_context_omits_attribution_block() -> None:
    disabled = _battle_input(conditions=[_condition()])
    disabled["item_event_confirmations"] = [_event()]
    disabled_prompt = advisor_client._build_ui_selected_prompt(disabled, enable_battle_state_context=False)
    invalid_prompt = advisor_client._build_ui_selected_prompt(
        _battle_input(conditions=[_condition(condition_type="confusion")]),
        enable_battle_state_context=True,
    )

    assert "Trusted context attribution:" not in disabled_prompt
    assert "Trusted context attribution:" not in invalid_prompt
