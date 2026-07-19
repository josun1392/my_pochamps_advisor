from llm.advisor_battle_state_context import build_consecutive_use_power_assessment


def test_missing_and_invalid_chain_counts_are_unavailable():
    assert build_consecutive_use_power_assessment({"move_id": "fury-cutter"}, None)["reason"] == "missing_fury_cutter_consecutive_uses"
    for value in (0, -1, True, 1.0, "1"):
        assert build_consecutive_use_power_assessment({"move_id": "fury-cutter"}, {"fury_cutter_consecutive_uses": value})["reason"] == "invalid_consecutive_use_count"


def test_unconfirmed_chain_is_unavailable():
    assert build_consecutive_use_power_assessment({"move_id": "echoed-voice"}, {"echoed_voice_consecutive_uses": 1, "chain_confirmed": False})["reason"] == "unconfirmed_consecutive_chain"
