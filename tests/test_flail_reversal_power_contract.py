import pytest
from llm.advisor_battle_state_context import build_current_hp_based_power_assessment
def _power(move,hp): return build_current_hp_based_power_assessment({"move_id":move},{"current_hp":[{"side":"self","current_hp":hp,"maximum_hp":100}]})["effective_power"]
@pytest.mark.parametrize("hp,power",[(100,20),(68,40),(35,80),(20,100),(10,150),(4,200)])
def test_flail_brackets(hp,power): assert _power("flail",hp)==power
def test_reversal_uses_same_brackets(): assert _power("reversal",20)==100
