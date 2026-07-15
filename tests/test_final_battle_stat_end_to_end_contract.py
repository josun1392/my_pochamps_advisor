from __future__ import annotations

import json
from copy import deepcopy

import llm.advisor_client as advisor_client
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


def test_final_stat_payload_prompt_acknowledgement_and_gate() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_final_stat_confirmations"] = [{"side": "self", "stat": "hp", "value": 301, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}, {"side": "self", "stat": "attack", "value": 205, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}]
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    entries = advisor_client.build_trusted_context_acknowledgement_entries(payload)
    assert payload["final_stat_context"]["current_final_stats"][0]["confidence"] == "known"
    assert ("current_final_stat", "self", "attack", "205") in entries
    assert "Current final stat | self | attack | 205" in prompt
    response = "[Trusted Context]\n- Current final stat | self | attack | 205\n- Current final stat | self | hp | 301\n\n[Advice]\nUse the confirmed final stats without applying stages or claiming exact damage."
    assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is None
    off_prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=False)
    assert "final_stat_context" not in json.loads(off_prompt.rsplit("\n\n", 1)[1])
