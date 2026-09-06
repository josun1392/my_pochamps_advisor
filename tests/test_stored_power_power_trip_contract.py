import pytest
from llm.advisor_battle_state_context import build_positive_stage_sum_power_assessment
@pytest.mark.parametrize("move",["stored-power","power-trip"])
def test_positive_stages_only(move):
 r=build_positive_stage_sum_power_assessment({"move_id":move},{"current_stages":[{"side":"self","stat":stat,"stage":{"attack":2,"speed":1,"defense":-2}.get(stat,0)} for stat in ("attack","defense","special-attack","special-defense","speed","accuracy","evasion")]})
 assert r["effective_power"]==80
