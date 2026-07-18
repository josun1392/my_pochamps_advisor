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
