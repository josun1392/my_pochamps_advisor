from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY


def test_registered_moves_have_the_expected_families():
    assert DYNAMIC_MOVE_ASSESSMENT_REGISTRY["eruption"] == "current_hp_based_power"
    assert DYNAMIC_MOVE_ASSESSMENT_REGISTRY["electro-ball"] == "speed_based_power"
    assert DYNAMIC_MOVE_ASSESSMENT_REGISTRY["fury-cutter"] == "consecutive_use_power"


def test_ordinary_move_is_not_registered():
    assert "tackle" not in DYNAMIC_MOVE_ASSESSMENT_REGISTRY
