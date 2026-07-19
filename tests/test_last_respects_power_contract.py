from llm.advisor_battle_state_context import build_battle_counter_power_assessment


def test_last_respects_uses_confirmed_fainted_allies_only():
    result = build_battle_counter_power_assessment({"move_id": "last-respects"}, {"last_respects_fainted_allies": 2})
    assert result["effective_power"] == 150


def test_last_respects_enforces_legal_other_ally_bound():
    assert build_battle_counter_power_assessment({"move_id": "last-respects"}, {"last_respects_fainted_allies": 5})["effective_power"] == 300
    assert build_battle_counter_power_assessment({"move_id": "last-respects"}, {"last_respects_fainted_allies": 6})["reason"] == "invalid_battle_counter"
