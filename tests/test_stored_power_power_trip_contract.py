import pytest
from llm.advisor_battle_state_context import build_stat_stage_based_power_assessment
@pytest.mark.parametrize("move",["stored-power","power-trip"])
def test_positive_stages_only(move):
 r=build_stat_stage_based_power_assessment({"move_id":move},{"current_stages":[{"side":"self","stat":"attack","stage":2},{"side":"self","stat":"speed","stage":1},{"side":"self","stat":"defense","stage":-2}]})
 assert r["effective_power"]==80
