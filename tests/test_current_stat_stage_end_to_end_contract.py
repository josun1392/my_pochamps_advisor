from __future__ import annotations

import json
from copy import deepcopy

import pytest

import llm.advisor_client as advisor_client
import scripts.run_sanitized_condition_smoke as smoke_cli
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


def _stage(side: str, stat: str, stage: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}


def _payload(stages: list[dict[str, object]], *, enabled: bool = True) -> tuple[dict, tuple, str]:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_stat_stage_confirmations"] = stages
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=enabled)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    return payload, advisor_client.build_trusted_context_acknowledgement_entries(payload), prompt


def _response(entries: tuple, advice: str = "Choose cautiously; these current stages do not settle exact damage or turn order.") -> str:
    lines = []
    for category, side, identity, detail in entries:
        if category == "current_stat_stage":
            value = int(detail)
            rendered = f"{value:+d}" if value else "0"
            lines.append(f"- Current stat stage | {side} | {identity} | {rendered}")
        else:
            raise AssertionError(category)
    return "[Trusted Context]\n" + "\n".join(lines) + f"\n\n[Advice]\n{advice}"


@pytest.mark.parametrize(
    "stages",
    [
        [_stage("self", "attack", -1)], [_stage("self", "speed", 2)],
        [_stage("self", "attack", -1), _stage("self", "speed", 2)],
        [_stage("self", "attack", 0), _stage("opponent", "defense", -2)],
        [_stage("self", "attack", -6)], [_stage("opponent", "speed", 6)],
    ],
)
def test_stage_matrix_payload_prompt_parser_and_cli_evaluator(stages: list[dict[str, object]]) -> None:
    payload, entries, prompt = _payload(stages)
    assert payload["stat_stage_context"]["current_stages"] == [{**entry, "confidence": "known"} for entry in stages]
    assert "If stat_stage_context is present" in prompt
    assert all(entry[0] == "current_stat_stage" for entry in entries)
    response = _response(entries)
    assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is None
    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries)[0] == "pass"


def test_stage_gate_invalid_and_absent_paths_do_not_require_trusted_entries() -> None:
    for stages, enabled in (([_stage("self", "attack", 7)], True), ([_stage("self", "attack", -1)], False), ([], True)):
        payload, entries, prompt = _payload(stages, enabled=enabled)
        assert entries == ()
        assert "stat_stage_context" not in payload
        assert "Current stat stage |" not in prompt


@pytest.mark.parametrize(
    "advice",
    ["Intimidate activated this turn.", "Attack dropped this turn.", "The exact final Attack is 100.", "The final speed order is known.", "The exact damage is 42."],
)
def test_stage_forbidden_claims_fail_after_exact_acknowledgement(advice: str) -> None:
    _, entries, _ = _payload([_stage("self", "attack", -1)])
    assert smoke_cli.evaluate_current_condition_item_event_response(_response(entries, advice), expected_entries=entries)[0] == "fail"


def test_stage_exact_set_rejects_missing_extra_duplicate_side_stat_and_value_changes() -> None:
    _, entries, _ = _payload([_stage("self", "attack", -1), _stage("self", "speed", 2)])
    canonical = _response(entries)
    cases = [
        canonical.replace("- Current stat stage | self | speed | +2\n", ""),
        canonical.replace("[Advice]", "- Current stat stage | opponent | defense | -2\n\n[Advice]"),
        canonical.replace("[Advice]", "- Current stat stage | self | attack | -1\n\n[Advice]"),
        canonical.replace("self | attack", "opponent | attack"), canonical.replace("attack | -1", "defense | -1"),
        canonical.replace("speed | +2", "speed | +3"), canonical.replace("speed | +2", "speed | +7"),
    ]
    for response in cases:
        assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is not None


def test_stage_coexists_with_condition_ability_and_observed_item_event() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_stat_stage_confirmations"] = [_stage("self", "attack", -1)]
    battle_input["current_condition_confirmations"] = [{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]
    battle_input["current_ability_confirmations"] = [{"side": "self", "ability": "intimidate", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]
    battle_input["item_event_confirmations"] = [{"side": "opponent", "item": "focus-sash", "event_type": "item_activation_observed", "status": "user_confirmed", "source": "explicit_user_event_confirmation", "turn": None, "note": None}]
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    entries = advisor_client.build_trusted_context_acknowledgement_entries(payload)

    assert entries == (
        ("current_condition", "self", "burn", None),
        ("current_ability", "self", "intimidate", None),
        ("current_stat_stage", "self", "attack", "-1"),
        ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"),
    )
    response = (
        "[Trusted Context]\n- Current condition | self | burn\n- Current ability | self | intimidate\n"
        "- Current stat stage | self | attack | -1\n- Observed item event | opponent | focus-sash | item_activation_observed\n\n"
        "[Advice]\nChoose cautiously; the current stage does not establish its cause, exact damage, or final order."
    )
    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries)[0] == "pass"
