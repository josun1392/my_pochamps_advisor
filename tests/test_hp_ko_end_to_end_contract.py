from __future__ import annotations

import json

import llm.advisor_client as advisor_client


def _final(side: str, stat: str, value: int) -> dict[str, object]: return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}


def test_hp_assessment_payload_acknowledgement_and_gate() -> None:
    battle_input = {"moves": {"my_selected_move": {"move_id": "tackle", "category": "physical", "power": 80}}, "current_final_stat_confirmations": [_final("self", "attack", 200), _final("opponent", "defense", 150)], "current_hp_confirmations": [{"side": "opponent", "current_hp": 90, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True); payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    trusted, results = advisor_client.build_ui_selected_trusted_context_entries(battle_input, enable_battle_state_context=True), advisor_client.build_ui_selected_deterministic_result_entries(battle_input, enable_battle_state_context=True)
    assert payload["deterministic_calculation_context"]["hp_assessments"]
    assert ("damage_percentage", "self", "opponent", "tackle", "13.3-16.0", "base-damage-stage-only") in results
    assert any(entry[0] == "current_hp" and entry[2] == "90" and entry[3] == "300" for entry in trusted)
    assert "current_hp_context" not in json.loads(advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=False).rsplit("\n\n", 1)[1])


def test_zero_hp_keeps_trusted_hp_and_percentage_but_omits_ko_result_lines() -> None:
    battle_input = {"moves": {"my_selected_move": {"move_id": "tackle", "category": "physical", "power": 80}}, "current_final_stat_confirmations": [_final("self", "attack", 200), _final("opponent", "defense", 150)], "current_hp_confirmations": [{"side": "opponent", "current_hp": 0, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1]); trusted = advisor_client.build_ui_selected_trusted_context_entries(battle_input, enable_battle_state_context=True); results = advisor_client.build_ui_selected_deterministic_result_entries(battle_input, enable_battle_state_context=True)
    assessment = payload["deterministic_calculation_context"]["hp_assessments"][0]
    assert assessment["assessment_status"] == "not_applicable" and assessment["reason"] == "target_already_fainted"
    assert any(entry[0] == "current_hp" and entry[2:] == ("0", "300") for entry in trusted)
    assert any(entry[0] == "damage_percentage" for entry in results)
    assert not any(entry[0] in {"ohko_assessment", "two_hit_ko_assessment"} for entry in results)
    trusted_lines = "\n".join(f"- Current final stat | {side} | {stat} | {value}" if category == "current_final_stat" else f"- Current HP | {side} | {stat} | maximum {value}" for category, side, stat, value in trusted)
    result_lines = "\n".join(f"- Effective stat | {entry[1]} | {entry[2]} | {entry[3]} | {entry[4]}" if entry[0] == "effective_stat" else f"- Damage estimate | {entry[1]} | {entry[2]} | {entry[3]} | {entry[4]} | {entry[5]}" if entry[0] == "damage_estimate" else f"- Damage percentage | {entry[1]} | {entry[2]} | {entry[3]} | {entry[4]} | {entry[5]}" for entry in results)
    response = f"[Trusted Context]\n{trusted_lines}\n\n[Deterministic Results]\n{result_lines}\n\n[Advice]\nThe target is already fainted, so further KO assessment is not applicable."
    assert advisor_client.evaluate_deterministic_result_response(response, trusted, results) is None
    assert advisor_client.evaluate_deterministic_result_response(response.replace("not applicable", "guaranteed OHKO"), trusted, results) == "deterministic-results semantic boundary violation"
