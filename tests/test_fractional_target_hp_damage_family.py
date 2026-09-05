from advisor.canonical_fractional_target_hp_damage_family import resolve_canonical_fractional_target_hp_damage_move
from llm.advisor_detached_fractional_target_hp_damage import materialize_detached_fractional_target_hp_damage
from llm.advisor_detached_fractional_target_hp_damage_attack_leaf import materialize_detached_fractional_target_hp_damage_attack_leaves
from llm.advisor_runtime_d0_special_damage_execution_authority import freeze_runtime_d0_fractional_target_hp_damage_execution_authority
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_strict_hit_probability_assessment, freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from copy import deepcopy
from tests.test_detached_opponent_response_profile import _complete_state, _fixed_damage_inputs, _owner, _state
def _hp(n):return {"current_hp":n,"max_hp":100,"fainted":n==0}
def test_catalog_and_half_minimum():
 assert resolve_canonical_fractional_target_hp_damage_move(move={"move_id":"super-fang","type":"normal","category":"physical","accuracy":90,"contact":True})["status"]=="resolved"
 assert [materialize_detached_fractional_target_hp_damage(move={"move_id":"super-fang","type":"normal","category":"physical","accuracy":90,"contact":True},target_hp=_hp(h),hit_state="hit",applicability="applicable")["damage"] for h in (100,99,2,1)]==[50,49,1,1]
def test_miss_and_immunity_no_damage():
 move={"move_id":"super-fang","type":"normal","category":"physical","accuracy":90,"contact":True}
 assert materialize_detached_fractional_target_hp_damage(move=move,target_hp=_hp(60),hit_state="missed",applicability="applicable")["damage"]==0
 assert materialize_detached_fractional_target_hp_damage(move=move,target_hp=_hp(60),hit_state="hit",applicability="immune")["damage"]==0

def _execution(hp=100, move_id="super-fang", types=("normal",)):
 state=_complete_state(_state()); state["opponent_side"]["pokemon"][0]["current_hp"]=hp; state["opponent_side"]["pokemon"][0]["fainted"]=hp==0; state["opponent_side"]["pokemon"][0]["current_type"]=list(types)
 snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}; d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state,"self")); move={"move_id":move_id,"type":{"super-fang":"normal","natures-madness":"fairy","ruination":"dark"}[move_id],"category":"physical" if move_id=="super-fang" else "special","accuracy":90,"contact":move_id=="super-fang"}
 authority=freeze_runtime_d0_fractional_target_hp_damage_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state,"self"),target=_owner(state,"opponent"),move_metadata=move)
 hit=build_runtime_d0_strict_hit_probability_assessment(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state,"self"),target=_owner(state,"opponent"),selected_move=move)
 return d0,authority,hit

def test_execution_envelope_branches_accuracy_and_preserves_no_crit_or_roll():
 d0,authority,hit=_execution(99); leaves=materialize_detached_fractional_target_hp_damage_attack_leaves(strategy_d0=d0,execution_authority=authority,strict_hit_probability=hit)
 assert leaves["status"]=="evaluable" and leaves["terminal_probability_mass"]=={"numerator":1,"denominator":1}
 rows={row["hit_state"]:row for row in leaves["terminal_leaves"]}; assert rows["hit"]["consequences"]["damage"]==49 and rows["miss"]["consequences"]["damage"]==0
 assert all(row["critical_state"]=="not_applicable" and row["damage_roll"]=="not_applicable" for row in rows.values())

def test_execution_envelope_uses_immunity_without_effectiveness_scaling_and_rejects_forgery():
 d0,authority,hit=_execution(100,types=("ghost",)); leaves=materialize_detached_fractional_target_hp_damage_attack_leaves(strategy_d0=d0,execution_authority=authority,strict_hit_probability=hit)
 assert {row["consequences"]["damage"] for row in leaves["terminal_leaves"]}=={0}
 d0,authority,hit=_execution(2); forged={**authority,"execution_target_hp":100}; assert materialize_detached_fractional_target_hp_damage_attack_leaves(strategy_d0=d0,execution_authority=forged,strict_hit_probability=hit)["status"]=="rejected"

def test_immediate_pair_dispatches_fractional_family_without_changing_seismic_path():
 _,snapshot,d0,own,opponent,order=_fixed_damage_inputs(own_first=True,opponent_hp=100)
 move={"move_id":"super-fang","type":"normal","category":"physical","accuracy":90,"contact":True}
 own={"action_id":"attack:super-fang","action_type":"attack","identity":"super-fang","move_metadata_authority":{"status":"resolved","candidate_id":"attack:super-fang","active_attacker":d0["decision_owner"],"move_id":"super-fang","metadata":move,"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":d0["decision_owner"]}}
 order={**order,"own_action_id":"attack:super-fang"}; pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=order)
 assert pair["status"]=="evaluable" and {row["first_action_leaf"]["consequences"]["damage"] for row in pair["terminal_branches"]}=={0,50} and normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"]=="evaluable"
 forged=deepcopy(pair); forged["terminal_branches"][0]["first_action_leaf"]["consequences"]["fractional_target_hp_damage"]["derived_damage"]=999
 assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"]=="rejected"
