from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import llm.advisor_client as advisor_client
import scripts.run_sanitized_condition_smoke as smoke_cli
import ui.main_window as main_window_module
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload
from ui.main_window import LLMAdviceWorker


TrustedEntry = tuple[str, str, str, str | None]


def _condition(side: str, condition_type: str) -> dict[str, str]:
    return {
        "side": side,
        "condition_type": condition_type,
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
    }


def _event(side: str, item: str, event_type: str, *, turn: int | None = None) -> dict[str, Any]:
    return {
        "side": side,
        "item": item,
        "event_type": event_type,
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": turn,
        "note": None,
    }


def _battle_input(
    *,
    conditions: list[dict[str, str]] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = deepcopy(_opponent_move_ui_advice_flow_payload())
    if conditions is not None:
        result["current_condition_confirmations"] = conditions
    if events is not None:
        result["item_event_confirmations"] = events
    return result


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _acknowledgement_response(entries: tuple[TrustedEntry, ...], advice: str) -> str:
    lines = []
    for category, side, identity, event_type in entries:
        if category == "current_condition":
            lines.append(f"- Current condition | {side} | {identity}")
        else:
            lines.append(f"- Observed item event | {side} | {identity} | {event_type}")
    return "[Trusted Context]\n" + "\n".join(lines) + f"\n\n[Advice]\n{advice}"


MATRIX = (
    pytest.param(
        "condition-and-item-event",
        _battle_input(
            conditions=[_condition("self", "burn"), _condition("opponent", "unknown")],
            events=[_event("opponent", "focus-sash", "item_activation_observed")],
        ),
        True,
        (
            ("current_condition", "self", "burn", None),
            ("current_condition", "opponent", "unknown", None),
            ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"),
        ),
        id="condition-and-item-event",
    ),
    pytest.param(
        "condition-one-side",
        _battle_input(conditions=[_condition("self", "paralysis")]),
        True,
        (("current_condition", "self", "paralysis", None),),
        id="condition-one-side",
    ),
    pytest.param(
        "condition-both-sides",
        _battle_input(conditions=[_condition("self", "none"), _condition("opponent", "poison")]),
        True,
        (("current_condition", "self", "none", None), ("current_condition", "opponent", "poison", None)),
        id="condition-both-sides",
    ),
    pytest.param(
        "unknown-only",
        _battle_input(conditions=[_condition("opponent", "unknown")]),
        True,
        (("current_condition", "opponent", "unknown", None),),
        id="unknown-only",
    ),
    pytest.param(
        "none-only",
        _battle_input(conditions=[_condition("self", "none")]),
        True,
        (("current_condition", "self", "none", None),),
        id="none-only",
    ),
    pytest.param(
        "item-event-only",
        _battle_input(events=[_event("opponent", "leftovers", "item_recovery_observed")]),
        True,
        (("observed_item_event", "opponent", "leftovers", "item_recovery_observed"),),
        id="item-event-only",
    ),
    pytest.param(
        "multiple-item-events",
        _battle_input(
            events=[
                _event("opponent", "focus-sash", "item_activation_observed", turn=2),
                _event("self", "leftovers", "item_recovery_observed", turn=3),
            ]
        ),
        True,
        (
            ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"),
            ("observed_item_event", "self", "leftovers", "item_recovery_observed"),
        ),
        id="multiple-item-events",
    ),
    pytest.param("context-absent", _battle_input(), True, (), id="context-absent"),
    pytest.param(
        "limited-context-off",
        _battle_input(
            conditions=[_condition("self", "burn")],
            events=[_event("opponent", "focus-sash", "item_activation_observed")],
        ),
        False,
        (),
        id="limited-context-off",
    ),
)


@pytest.mark.parametrize(("_name", "battle_input", "enabled", "expected"), MATRIX)
def test_context_matrix_generates_dynamic_prompt_and_expected_entries(
    _name: str,
    battle_input: dict[str, Any],
    enabled: bool,
    expected: tuple[TrustedEntry, ...],
) -> None:
    prompt = advisor_client._build_ui_selected_prompt(
        battle_input,
        enable_battle_state_context=enabled,
    )
    payload = _prompt_payload(prompt)

    assert advisor_client.build_trusted_context_acknowledgement_entries(payload) == expected
    assert advisor_client.build_ui_selected_trusted_context_entries(
        battle_input,
        enable_battle_state_context=enabled,
    ) == expected

    if not expected:
        assert "Start the answer with exactly this short trusted-context acknowledgement format" not in prompt
        assert "[Trusted Context]" not in prompt
        return

    assert "Start the answer with exactly this short trusted-context acknowledgement format" in prompt
    assert "[Advice]" in prompt
    for category, side, identity, event_type in expected:
        if category == "current_condition":
            assert f"- Current condition | {side} | {identity}" in prompt
        else:
            assert f"- Observed item event | {side} | {identity} | {event_type}" in prompt


@pytest.mark.parametrize(("_name", "battle_input", "enabled", "expected"), MATRIX[:7])
def test_context_matrix_canonical_and_minor_format_acknowledgements_validate(
    _name: str,
    battle_input: dict[str, Any],
    enabled: bool,
    expected: tuple[TrustedEntry, ...],
) -> None:
    del battle_input, enabled
    canonical = _acknowledgement_response(
        expected,
        "Choose a cautious line and keep the limited context separate from any unconfirmed outcome.",
    )
    minor_variant = canonical.replace("Current condition", "Current Condition").replace("focus-sash", "Focus Sash")

    assert advisor_client.validate_trusted_context_acknowledgement(canonical, expected) is None
    assert advisor_client.validate_trusted_context_acknowledgement(minor_variant, expected) is None


def test_exact_set_matrix_rejects_missing_extra_duplicate_and_changed_entries() -> None:
    expected = MATRIX[0].values[3]
    canonical = _acknowledgement_response(expected, "Switch or choose a safer line while the outcome remains uncertain.")
    missing = _acknowledgement_response(expected[:-1], "Choose cautiously.")
    extra = canonical.replace("\n\n[Advice]", "\n- Current condition | self | paralysis\n\n[Advice]")
    duplicate = canonical.replace("\n\n[Advice]", "\n- Current condition | self | burn\n\n[Advice]")
    side_swap = canonical.replace("Current condition | self | burn", "Current condition | opponent | burn")
    category_swap = canonical.replace(
        "Observed item event | opponent | focus-sash | item_activation_observed",
        "Current condition | opponent | focus-sash",
    )
    identity_change = canonical.replace("opponent | unknown", "opponent | paralysis")
    event_type_change = canonical.replace("item_activation_observed", "item_recovery_observed")
    event_type_missing = canonical.replace(" | item_activation_observed", "")

    assert advisor_client.validate_trusted_context_acknowledgement(missing, expected) == "trusted-context entry mismatch"
    assert advisor_client.validate_trusted_context_acknowledgement(extra, expected) == "trusted-context entry mismatch"
    assert advisor_client.validate_trusted_context_acknowledgement(duplicate, expected) == "trusted-context duplicate entry"
    assert advisor_client.validate_trusted_context_acknowledgement(side_swap, expected) == "trusted-context entry mismatch"
    assert advisor_client.validate_trusted_context_acknowledgement(category_swap, expected) == "trusted-context entry mismatch"
    assert advisor_client.validate_trusted_context_acknowledgement(identity_change, expected) == "trusted-context entry mismatch"
    assert advisor_client.validate_trusted_context_acknowledgement(event_type_change, expected) == "trusted-context entry mismatch"
    assert "malformed" in (advisor_client.validate_trusted_context_acknowledgement(event_type_missing, expected) or "")


def test_absent_or_off_context_does_not_require_a_block_but_rejects_an_extra_entry() -> None:
    normal_advice = "Choose the safer action; limited trusted context was not supplied."
    extra_block = _acknowledgement_response(
        (("current_condition", "self", "burn", None),),
        normal_advice,
    )

    assert "[Trusted Context]" not in normal_advice
    assert advisor_client.validate_trusted_context_acknowledgement(extra_block, ()) == "trusted-context entry mismatch"


def _advice_is_usable(response: str, entries: tuple[TrustedEntry, ...]) -> bool:
    failure = advisor_client.validate_trusted_context_acknowledgement(response, entries)
    if failure is not None:
        return False
    advice = response.split("[Advice]", 1)[1].strip().lower()
    has_recommendation = any(token in advice for token in ("switch", "attack", "choose", "preserve", "scout"))
    has_uncertainty = any(token in advice for token in ("uncertain", "limited", "cannot", "avoid"))
    return has_recommendation and has_uncertainty and "source:" not in advice and "confidence:" not in advice and "{" not in advice


def test_advice_ux_keeps_short_readback_and_actionable_uncertainty_aware_guidance() -> None:
    expected = MATRIX[0].values[3]
    usable = _acknowledgement_response(
        expected,
        "Choose a conservative switch or attack line; burn and the observed event are limited context, so avoid assuming an exact outcome.",
    )
    acknowledgement_only = _acknowledgement_response(expected, "")
    repetition_only = _acknowledgement_response(
        expected,
        "Current condition self burn; current condition opponent unknown; observed item event opponent focus-sash.",
    )

    assert _advice_is_usable(usable, expected)
    assert not _advice_is_usable(acknowledgement_only, expected)
    assert not _advice_is_usable(repetition_only, expected)


def test_none_unknown_and_item_event_boundaries_remain_non_resolved() -> None:
    expected = MATRIX[0].values[3]
    pass_response = _acknowledgement_response(
        expected,
        "Choose cautiously: the opponent condition remains unknown and the observed Focus Sash event does not settle an exact outcome.",
    )
    exact_response = _acknowledgement_response(
        expected,
        "Attack because Focus Sash left the Pokemon at exactly 1 HP.",
    )
    none_expected = (("current_condition", "self", "none", None),)
    none_response = _acknowledgement_response(
        none_expected,
        "Choose an attack while treating no current major status as present-state context, not a recovery event.",
    )

    assert smoke_cli.evaluate_current_condition_item_event_response(pass_response, expected_entries=expected)[0] == "pass"
    assert smoke_cli.evaluate_current_condition_item_event_response(exact_response, expected_entries=expected)[0] == "fail"
    assert advisor_client.validate_trusted_context_acknowledgement(none_response, none_expected) is None
    assert "recovered" not in none_response.lower() and "removed" not in none_response.lower()


def test_normal_ui_flow_preserves_structured_response_without_cli_json_interception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = MATRIX[0].values[3]
    response = _acknowledgement_response(
        expected,
        "Choose a conservative line because the available trusted context is limited and does not resolve the turn.",
    )
    battle_input = MATRIX[0].values[1]
    monkeypatch.setattr(
        advisor_client,
        "call_gemini",
        lambda prompt, model: (response, {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}),
    )
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    recommendation, usage, summary = advisor_client.run_ui_selected_advice(
        battle_input,
        model="offline-v12-72-ui",
        enable_battle_state_context=True,
    )

    assert recommendation == response
    assert usage == {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}
    assert summary == {"mocked": True}
    assert not recommendation.lstrip().startswith("{")

    monkeypatch.setattr(main_window_module, "run_ui_selected_advice", lambda *args, **kwargs: (response, usage, summary))
    worker = LLMAdviceWorker(battle_input, enable_battle_state_context=True)
    received: list[tuple[str, dict[str, Any]]] = []
    worker.finished.connect(lambda text, payload: received.append((text, payload)))
    worker.run()

    assert received == [(response, {"usage": usage, "summary": summary})]
