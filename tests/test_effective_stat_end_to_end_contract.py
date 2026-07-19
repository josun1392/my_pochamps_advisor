from __future__ import annotations

import json
from copy import deepcopy

import llm.advisor_client as advisor_client
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


def _entry(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}


def _stage(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "stage": value, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}


def test_production_prompt_keeps_trusted_inputs_and_stage_only_results_separate() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_final_stat_confirmations"] = [_entry("self", "speed", 167), _entry("opponent", "speed", 201)]
    battle_input["current_stat_stage_confirmations"] = [_stage("self", "speed", 2), _stage("opponent", "speed", 0)]
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    results = advisor_client.build_ui_selected_deterministic_result_entries(battle_input, enable_battle_state_context=True)
    trusted = advisor_client.build_ui_selected_trusted_context_entries(battle_input, enable_battle_state_context=True)
    assert payload["deterministic_calculation_context"]["speed_comparison"]["result"] == "self_faster"
    assert ("effective_stat", "self", "speed", "334", "final-stat-plus-stage") in results
    response = """[Trusted Context]
- Current stat stage | self | speed | +2
- Current stat stage | opponent | speed | 0
- Current final stat | opponent | speed | 201
- Current final stat | self | speed | 167

[Deterministic Results]
- Effective stat | self | speed | 334 | final-stat-plus-stage
- Effective stat | opponent | speed | 201 | final-stat-plus-stage
- Speed comparison | self-faster | stage-only
- Hit chance | self | opponent | flamethrower | 100% | calculated-100-percent | move-accuracy-and-stages-only

[Advice]
Self is faster by stage-adjusted Speed only; final move order remains unresolved."""
    assert advisor_client.evaluate_deterministic_result_response(response, trusted, results) is None
    assert advisor_client.evaluate_deterministic_result_response(response.replace("334", "333"), trusted, results) == "deterministic-results entry mismatch"
    assert advisor_client.evaluate_deterministic_result_response(response.replace("remains unresolved", "will move first"), trusted, results) == "deterministic-results semantic boundary violation"
    off_payload = json.loads(advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=False).rsplit("\n\n", 1)[1])
    assert "deterministic_calculation_context" not in off_payload


def test_field_and_speed_ability_context_do_not_modify_stage_only_result() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_final_stat_confirmations"] = [_entry("self", "speed", 167), _entry("opponent", "speed", 201)]
    battle_input["current_stat_stage_confirmations"] = [_stage("self", "speed", 2)]
    battle_input["current_ability_confirmations"] = [{"side": "self", "ability": "swift-swim", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]
    battle_input["current_field_state_confirmation"] = {"weather": "rain", "terrain": "none", "global_effects": ["trick-room"], "side_effects": [{"side": "self", "effect": "tailwind"}], "status": "user_confirmed", "source": "user_confirmed_current_field_state"}
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    result = payload["deterministic_calculation_context"]
    assert result["speed_comparison"] == {"calculation_scope": "stage_only", "calculation_status": "resolved", "result": "self_faster", "self_effective_speed": 334, "opponent_effective_speed": 201}
    assert result["excluded_modifiers"] == ["priority", "item", "ability", "weather", "terrain", "tailwind", "trick-room", "rng"]
    assert "do not apply or claim priority, item, ability, weather, terrain, Tailwind, Trick Room, or RNG modifiers" in prompt
