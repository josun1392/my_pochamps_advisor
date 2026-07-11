from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


_FORBIDDEN_FIELDS = frozenset(
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

_FORBIDDEN_POSITIVE_CLAIMS = (
    "the item definitely resolved its full effect",
    "exact hp was restored",
    "exact damage was prevented",
    "the pokemon survived at exactly 1 hp",
    "quick claw activated because of a specific rng roll",
    "the item changed the final speed order",
    "the berry restored an exact amount",
    "the item damage modifier was applied",
    "the resulting post-turn hp is known",
)


def _event(**overrides: Any) -> dict[str, Any]:
    result = {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": 5,
        "note": "User saw Focus Sash activation text.",
    }
    result.update(overrides)
    return result


def _battle_input(*, events: list[dict[str, Any]] | None) -> dict[str, Any]:
    payload = deepcopy(_opponent_move_ui_advice_flow_payload())
    payload["item_profiles"] = {
        "my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "leftovers"},
        "opponent_active": {"status": "user_confirmed", "source": "user_input", "item_id": "choice-scarf"},
    }
    if events is not None:
        payload["item_event_confirmations"] = events
    return payload


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _assert_forbidden_fields_absent(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in _FORBIDDEN_FIELDS
            _assert_forbidden_fields_absent(child)
    elif isinstance(value, list):
        for child in value:
            _assert_forbidden_fields_absent(child)


def _assert_forbidden_positive_claims_absent(prompt: str) -> None:
    lower_prompt = prompt.lower()
    for claim in _FORBIDDEN_POSITIVE_CLAIMS:
        assert claim not in lower_prompt


def _capture_offline_ui_prompt(
    monkeypatch: pytest.MonkeyPatch,
    battle_input: dict[str, Any],
    *,
    limited_context_enabled: bool,
) -> tuple[str, int]:
    captured_prompts: list[str] = []
    fake_provider_calls = 0

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        nonlocal fake_provider_calls
        assert model == "offline-v12-41-item-event"
        fake_provider_calls += 1
        captured_prompts.append(prompt)
        return (
            "The user explicitly confirmed an observed item event. This does not resolve exact HP, damage, RNG, or turn order.",
            {"input_tokens": 12, "output_tokens": 8, "cached_tokens": 0},
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    response, usage, summary = advisor_client.run_ui_selected_advice(
        battle_input,
        model="offline-v12-41-item-event",
        enable_battle_state_context=limited_context_enabled,
    )

    assert response.startswith("The user explicitly confirmed")
    assert usage == {"input_tokens": 12, "output_tokens": 8, "cached_tokens": 0}
    assert summary == {"mocked": True}
    assert fake_provider_calls == 1
    assert len(captured_prompts) == 1
    return captured_prompts[0], fake_provider_calls


def test_checkbox_off_omits_observed_event_payload_and_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    event = _event(item="yache-berry", event_type="item_prevention_observed")

    prompt, fake_provider_calls = _capture_offline_ui_prompt(
        monkeypatch,
        _battle_input(events=[event]),
        limited_context_enabled=False,
    )
    payload = _prompt_payload(prompt)

    assert fake_provider_calls == 1
    assert "item_event_context" not in payload
    assert "observed_events" not in payload
    assert "yache-berry" not in prompt
    assert "item_prevention_observed" not in prompt
    assert "If item_event_context is present" not in prompt
    _assert_forbidden_fields_absent(payload)
    _assert_forbidden_positive_claims_absent(prompt)


@pytest.mark.parametrize("event_type", sorted(EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES))
def test_checkbox_on_serializes_each_observed_event_type_safely(
    monkeypatch: pytest.MonkeyPatch,
    event_type: str,
) -> None:
    event = _event(event_type=event_type)

    prompt, fake_provider_calls = _capture_offline_ui_prompt(
        monkeypatch,
        _battle_input(events=[event]),
        limited_context_enabled=True,
    )
    payload = _prompt_payload(prompt)
    observed_event = payload["item_event_context"]["observed_events"][0]

    assert fake_provider_calls == 1
    assert observed_event == {**event, "confidence": "observed"}
    assert "If item_event_context is present" in prompt
    assert "explicitly user-confirmed observed item event" in prompt
    assert "not a resolved mechanic result" in prompt
    assert "Do not infer exact HP, exact damage" in prompt
    _assert_forbidden_fields_absent(payload)
    _assert_forbidden_positive_claims_absent(prompt)


def test_checkbox_on_preserves_none_turn_note_and_separates_known_item_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event(side="self", item="leftovers", event_type="item_recovery_observed", turn=None, note=None)

    prompt, _ = _capture_offline_ui_prompt(
        monkeypatch,
        _battle_input(events=[event]),
        limited_context_enabled=True,
    )
    payload = _prompt_payload(prompt)
    battle_state = payload["battle_state_context"]
    observed_event = payload["item_event_context"]["observed_events"][0]

    assert battle_state["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert observed_event == {**event, "confidence": "observed"}
    assert battle_state["self_active"]["item"] != observed_event
    assert "item_event_context" in payload
    _assert_forbidden_fields_absent(payload)


def test_known_item_without_explicit_event_omits_observed_event_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt, _ = _capture_offline_ui_prompt(
        monkeypatch,
        _battle_input(events=None),
        limited_context_enabled=True,
    )
    payload = _prompt_payload(prompt)

    assert payload["battle_state_context"]["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert "item_event_context" not in payload
    assert "If item_event_context is present" not in prompt


def test_invalid_raw_events_do_not_reappear_in_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid_events = [
        _event(item="missing-side", side=None),
        _event(item="wrong-source", source="battle_log_observed"),
        _event(item="exact-hp", exact_hp=1),
        _event(item="rng-order", rng_roll=42, speed_order_override=True),
    ]

    prompt, _ = _capture_offline_ui_prompt(
        monkeypatch,
        _battle_input(events=invalid_events),
        limited_context_enabled=True,
    )
    payload = _prompt_payload(prompt)

    assert "item_event_context" not in payload
    for item_name in ("missing-side", "wrong-source", "exact-hp", "rng-order"):
        assert item_name not in prompt
    _assert_forbidden_fields_absent(payload)
    _assert_forbidden_positive_claims_absent(prompt)
