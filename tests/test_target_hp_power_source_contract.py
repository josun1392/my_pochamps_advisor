import pytest
from llm.advisor_battle_state_context import build_target_hp_based_power_assessment
def _hp(current=None, maximum=None):
 e={"side":"opponent"}
 if current is not None:e["current_hp"]=current
 if maximum is not None:e["maximum_hp"]=maximum
 return {"current_hp":[e]}
def test_missing_and_fainted_boundaries():
 assert build_target_hp_based_power_assessment({"move_id":"crush-grip"},None)["reason"]=="missing_opponent_current_hp"
 assert build_target_hp_based_power_assessment({"move_id":"crush-grip"},_hp(0,100))["reason"]=="opponent_already_fainted"
@pytest.mark.parametrize("current,maximum",[(True,100),(101,100),(-1,100),(1,0)])
def test_invalid_hp(current,maximum): assert build_target_hp_based_power_assessment({"move_id":"crush-grip"},_hp(current,maximum))["reason"]=="invalid_opponent_hp_context"
