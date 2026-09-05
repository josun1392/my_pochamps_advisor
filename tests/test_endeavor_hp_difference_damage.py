from copy import deepcopy

from advisor.canonical_endeavor_hp_difference_damage_family import resolve_canonical_endeavor_hp_difference_damage_move
from llm.advisor_detached_endeavor_hp_difference_damage import materialize_detached_endeavor_hp_difference_damage
from llm.advisor_detached_endeavor_hp_difference_damage_attack_leaf import materialize_detached_endeavor_hp_difference_damage_attack_leaves
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_special_damage_execution_authority import freeze_runtime_d0_endeavor_hp_difference_damage_execution_authority
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_strict_hit_probability_assessment, freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context
from tests.test_detached_opponent_response_profile import _complete_state, _fixed_damage_inputs, _owner, _state

MOVE={"move_id":"endeavor","type":"normal","category":"physical","accuracy":100,"contact":True}
def _hp(value): return {"current_hp":value,"max_hp":100,"fainted":value==0}
def test_catalog_and_arithmetic_contract():
 assert resolve_canonical_endeavor_hp_difference_damage_move(move=MOVE)["effect"]["family"]=="hp_difference_damage"
 assert resolve_canonical_endeavor_hp_difference_damage_move(move={"move_id":"tackle"})["status"]=="unsupported"
 assert [(materialize_detached_endeavor_hp_difference_damage(move=MOVE,attacker_hp=_hp(a),target_hp=_hp(t),hit_state="hit",applicability="applicable")["damage"],materialize_detached_endeavor_hp_difference_damage(move=MOVE,attacker_hp=_hp(a),target_hp=_hp(t),hit_state="hit",applicability="applicable")["target_post_hp"]) for a,t in ((1,100),(30,100),(49,50))]==[(99,1),(70,30),(1,49)]
 assert materialize_detached_endeavor_hp_difference_damage(move=MOVE,attacker_hp=_hp(50),target_hp=_hp(50),hit_state="hit",applicability="applicable")["reason"]=="endeavor_target_hp_not_above_attacker_hp"

def _execution(attacker=30,target=100,types=("normal",)):
 state=_complete_state(_state()); state["self_side"]["pokemon"][0].update(current_hp=attacker,fainted=False); state["opponent_side"]["pokemon"][0].update(current_hp=target,fainted=False,current_type=list(types))
 snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}; d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state,"self")); authority=freeze_runtime_d0_endeavor_hp_difference_damage_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state,"self"),target=_owner(state,"opponent"),move_metadata=MOVE); hit=build_runtime_d0_strict_hit_probability_assessment(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state,"self"),target=_owner(state,"opponent"),selected_move=MOVE); return d0,snapshot,authority,hit

def test_execution_envelope_binds_both_hp_and_handles_failure_immunity():
 d0,_,authority,hit=_execution(); leaves=materialize_detached_endeavor_hp_difference_damage_attack_leaves(strategy_d0=d0,execution_authority=authority,strict_hit_probability=hit); leaf=leaves["terminal_leaves"][0]
 assert leaf["consequences"]["damage"]==70 and leaf["consequences"]["target_final_hp"]==30 and leaf["critical_state"]==leaf["damage_roll"]=="not_applicable"
 d0,_,authority,hit=_execution(80,50); assert materialize_detached_endeavor_hp_difference_damage_attack_leaves(strategy_d0=d0,execution_authority=authority,strict_hit_probability=hit)["terminal_leaves"][0]["consequences"]["damage"]==0
 d0,_,authority,hit=_execution(1,100,("ghost",)); assert materialize_detached_endeavor_hp_difference_damage_attack_leaves(strategy_d0=d0,execution_authority=authority,strict_hit_probability=hit)["terminal_leaves"][0]["consequences"]["damage"]==0
 forged={**authority,"execution_attacker_hp":99}; assert materialize_detached_endeavor_hp_difference_damage_attack_leaves(strategy_d0=d0,execution_authority=forged,strict_hit_probability=hit)["status"]=="rejected"

def test_pair_dispatch_and_ledger_forgery_rejection():
 _,snapshot,d0,_,opponent,order=_fixed_damage_inputs(own_first=True,opponent_hp=100,own_hp=30); own={"action_id":"attack:endeavor","action_type":"attack","identity":"endeavor","move_metadata_authority":{"status":"resolved","candidate_id":"attack:endeavor","active_attacker":d0["decision_owner"],"move_id":"endeavor","metadata":MOVE,"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":d0["decision_owner"]}}; pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority={**order,"own_action_id":"attack:endeavor"})
 assert pair["status"]=="evaluable" and normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"]=="evaluable"
 forged=deepcopy(pair); forged["terminal_branches"][0]["first_action_leaf"]["consequences"]["endeavor_hp_difference_damage"]["derived_damage"]=1; assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"]=="rejected"

def test_endeavor_second_consumes_path_local_attacker_hp_after_first_damage():
 _,snapshot,d0,_,opponent,order=_fixed_damage_inputs(own_first=False,opponent_hp=100,own_hp=100); own={"action_id":"attack:endeavor","action_type":"attack","identity":"endeavor","move_metadata_authority":{"status":"resolved","candidate_id":"attack:endeavor","active_attacker":d0["decision_owner"],"move_id":"endeavor","metadata":MOVE,"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":d0["decision_owner"]}}; pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority={**order,"own_action_id":"attack:endeavor"})
 second=pair["terminal_branches"][0]["second_action"]["leaf"]; assert second["consequences"]["endeavor_hp_difference_damage"]["attacker_execution_hp"]==50 and second["consequences"]["target_final_hp"]==50

def test_active_substitute_fails_closed():
 state=_complete_state(_state()); target=_owner(state,"opponent"); state["substitute_state_context"]=update_substitute_state_context(context=state["substitute_state_context"],session_id=state["session_id"],owner=target,state="known_active",substitute_hp=25,provenance="test"); snap={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}; d0=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(state,"self")); assert freeze_runtime_d0_endeavor_hp_difference_damage_execution_authority(strategy_d0=d0,runtime_snapshot=snap,attacker=_owner(state,"self"),target=target,move_metadata=MOVE)["status"]=="incomplete"
