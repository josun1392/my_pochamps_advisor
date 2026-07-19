from llm.advisor_battle_state_context import build_battle_counter_power_assessment


def test_rage_fist_zero_and_intermediate_hits():
    assert build_battle_counter_power_assessment({"move_id": "rage-fist"}, {"rage_fist_hits_received": 0})["effective_power"] == 50
    assert build_battle_counter_power_assessment({"move_id": "rage-fist"}, {"rage_fist_hits_received": 3})["effective_power"] == 200


def test_rage_fist_power_is_capped_at_350():
    assert build_battle_counter_power_assessment({"move_id": "rage-fist"}, {"rage_fist_hits_received": 6})["effective_power"] == 350
    assert build_battle_counter_power_assessment({"move_id": "rage-fist"}, {"rage_fist_hits_received": 99})["effective_power"] == 350
