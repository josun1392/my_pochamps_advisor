from copy import deepcopy
import pytest

from advisor.canonical_target_already_acted_power_family import resolve_canonical_target_already_acted_power_move
from llm.advisor_detached_target_already_acted_power_authority import materialize_detached_target_already_acted_power_authority
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order

def _move(): return {"move_id":"payback","type":"dark","category":"physical","power":50,"accuracy":100,"priority":0,"contact":True}
def _d0():
 _state,snapshot,d0,_own,_responses,_orders=_inputs(own_move="tackle"); return snapshot,d0
def _leaf(d0, *, action_type="attack", hit_state="hit", move="tackle", foreign=False):
 attacker=deepcopy(d0["active_owners"]["opponent"])
 if foreign:attacker["pokemon_id"]="foreign"
 return {"leaf_id":"prior","candidate_id":"opponent_attack:"+move,"action_type":action_type,"hit_state":hit_state,"provenance":{"attacker":attacker,"target":deepcopy(d0["active_owners"]["self"]),"move_id":move}}
def _authority(d0,leaf=None,selected=None):return materialize_detached_target_already_acted_power_authority(strategy_d0=d0,move=_move(),user=d0["active_owners"]["self"],target=d0["active_owners"]["opponent"],source_terminal_leaf=leaf,source_selected_action=selected,execution_order_provenance={"order":"opponent_first"})

def test_catalog_and_absent_prior_action_are_unboosted():
 assert resolve_canonical_target_already_acted_power_move(move=_move())["effect"]["boosted_power"]==100
 assert resolve_canonical_target_already_acted_power_move(move={"move_id":"tackle"})["status"]=="unsupported"
 _snapshot,d0=_d0(); assert _authority(d0)["selected_base_power"]==50

@pytest.mark.parametrize(("action_type","hit_state"),(("attack","hit"),("attack","miss"),("attack","immune"),("protection","not_applicable"),("status","not_applicable")))
def test_completed_damaging_miss_or_non_damaging_target_actions_boost(action_type,hit_state):
 _snapshot,d0=_d0(); authority=_authority(d0,_leaf(d0,action_type=action_type,hit_state=hit_state,move="protect" if action_type=="protection" else "tail-whip" if action_type=="status" else "tackle"))
 assert authority["selected_base_power"]==100

def test_foreign_or_cancelled_non_leaf_does_not_boost_and_encore_binding_is_preserved():
 _snapshot,d0=_d0(); assert _authority(d0,_leaf(d0,foreign=True))["selected_base_power"]==50
 authority=_authority(d0,_leaf(d0,move="forced"),{"action_id":"opponent_attack:selected","identity":"selected"})
 action=authority["qualifying_target_action"]
 assert action["source_selected_move_id"]=="selected" and action["source_execution_move_id"]=="forced"

def test_pair_uses_50_before_target_action_and_100_after_target_action():
 _state,snapshot,d0,own,responses,_orders=_inputs(own_move="tackle")
 own={**own,"action_id":"attack:payback","identity":"payback"}; own["move_metadata_authority"]={**own["move_metadata_authority"],"candidate_id":"attack:payback","move_id":"payback","metadata":_move()}
 opponent=next(row for row in responses["actions"] if row["action_id"]=="opponent_attack:tackle")
 first=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=_order(d0,own,opponent,"own_first"))
 second=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=_order(d0,own,opponent,"opponent_first"))
 assert first["status"]==second["status"]=="evaluable"
 assert all(row["first_action_leaf"]["provenance"]["target_already_acted_power_authority"]["selected_base_power"]==50 for row in first["terminal_branches"])
 rows=[row["second_action"]["leaf"] for row in second["terminal_branches"] if row["second_action"]["state"]=="executed"]
 assert rows and all(row["provenance"]["target_already_acted_power_authority"]["selected_base_power"]==100 for row in rows)
 assert normalize_exact_immediate_action_pair_outcome_ledger(pair=second)["status"]=="evaluable"
 forged=deepcopy(second); forged["terminal_branches"][0]["second_action"]["leaf"]["provenance"]["target_already_acted_power_authority"]["selected_base_power"]=50
 assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"]=="rejected"
