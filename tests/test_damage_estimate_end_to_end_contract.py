from __future__ import annotations

import json

import llm.advisor_client as advisor_client


def _final(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}


def test_damage_result_has_a_separate_exact_acknowledgement_and_is_gated() -> None:
    battle_input = {
        "moves": {"my_selected_move": {"move_id": "tackle", "category": "physical", "power": 80}},
        "current_final_stat_confirmations": [_final("self", "attack", 200), _final("opponent", "defense", 150)],
    }
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    trusted = advisor_client.build_ui_selected_trusted_context_entries(battle_input, enable_battle_state_context=True)
    results = advisor_client.build_ui_selected_deterministic_result_entries(battle_input, enable_battle_state_context=True)
    assert payload["deterministic_calculation_context"]["damage_estimates"][0]["min_damage"] == 40
    assert ("damage_estimate", "self", "opponent", "tackle", "40-48", "base-damage-stage-only") in results
    trusted_lines = "\n".join(f"- Current final stat | {side} | {stat} | {value}" for _, side, stat, value in trusted)
    result_lines = "\n".join(
        f"- Effective stat | {entry[1]} | {entry[2]} | {entry[3]} | {entry[4]}" if entry[0] == "effective_stat" else f"- Damage estimate | {entry[1]} | {entry[2]} | {entry[3]} | {entry[4]} | {entry[5]}"
        for entry in results
    )
    response = f"[Trusted Context]\n{trusted_lines}\n\n[Deterministic Results]\n{result_lines}\n\n[Advice]\nThe limited range is 40 to 48; actual damage remains unresolved."
    assert advisor_client.evaluate_deterministic_result_response(response, trusted, results) is None
    assert advisor_client.evaluate_deterministic_result_response(response.replace("40-48", "41-48"), trusted, results) == "deterministic-results entry mismatch"
    assert advisor_client.evaluate_deterministic_result_response(response.replace("remains unresolved", "includes STAB applied"), trusted, results) == "deterministic-results semantic boundary violation"
    off_payload = json.loads(advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=False).rsplit("\n\n", 1)[1])
    assert "deterministic_calculation_context" not in off_payload
