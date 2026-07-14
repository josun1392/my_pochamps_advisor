from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import llm.advisor_client as advisor_client
import scripts.run_sanitized_condition_smoke as smoke_cli
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


TrustedEntry = tuple[str, str, str, str | None]


def _ability(side: str, ability: str) -> dict[str, str]:
    return {
        "side": side,
        "ability": ability,
        "status": "user_confirmed",
        "source": "user_confirmed_current_ability",
    }


def _condition(side: str, condition_type: str) -> dict[str, str]:
    return {
        "side": side,
        "condition_type": condition_type,
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
    }


def _event() -> dict[str, Any]:
    return {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": None,
        "note": None,
    }


def _battle_input(
    *,
    abilities: list[dict[str, str]] | None = None,
    conditions: list[dict[str, str]] | None = None,
    item_event: bool = False,
) -> dict[str, Any]:
    result = deepcopy(_opponent_move_ui_advice_flow_payload())
    if abilities is not None:
        result["current_ability_confirmations"] = abilities
    if conditions is not None:
        result["current_condition_confirmations"] = conditions
    if item_event:
        result["item_event_confirmations"] = [_event()]
    return result


def _payload_and_entries(battle_input: dict[str, Any], *, enabled: bool = True) -> tuple[dict[str, Any], tuple[TrustedEntry, ...], str]:
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=enabled)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    return payload, advisor_client.build_trusted_context_acknowledgement_entries(payload), prompt


def _response(entries: tuple[TrustedEntry, ...], advice: str = "Choose a cautious line because this trusted context remains limited.") -> str:
    lines = []
    for category, side, identity, event_type in entries:
        if category == "current_condition":
            lines.append(f"- Current condition | {side} | {identity}")
        elif category == "current_ability":
            lines.append(f"- Current ability | {side} | {identity}")
        else:
            lines.append(f"- Observed item event | {side} | {identity} | {event_type}")
    return "[Trusted Context]\n" + "\n".join(lines) + f"\n\n[Advice]\n{advice}"


@pytest.mark.parametrize(
    ("name", "battle_input", "enabled", "expected"),
    [
        ("self", _battle_input(abilities=[_ability("self", "intimidate")]), True, (("current_ability", "self", "intimidate", None),)),
        ("unknown", _battle_input(abilities=[_ability("opponent", "unknown")]), True, (("current_ability", "opponent", "unknown", None),)),
        ("both", _battle_input(abilities=[_ability("self", "Mold Breaker"), _ability("opponent", "Quark Drive")]), True, (("current_ability", "self", "mold-breaker", None), ("current_ability", "opponent", "quark-drive", None))),
        ("condition", _battle_input(abilities=[_ability("self", "intimidate")], conditions=[_condition("self", "burn")]), True, (("current_condition", "self", "burn", None), ("current_ability", "self", "intimidate", None))),
        ("event", _battle_input(abilities=[_ability("self", "intimidate")], item_event=True), True, (("current_ability", "self", "intimidate", None), ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"))),
        ("combined", _battle_input(abilities=[_ability("self", "intimidate"), _ability("opponent", "unknown")], conditions=[_condition("self", "burn")], item_event=True), True, (("current_condition", "self", "burn", None), ("current_ability", "self", "intimidate", None), ("current_ability", "opponent", "unknown", None), ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"))),
        ("limited-off", _battle_input(abilities=[_ability("self", "intimidate")]), False, ()),
        ("invalid-none", _battle_input(abilities=[_ability("self", "none")]), True, ()),
        ("candidate-list", _battle_input(abilities=[_ability("self", "levitate / heatproof")]), True, ()),
        ("absent", _battle_input(), True, ()),
    ],
)
def test_ability_context_matrix_maps_prompt_and_structured_entries(
    name: str,
    battle_input: dict[str, Any],
    enabled: bool,
    expected: tuple[TrustedEntry, ...],
) -> None:
    payload, entries, prompt = _payload_and_entries(battle_input, enabled=enabled)

    assert entries == expected, name
    assert ("ability_context" in payload) is bool(any(entry[0] == "current_ability" for entry in expected))
    if expected:
        assert "Start the answer with exactly this short trusted-context acknowledgement format" in prompt
    else:
        assert "Current ability |" not in prompt
        assert "ability_context" not in payload
        return

    response = _response(entries)
    assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is None
    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries)[0] == "pass"


@pytest.mark.parametrize(
    ("mutation", "expected_summary"),
    [
        (lambda response: response.replace("- Current ability | self | intimidate\n", ""), "ability entry"),
        (lambda response: response.replace("[Advice]", "- Current ability | opponent | levitate\n\n[Advice]"), "ability entry"),
        (lambda response: response.replace("[Advice]", "- Current ability | self | intimidate\n\n[Advice]"), "ability entry"),
        (lambda response: response.replace("self | intimidate", "opponent | intimidate"), "ability entry"),
        (lambda response: response.replace("Current ability | self | intimidate", "Current condition | self | intimidate"), "ability entry"),
        (lambda response: response.replace("opponent | unknown", "opponent | levitate"), "ability entry"),
        (lambda response: response.replace("opponent | unknown", "opponent | levitate / heatproof"), "ability entry"),
        (lambda response: response.replace("Choose a cautious line because this trusted context remains limited.", "The ability activated this turn."), "forbidden"),
        (lambda response: response.replace("Choose a cautious line because this trusted context remains limited.", "Its exact stat change is known."), "forbidden"),
        (lambda response: response.replace("Choose a cautious line because this trusted context remains limited.", "Its immunity was resolved."), "forbidden"),
        (lambda response: response.replace("Choose a cautious line because this trusted context remains limited.", "The final speed order is known."), "forbidden"),
        (lambda response: response.replace("Choose a cautious line because this trusted context remains limited.", "The ability was suppressed."), "forbidden"),
        (lambda response: response.replace("Choose a cautious line because this trusted context remains limited.", ""), "advice body missing"),
    ],
)
def test_ability_acknowledgement_and_semantic_failures_are_sanitized(
    mutation: Any,
    expected_summary: str,
) -> None:
    _, entries, _ = _payload_and_entries(
        _battle_input(abilities=[_ability("self", "intimidate"), _ability("opponent", "unknown")])
    )
    semantic_status, summary = smoke_cli.evaluate_current_condition_item_event_response(
        mutation(_response(entries)), expected_entries=entries
    )

    assert semantic_status == "fail"
    assert expected_summary in summary


def test_unknown_ability_is_not_promoted_from_species_or_advice_body() -> None:
    _, entries, _ = _payload_and_entries(_battle_input(abilities=[_ability("opponent", "unknown")]))
    response = _response(entries, "Opponent current ability is levitate because its species can have Levitate.")

    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries) == (
        "fail",
        "unknown-ability inference",
    )


def test_normal_ui_path_preserves_ability_structured_response(monkeypatch: pytest.MonkeyPatch) -> None:
    battle_input = _battle_input(abilities=[_ability("self", "intimidate")], conditions=[_condition("self", "burn")])
    _, entries, _ = _payload_and_entries(battle_input)
    response = _response(entries)
    usage = {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}
    monkeypatch.setattr(advisor_client, "call_gemini", lambda prompt, model: (response, usage))
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    advice, returned_usage, summary = advisor_client.run_ui_selected_advice(
        battle_input, model="offline-v12-75-ui", enable_battle_state_context=True
    )

    assert advice == response
    assert returned_usage == usage
    assert summary == {"mocked": True}
    assert not advice.lstrip().startswith("{")
