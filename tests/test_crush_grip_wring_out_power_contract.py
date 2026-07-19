import pytest
from llm.advisor_battle_state_context import build_target_hp_based_power_assessment
@pytest.mark.parametrize("move",["crush-grip","wring-out"])
def test_formula_full_half_low_and_odd(move):
 def power(c,m):return build_target_hp_based_power_assessment({"move_id":move},{"current_hp":[{"side":"opponent","current_hp":c,"maximum_hp":m}]})["effective_power"]
 assert (power(100,100),power(50,100),power(1,300),power(81,161))==(121,61,1,61)
