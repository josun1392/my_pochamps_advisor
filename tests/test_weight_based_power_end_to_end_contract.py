from llm.advisor_battle_state_context import build_weight_based_power_assessment
def test_weight_unit_is_canonical_hectogram(): assert build_weight_based_power_assessment({"move_id":"grass-knot"},{"opponent_weight":100})["weight_unit"]=="hectogram"
