from advisor.canonical_user_held_item_absence_power import resolve_canonical_user_held_item_absence_power_move
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result
def test_catalog():assert resolve_canonical_user_held_item_absence_power_move(move={"move_id":"acrobatics"})["effect"]["boosted_power"]==110
def test_exact_item_states_choose_power_or_fail_closed():
 absent=_modifier_result(move_id="acrobatics",move_type="flying",power=55,item="none")
 present=_modifier_result(move_id="acrobatics",move_type="flying",power=55,item="muscle-band")
 unknown=_modifier_result(move_id="acrobatics",move_type="flying",power=55,item="unknown")
 assert absent["dynamic_power_evidence"]["effective_power"]==110
 assert present["dynamic_power_evidence"]["effective_power"]==55
 assert unknown["status"]=="insufficient_context"
