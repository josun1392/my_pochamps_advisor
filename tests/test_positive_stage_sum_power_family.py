import pytest
from advisor.canonical_positive_stage_sum_power_family import resolve_canonical_positive_stage_sum_power_move
from llm.advisor_battle_state_context import build_positive_stage_sum_power_assessment
_STATS=("attack","defense","special-attack","special-defense","speed","accuracy","evasion")
def _context(**stages): return {"current_stages":[{"side":"self","stat":stat,"stage":stages.get(stat,0)} for stat in _STATS]}
def test_catalog_contact_and_categories():
 assert resolve_canonical_positive_stage_sum_power_move(move={"move_id":"stored-power"})["effect"]["contact"] is False
 assert resolve_canonical_positive_stage_sum_power_move(move={"move_id":"power-trip"})["effect"]["category"]=="physical"
@pytest.mark.parametrize("stages,power",[({},20),({"attack":1},40),({"attack":6},140),({"attack":2,"special-attack":1,"speed":3},140),({"attack":3,"defense":-2},80),({stat:6 for stat in _STATS},860)])
def test_exact_positive_sum(stages,power): assert build_positive_stage_sum_power_assessment({"move_id":"stored-power"},_context(**stages))["effective_power"]==power
def test_missing_stage_is_not_neutral():
 context=_context(); context["current_stages"].pop()
 assert build_positive_stage_sum_power_assessment({"move_id":"power-trip"},context)["status"]=="unavailable"
