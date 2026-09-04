from copy import deepcopy
from llm.advisor_reducer_state_model import project_atomic_transition,state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_last_executed_move_authority import freeze_runtime_d0_last_executed_move_authority
from llm.advisor_detached_disable_action_restriction import materialize_detached_disable_application,resolve_disable_move_selectability
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_taunt_action_restriction import _taunt_inputs
from tests.test_runtime_d0_native_damage_context import _state

def _owner(s,side="self"):
 p=s[f"{side}_side"]["pokemon"][0];return {"session_id":s["session_id"],"side":side,"slot_index":0,"pokemon_id":p["pokemon_id"]}
def _plan(s,*x):return {"session_id":s["session_id"],"status":"planned","conflicts":[],"replay_policy_version":"v1","ordered_steps":list(x)}
def _step(i,n,e,o,**x):return {"observation_id":i,"observation_sequence":n,"planned_effect":e,"trust":"user_confirmed_observation",**o,**x}
def _snap(s):return {"status":"runtime_snapshot_ready","session_id":s["session_id"],"state":deepcopy(s),"state_fingerprint":state_fingerprint(s)}
def _history(s):
 o=_owner(s,"opponent");return project_atomic_transition(s,_plan(s,_step("used",1,"record_executed_move",o,turn_number=1,move_id="thunderbolt",source_action_id="opponent_attack:thunderbolt")),s["session_id"])["projected_state"]

def test_disable_lifecycle_is_four_turn_identity_bound():
 s=_history(_state("disable-life"));o=_owner(s,"opponent")
 cur=project_atomic_transition(s,_plan(s,_step("disable",2,"apply_disable_restriction",o,turn_number=1,source_action_id="attack:disable",source_move_id="disable",disabled_move_id="thunderbolt",last_used_execution_id="used")),s["session_id"])["projected_state"]
 for seq,turn,rem in ((3,2,3),(4,3,2),(5,4,1),(6,5,None)):
  cur=project_atomic_transition(cur,_plan(cur,_step(str(turn),seq,"complete_disable_restricted_active_turn",o,turn_number=turn,completion_kind="affected_active_turn_completed")),cur["session_id"])["projected_state"]
  assert cur["current_disable_restrictions"]["opponent"]["remaining_target_turns"]==rem
 assert cur["current_disable_restrictions"]["opponent"]["retired_reason"]=="expired"

def test_disable_application_selectability_and_champions_no_pp_rule():
 s=_history(_state("disable-app"));snap=_snap(s);d=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s));actor,target=_owner(s),_owner(s,"opponent");last=freeze_runtime_d0_last_executed_move_authority(strategy_d0=d,runtime_snapshot=snap,owner=target)
 b={"session_id":d["session_id"],"source_runtime_fingerprint":d["source_runtime_fingerprint"],"source_branch_fingerprint":d["strategy_preview_fingerprint"],"decision_owner":d["decision_owner"]}; known=lambda **x:{"status":"resolved",**b,"actor":actor,"target":target,"action_id":"attack:disable","move_id":"disable",**x}; owner_bound=lambda **x:{"status":"resolved",**b,"owner":target,**x}
 action={"action_id":"attack:disable","identity":"disable","metadata_authority":{"metadata":{"move_id":"disable","category":"status","type":"normal","accuracy":100,"priority":0}}}
 app=materialize_detached_disable_application(strategy_d0=d,action=action,actor=actor,target=target,accuracy_authority=known(outcome="hit"),last_used_move_authority=last,current_known_moves_authority=owner_bound(move_ids=["thunderbolt"],moveset_completeness="complete"),current_disable_authority=owner_bound(state="not_active"),target_side_ability_authority=known(ability="none"),protection_authority=known(outcome="not_applicable"),reflection_authority=known(outcome="not_applicable"))
 assert app["outcome"]=="applicable" and app["remaining_target_turns"]==4
 authority=owner_bound(state="active",disabled_move_id="thunderbolt")
 assert resolve_disable_move_selectability(disable_authority=authority,owner=target,move_metadata_authority={"metadata":{"move_id":"thunderbolt"}})["selectability"]=="not_selectable"
 assert resolve_disable_move_selectability(disable_authority=authority,owner=target,move_metadata_authority={"metadata":{"move_id":"tackle"}})["selectability"]=="selectable"

def test_disable_first_restricts_pending_selected_move_without_damage(monkeypatch):
 snap,d,own,foe,own_action,opponent,order,_,pure=_taunt_inputs(category="physical")
 own_action={**own_action,"action_id":"attack:disable","identity":"disable","move_metadata_authority":{**own_action["move_metadata_authority"],"candidate_id":"attack:disable","move_id":"disable","metadata":{"move_id":"disable","category":"status","type":"normal","accuracy":100,"priority":0}}};order={**order,"own_action_id":"attack:disable"}
 app={"status":"resolved","session_id":d["session_id"],"source_runtime_fingerprint":d["source_runtime_fingerprint"],"source_branch_fingerprint":d["strategy_preview_fingerprint"],"decision_owner":d["decision_owner"],"actor":own,"target":foe,"action_id":"attack:disable","move_id":"disable","outcome":"applicable","disabled_move_id":"tackle","last_used_execution_id":"used"}
 monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger",lambda **_: {"status":"evaluable","terminal_leaves":()})
 pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d,runtime_snapshot=snap,own_action=own_action,opponent_action=opponent,action_order_authority=order,disable_application_authorities={"attack:disable":app},pure_status_execution_authorities=pure)
 leaf=pair["terminal_branches"][0]["second_action"]["leaf"]
 assert leaf["consequences"]["execution_failure"]=="disable_action_restriction" and leaf["hit_state"]==leaf["critical_state"]==leaf["damage_roll"]=="not_applicable"
 assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"]=="evaluable"
