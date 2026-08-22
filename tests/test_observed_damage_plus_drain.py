from copy import deepcopy
from llm.advisor_observed_damage_plus_drain import materialize_observed_giga_drain
from llm.advisor_observed_damage_application import apply_exact_observed_drain_consequence
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from tests.test_forced_switch_execution import _owner,_state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _pre
def _o(s,side="self",target="opponent",damage=20,kind="heal",amount=10,result="applied",**x):
 u,t=_owner(s,side),_owner(s,target); v={"schema_version":"observed-damage-plus-drain-result-v1","session_id":u["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(s),"user":u,"target_owner":t,"move_id":"giga-drain","damage_amount":damage,"damaging_hit_result":"applied","drain_result":result,"drain_consequence":kind if result=="applied" else None,"drain_amount":amount if result=="applied" else None,"provenance":"trusted_observed_damage_plus_drain_result_v1"};v.update(x);return v
def _m(s,o=None):return materialize_observed_giga_drain(branch_state=s,source_branch_fingerprint=fingerprint_transition_preview_state(s),observed_result=_o(s) if o is None else o)
def test_giga_drain_side_neutral_cap_damage_and_replay():
 s,_=_state();s["active"]["self"]["current_hp"]=95;b=deepcopy(s);r=_m(s);assert s==b and r["next_state"]["active"]["opponent"]["current_hp"]==80 and r["next_state"]["active"]["self"]["current_hp"]==100
 assert _m(s,_o(s,side="opponent",target="self"))["next_state"]["active"]["opponent"]["current_hp"]==100
 assert materialize_observed_giga_drain(branch_state=r["next_state"],source_branch_fingerprint=r["resulting_branch_fingerprint"],observed_result=_o(s))["status"]=="rejected"
def test_giga_drain_target_ko_liquid_ooze_outcome_and_fail_closed():
 s,_=_state();r=_m(s,_o(s,damage=100,amount=10));assert r["next_state"]["active"]["opponent"]["fainted"] and r["next_state"]["active"]["self"]["current_hp"]==100
 assert apply_exact_observed_drain_consequence(branch_state=r["next_state"],source_branch_fingerprint=r["resulting_branch_fingerprint"],drain_authority=r["drain_authority"])["status"]=="rejected"
 s,_=_state();s["active"]["self"]["current_hp"]=10;r=_m(s,_o(s,kind="self_damage",amount=10));assert r["next_state"]["active"]["self"]["fainted"]
 s,_=_state();s["active"]["self"]["current_hp"]=None;assert _m(s)["status"]=="rejected"
 s,_=_state();assert _m(s,_o(s,result="unknown"))["status"]=="rejected"
def test_drain_evidence_is_stale_after_eot_handoff_and_fresh_turn_two_resolves():
 p=_pre(self_hp=50,self_item=None,self_condition="none");_ingrain(p["next_state"],self_state="unknown");f0=apply_successful_ingrain(branch_state=p["next_state"],source_branch_fingerprint=fingerprint_transition_preview_state(p["next_state"]),action_effect=_effect(p["next_state"]))["next_state"]
 o=_o(f0);r=_m(f0,o);e=project_per_owner_end_of_turn(pre_end_of_turn={"status":"resolved","next_state":r["next_state"],"boundary":{"phase":"pre_end_of_turn"}},owner=_owner(r["next_state"],"self"));fp=e["resulting_branch_fingerprint"]
 assert materialize_observed_giga_drain(branch_state=e["next_state"],source_branch_fingerprint=fp,observed_result=o)["status"]=="rejected"
 t=handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=e)["next_state"];assert materialize_observed_giga_drain(branch_state=t,source_branch_fingerprint=fingerprint_transition_preview_state(t),observed_result=o)["status"]=="rejected" and _m(t)["status"]=="resolved"
