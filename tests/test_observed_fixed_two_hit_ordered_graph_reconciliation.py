from copy import deepcopy
from fractions import Fraction

from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
from llm.advisor_fixed_two_hit_observation_runtime_admission import admit_observed_fixed_two_hit_result
from llm.advisor_lifecycle_confirmation import EXECUTED_MOVE_SOURCE,USER_TRUST,LifecycleConfirmationBoundary
from llm.advisor_multi_hit_graph_reconciliation import retain_historical_fixed_two_hit_prediction,validate_historical_multi_hit_prediction,reconcile_observed_fixed_two_hit_graph
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _inputs,_sturdy,_focus_sash
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _state,_owner
from tests.test_runtime_d0_fixed_two_hit_multi_hit_execution_authority import _state as _runtime_state


_ARTIFACT_CACHE={}

def _artifact(*,move="double-hit",power=40,accuracy=100,target_hp=100,sturdy=False,sash=False,contact=False,target_ability="pressure",own_hp=None):
    key=(move,power,accuracy,target_hp,sturdy,sash,contact,target_ability,own_hp)
    if key in _ARTIFACT_CACHE:
        return deepcopy(_ARTIFACT_CACHE[key])
    if own_hp is None:
        state,snapshot,d0,action,execution,own,foe=_inputs(move_id=move,power=power,accuracy=accuracy,target_hp=target_hp,target_ability=target_ability)
    else:
        state=_state();state["self_side"]["pokemon"][0]["current_hp"]=own_hp;state["self_side"]["pokemon"][0]["max_hp"]=max(100,own_hp)
        target=state["opponent_side"]["pokemon"][0];target["current_hp"]=target_hp;target["max_hp"]=max(100,target_hp);target["current_ability"]=target_ability
        snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":deepcopy(state),"state_fingerprint":state_fingerprint(state)}
        own,foe=_owner(state,"self"),_owner(state,"opponent");d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=own)
        metadata={"move_id":move,"category":"physical","power":power,"type":"normal" if move=="double-hit" else "fighting","accuracy":accuracy,"priority":0,"min_hits":2,"max_hits":2}
        authority={"status":"resolved","schema_version":"runtime-d0-selectable-move-metadata-authority-v1","candidate_id":f"attack:{move}","move_id":move,"metadata":metadata,"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":own,"active_attacker":own}
        action={"action_id":f"attack:{move}","action_type":"attack","identity":move,"move_metadata_authority":authority}
        execution=freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action)
    kwargs={}
    if sturdy:kwargs["sturdy_survival_authority"]=_sturdy(d0,own,foe,target_hp)
    if sash:kwargs["focus_sash_survival_authority"]=_focus_sash(d0,own,foe,action,target_hp)
    if contact:
        kwargs["contact_reactive_contact_authority"]=freeze_runtime_d0_canonical_contact_classification_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,attacker=own,target=foe)
    artifact=materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0,runtime_snapshot=snapshot,action=action,execution_authority=execution,**kwargs)
    assert artifact["status"]=="evaluable",artifact
    value=(state,artifact,action,own,foe)
    _ARTIFACT_CACHE[key]=deepcopy(value)
    return deepcopy(value)


def _retain(artifact):return retain_historical_fixed_two_hit_prediction(predictive_artifact=artifact,turn_number=1,decision_point="decision:1:self")
def _mass(r):
    p=r["compatible_original_probability_mass"];return Fraction(p["numerator"],p["denominator"])

def _execution(retained,*,observation_id="exec",seq=1):
    a=retained["actor"]
    return {"event_kind":"executed_move_observed","observation_id":observation_id,"observation_sequence":seq,
            "session_id":retained["session_id"],"turn_number":retained["turn_number"],
            "side":a["side"],"slot_index":a["slot_index"],"pokemon_id":a["pokemon_id"],
            "source":"ui_executed_move_confirmation","trust":"user_confirmed_observation",
            "confirmed":True,"observed":True,
            "payload":{"move_id":retained["move_id"],"source_action_id":retained["source_action_id"]}}

def _parent(retained,*,outcome="landed",count=2,reason="all_hits_landed",seq=2):
    a=retained["actor"]
    return {"event_kind":"multi_hit_action_result_observed","observation_id":"parent","observation_sequence":seq,"session_id":retained["session_id"],"turn_number":1,"side":a["side"],"slot_index":a["slot_index"],"pokemon_id":a["pokemon_id"],"source":"ui_multi_hit_action_result_confirmation","trust":"user_confirmed_observation","confirmed":True,"observed":True,"payload":{"family":"fixed_two_hit","decision_point":retained["decision_point"],"action_id":retained["action_id"],"move_id":retained["move_id"],"actor":deepcopy(a),"target":deepcopy(retained["target"]),"action_outcome":outcome,"landed_hit_count":count,"terminal_reason":reason,"source_execution_observation_id":"exec","predictive_artifact_fingerprint":retained["predictive_artifact_fingerprint"]}}

