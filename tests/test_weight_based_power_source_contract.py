from llm.advisor_battle_state_context import build_weight_based_power_assessment
def test_missing_weights_are_unavailable(): assert build_weight_based_power_assessment({"move_id":"heavy-slam"},None)["reason"]=="missing_self_weight"
