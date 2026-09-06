import pytest
from advisor.canonical_target_current_hp_power_family import resolve_canonical_target_current_hp_power_move
from llm.advisor_battle_state_context import build_target_hp_based_power_assessment
def _hp(current,maximum=100):return {"current_hp":[{"side":"opponent","current_hp":current,"maximum_hp":maximum}]}
def test_catalog_and_supported_moves():
 assert resolve_canonical_target_current_hp_power_move(move={"move_id":"hard-press"})["effect"]["type"]=="steel"
 assert resolve_canonical_target_current_hp_power_move(move={"move_id":"wring-out"})["effect"]["category"]=="special"
@pytest.mark.parametrize("move,current,power",[("hard-press",100,100),("hard-press",50,50),("hard-press",1,1),("crush-grip",100,121),("crush-grip",50,61),("wring-out",1,2)])
def test_exact_variants(move,current,power):assert build_target_hp_based_power_assessment({"move_id":move},_hp(current))["effective_power"]==power
def test_odd_ratio_uses_integer_floor():assert build_target_hp_based_power_assessment({"move_id":"hard-press"},_hp(1,3))["effective_power"]==33
