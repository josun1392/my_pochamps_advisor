from llm.advisor_battle_state_context import build_consecutive_use_power_assessment


def test_echoed_voice_adds_40_per_confirmed_stage_and_caps():
    helper = lambda count: build_consecutive_use_power_assessment({"move_id": "echoed-voice"}, {"echoed_voice_consecutive_uses": count})["effective_power"]
    assert [helper(count) for count in (1, 3, 5, 9)] == [40, 120, 200, 200]
