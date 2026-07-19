from llm.advisor_battle_state_context import build_consecutive_use_power_assessment


def test_fury_cutter_doubles_from_first_stage_and_caps():
    helper = lambda count: build_consecutive_use_power_assessment({"move_id": "fury-cutter"}, {"fury_cutter_consecutive_uses": count})["effective_power"]
    assert [helper(count) for count in (1, 2, 3, 4)] == [40, 80, 160, 160]


def test_fury_cutter_above_cap_stays_capped():
    assert build_consecutive_use_power_assessment({"move_id": "fury-cutter"}, {"fury_cutter_consecutive_uses": 20})["effective_power"] == 160
