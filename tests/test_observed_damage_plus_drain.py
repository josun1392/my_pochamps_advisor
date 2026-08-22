from copy import deepcopy
from llm.advisor_observed_damage_plus_drain import materialize_observed_giga_drain
from llm.advisor_observed_damage_application import apply_exact_observed_drain_consequence
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _owner,_state
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