def _children(retained,leaf,*,critical=None):
    out=[]
    for i,h in enumerate(leaf["ordered_hits"],1):
        a=retained["actor"];out.append({"event_kind":"multi_hit_ordered_hit_observed","observation_id":f"hit-{i}","observation_sequence":2+i,"session_id":retained["session_id"],"turn_number":1,"side":a["side"],"slot_index":a["slot_index"],"pokemon_id":a["pokemon_id"],"source":"ui_multi_hit_ordered_hit_confirmation","trust":"user_confirmed_observation","confirmed":True,"observed":True,"payload":{"family":"fixed_two_hit","decision_point":retained["decision_point"],"action_id":retained["action_id"],"move_id":retained["move_id"],"actor":deepcopy(a),"target":deepcopy(retained["target"]),"parent_multi_hit_observation_id":"parent","hit_index":i,"hp_before":h["pre_hp"],"hp_after":h["post_hp"],"target_fainted_after_hit":h["post_hp"]==0,"critical_state":h["critical_state"] if critical else None,"related_contact_observation_ids":()}})
    return tuple(out)


def test_retention_is_exact_immutable_mass_one_and_tamper_fails():
    _,artifact,_,_,_=_artifact();ret=_retain(artifact)
    assert validate_historical_multi_hit_prediction(ret)["status"]=="resolved"
    assert ret["family"]=="fixed_two_hit" and ret["predictive_artifact"]==artifact
    bad=deepcopy(ret);bad["predictive_artifact"]["terminal_leaves"][0]["leaf_id"]="forged"
    assert validate_historical_multi_hit_prediction(bad)["status"]=="rejected"
    for key,value in (("session_id","x"),("turn_number",2),("action_id","x"),("source_action_id","x"),("move_id","double-kick"),("source_runtime_fingerprint","x")):
        bad=deepcopy(ret);bad[key]=value;assert validate_historical_multi_hit_prediction(bad)["status"]=="rejected"


def test_unsupported_family_and_wrong_actor_target_fail_closed():
    _,artifact,_,_,_=_artifact();ret=_retain(artifact)
    bad=deepcopy(ret);bad["family"]="variable_two_to_five";assert validate_historical_multi_hit_prediction(bad)["reason"]=="unsupported_multi_hit_family"
    for key in ("actor","target"):
        bad=deepcopy(ret);bad[key]={**bad[key],"pokemon_id":"foreign"};assert validate_historical_multi_hit_prediction(bad)["status"]=="rejected"


def test_no_observation_preserves_all_original_leaves_and_mass_one():
    _,artifact,_,_,_=_artifact(accuracy=50);ret=_retain(artifact)
    rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret)
    assert rec["status"]=="incomplete" and rec["reason"]=="insufficient_observation"
    assert len(rec["compatible_terminal_leaf_ids"])==len(artifact["terminal_leaves"]) and _mass(rec)==1
    assert rec["probability_normalization"]=="none_preserve_original_mass"


def test_action_miss_keeps_only_original_miss_leaf_and_rejects_child():
    _,artifact,_,_,_=_artifact(accuracy=50);ret=_retain(artifact);parent=_parent(ret,outcome="miss",count=0,reason="action_miss")
    rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=())
    miss=[x for x in artifact["terminal_leaves"] if x["hit_state"]=="miss"]
    assert rec["match_outcome"]=="uniquely_matched" and rec["compatible_source_paths"][0]["leaf_id"]==miss[0]["leaf_id"] and _mass(rec)==Fraction(1,2)
    fake=_children(ret,next(x for x in artifact["terminal_leaves"] if x["ordered_hits"]))[:1]
    assert reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=fake)["status"]=="rejected"


def test_ordered_hp_filters_path_local_second_hit_and_preserves_roll_ambiguity():
    _,artifact,_,_,_=_artifact();ret=_retain(artifact);leaf=artifact["terminal_leaves"][0];parent=_parent(ret);children=_children(ret,leaf)
    rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=children)
    assert rec["status"]=="resolved" and rec["match_outcome"] in {"uniquely_matched","multiple_compatible_paths"}
    assert all(path["ordered_hits"][0]["post_hp"]==children[0]["payload"]["hp_after"] and path["ordered_hits"][1]["pre_hp"]==children[1]["payload"]["hp_before"] for path in rec["compatible_source_paths"])
    expected=sum((Fraction(x["probability"]["numerator"],x["probability"]["denominator"]) for x in artifact["terminal_leaves"] if x["ordered_hits"][0]["pre_hp"]==children[0]["payload"]["hp_before"] and x["ordered_hits"][0]["post_hp"]==children[0]["payload"]["hp_after"] and x["ordered_hits"][1]["pre_hp"]==children[1]["payload"]["hp_before"] and x["ordered_hits"][1]["post_hp"]==children[1]["payload"]["hp_after"] and x["consequences"]["terminal_reason"]=="all_hits_landed"),Fraction())
    assert _mass(rec)==expected


