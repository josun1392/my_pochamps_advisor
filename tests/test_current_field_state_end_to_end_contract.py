from __future__ import annotations

import json
from copy import deepcopy

import llm.advisor_client as advisor_client
import scripts.run_sanitized_condition_smoke as smoke_cli
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


def _field() -> dict[str, object]:
    return {"weather": "rain", "terrain": "none", "global_effects": ["trick-room"], "side_effects": [{"side": "self", "effect": "reflect"}, {"side": "opponent", "effect": "tailwind"}], "status": "user_confirmed", "source": "user_confirmed_current_field_state"}


def _prompt_payload(*, enabled: bool = True) -> tuple[dict, tuple, str]:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_field_state_confirmation"] = _field()
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=enabled)
    return json.loads(prompt.rsplit("\n\n", 1)[1]), advisor_client.build_ui_selected_trusted_context_entries(battle_input, enable_battle_state_context=enabled), prompt


def _response(entries: tuple, advice: str = "Treat the confirmed field as context, but do not settle exact damage or order.") -> str:
    names = {"current_weather": "Current weather", "current_terrain": "Current terrain", "current_global_field_effect": "Current global field effect", "current_side_field_effect": "Current side field effect"}
    lines = []
    for category, side, identity, _ in entries:
        prefix = names[category]
        lines.append(f"- {prefix} | {side} | {identity}" if side else f"- {prefix} | {identity}")
    return "[Trusted Context]\n" + "\n".join(lines) + f"\n\n[Advice]\n{advice}"


def test_field_snapshot_maps_to_prompt_acknowledgement_and_cli_evaluator() -> None:
    payload, entries, prompt = _prompt_payload()
    assert payload["field_state_context"]["current_field"]["confidence"] == "known"
    assert entries == (("current_weather", "", "rain", None), ("current_terrain", "", "none", None), ("current_global_field_effect", "", "trick-room", None), ("current_side_field_effect", "self", "reflect", None), ("current_side_field_effect", "opponent", "tailwind", None))
    assert "If field_state_context is present" in prompt
    response = _response(entries)
    assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is None
    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries)[0] == "pass"


def test_field_exact_set_gate_and_forbidden_claims() -> None:
    payload, entries, _ = _prompt_payload()
    assert "field_state_context" in payload
    canonical = _response(entries)
    for invalid in (canonical.replace("- Current weather | rain\n", ""), canonical.replace("rain", "sun", 1), canonical.replace("[Advice]", "- Current terrain | electric\n\n[Advice]"), canonical.replace("self | reflect", "opponent | reflect")):
        assert advisor_client.validate_trusted_context_acknowledgement(invalid, entries) is not None
    for claim in ("Rain Dance was used this turn.", "There are turns remaining.", "Tailwind guarantees moving first.", "Reflect halves the damage exactly."):
        assert smoke_cli.evaluate_current_condition_item_event_response(_response(entries, claim), expected_entries=entries)[0] == "fail"


def test_field_limited_context_off_and_invalid_snapshot_are_absent() -> None:
    payload, entries, prompt = _prompt_payload(enabled=False)
    assert "field_state_context" not in payload and entries == () and "Current weather |" not in prompt
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_field_state_confirmation"] = {**_field(), "started_this_turn": True}
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    assert "field_state_context" not in json.loads(prompt.rsplit("\n\n", 1)[1])


def test_field_coexists_with_condition_ability_stat_stage_and_item_event() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input.update({
        "current_field_state_confirmation": _field(),
        "current_condition_confirmations": [{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"}],
        "current_ability_confirmations": [{"side": "self", "ability": "intimidate", "status": "user_confirmed", "source": "user_confirmed_current_ability"}],
        "current_stat_stage_confirmations": [{"side": "self", "stat": "speed", "stage": 2, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}],
        "item_event_confirmations": [{"side": "opponent", "item": "focus-sash", "event_type": "item_activation_observed", "status": "user_confirmed", "source": "explicit_user_event_confirmation", "turn": None, "note": None}],
    })
    entries = advisor_client.build_ui_selected_trusted_context_entries(battle_input, enable_battle_state_context=True)
    assert {entry[0] for entry in entries} == {"current_condition", "current_ability", "current_stat_stage", "current_weather", "current_terrain", "current_global_field_effect", "current_side_field_effect", "observed_item_event"}
    response = (
        "[Trusted Context]\n- Current condition | self | burn\n- Current ability | self | intimidate\n"
        "- Current stat stage | self | speed | +2\n- Current weather | rain\n- Current terrain | none\n"
        "- Current global field effect | trick-room\n- Current side field effect | self | reflect\n"
        "- Current side field effect | opponent | tailwind\n- Observed item event | opponent | focus-sash | item_activation_observed\n\n"
        "[Advice]\nChoose conservatively; confirmed field identities and stages do not establish exact damage or turn order."
    )
    assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is None
    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries)[0] == "pass"