def test_clamped_first_hit_ko_preserves_crit_roll_ambiguity_and_explicit_crit_filters():
    _,artifact,_,_,_=_artifact(target_hp=1);ret=_retain(artifact);leaf=artifact["terminal_leaves"][0]
    parent=_parent(ret,count=1,reason="target_fainted");children=_children(ret,leaf)
    rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=children)
    assert rec.get("match_outcome")=="multiple_compatible_paths", rec
    crits={p["ordered_hits"][0]["critical_state"] for p in rec["compatible_source_paths"]};assert crits=={"critical","non_critical"}
    filtered=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=_children(ret,leaf,critical=True))
    assert {p["ordered_hits"][0]["critical_state"] for p in filtered["compatible_source_paths"]}=={leaf["ordered_hits"][0]["critical_state"]}


def test_first_hit_ko_rejects_second_hit_and_normal_two_hit_requires_order():
    _,artifact,_,_,_=_artifact(target_hp=1);ret=_retain(artifact);leaf=artifact["terminal_leaves"][0];parent=_parent(ret,count=1,reason="target_fainted")
    good=_children(ret,leaf);assert len(good)==1
    extra=good+(deepcopy(good[0]),);extra[1]["payload"]["hit_index"]=2;extra[1]["observation_id"]="hit-2"
    assert reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=extra)["status"]=="rejected"
    _,artifact,_,_,_=_artifact();ret=_retain(artifact);leaf=artifact["terminal_leaves"][0];parent=_parent(ret)
    bad=list(_children(ret,leaf));bad[0],bad[1]=bad[1],bad[0]
    assert reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=bad)["status"]=="rejected"


def test_fixed_provenance_emits_only_consumed_observations():
    _,artifact,_,_,_=_artifact();ret=_retain(artifact);leaf=artifact["terminal_leaves"][0]
    parent=_parent(ret);children=_children(ret,leaf)
    unrelated={"observation_id":"unrelated","event_kind":"executed_move_observed"}
    derived_hp={"observation_id":"hit-1:hp","event_kind":"exact_hp_transition_observed"}
    derived_faint={"observation_id":"hit-1:faint","event_kind":"faint_observed"}
    rec=reconcile_observed_fixed_two_hit_graph(
        retained_prediction=ret,source_execution_observation=_execution(ret),
        parent_observation=parent,hit_observations=children,
        related_observations=(unrelated,derived_hp,derived_faint))
    assert rec["status"]=="resolved"
    assert rec["source_observation_ids"]==("parent",*(x["observation_id"] for x in children))


def test_fixed_explicit_related_contact_observation_is_retained_in_provenance():
    _,artifact,_,_,_=_artifact();leaf=artifact["terminal_leaves"][0];hit=leaf["ordered_hits"][0]
    hit["contact_reactive_status"]={"branch":"sleep","authority":{"reactive_ability":"effect-spore","source_hit":{
        "hit_index":1,"actual_damage":hit["pre_hp"]-hit["post_hp"],"target_pre_hp":hit["pre_hp"],
        "target_post_hp":hit["post_hp"],"target_routing":"target"}}}
    ret=_retain(artifact);parent=_parent(ret);children=list(_children(ret,leaf))
    children[0]["payload"]["related_contact_observation_ids"]=("reactive-1",)
    a,t=ret["actor"],ret["target"]
    related={"event_kind":"contact_reactive_status_result_observed","observation_id":"reactive-1","observation_sequence":9,
        "session_id":ret["session_id"],"turn_number":1,"source":"runtime_observed_contact_reactive_status_result",
        "trust":"user_confirmed_observation","confirmed":True,"observed":True,
        "payload":{"source_action_id":ret["source_action_id"],"move_id":ret["move_id"],"reactive_ability":"effect-spore",
            "outcome":"sleep","attacker_side":a["side"],"attacker_slot_index":a["slot_index"],"attacker_pokemon_id":a["pokemon_id"],
            "defender_side":t["side"],"defender_slot_index":t["slot_index"],"defender_pokemon_id":t["pokemon_id"],
            "hp_before":children[0]["payload"]["hp_before"],"hp_after":children[0]["payload"]["hp_after"]}}
    rec=reconcile_observed_fixed_two_hit_graph(
        retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,
        hit_observations=children,related_observations=(related,{"observation_id":"unrelated"}))
    assert rec["compatible_source_paths"]
    assert rec["source_observation_ids"]==("parent",*(x["observation_id"] for x in children),"reactive-1")
