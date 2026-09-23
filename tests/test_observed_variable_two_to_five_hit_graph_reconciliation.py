from copy import deepcopy
from fractions import Fraction

import pytest

from llm.advisor_multi_hit_graph_reconciliation import retain_historical_fixed_two_hit_prediction
from llm.advisor_variable_two_to_five_hit_graph_reconciliation import (
    reconcile_observed_variable_two_to_five_hit_graph,
    retain_historical_variable_two_to_five_prediction,
    validate_historical_variable_two_to_five_prediction,
)

SESSION="session-variable-c5"
ACTOR={"session_id":SESSION,"side":"self","slot_index":0,"pokemon_id":"attacker"}
TARGET={"session_id":SESSION,"side":"opponent","slot_index":0,"pokemon_id":"target"}

def _fd(n,d=1): return {"numerator":n,"denominator":d}

def _hit(selected,index,pre,post,roll=0,critical="non_critical",**extra):
    return {"hit_index":index,"selected_hit_count":selected,"pre_hp":pre,"post_hp":post,
            "critical_state":critical,"roll_index":roll,"probability":_fd(1),**extra}

def _artifact(*,move_id="bullet-seed",accuracy=100,early_reason=None,root_counts=(2,3,4,5)):
    roots=[];nodes=[];edges=[]
    hit_factor=Fraction(accuracy,100)
    if accuracy<100:
        roots.append({"root_id":"miss","probability":_fd(100-accuracy,100),"terminal":True,"selected_hit_count":None,
                      "consequences":{"target_final_hp":100}})
    per=Fraction(1,len(root_counts))
    distribution=tuple({"hit_count":selected,"probability":_fd(per.numerator,per.denominator)} for selected in root_counts)
    for selected in root_counts:
        root_prob=hit_factor*per
        root_node=f"root-{selected}"
        roots.append({"root_id":f"hit_count:{selected}","probability":_fd(root_prob.numerator,root_prob.denominator),
                      "terminal":False,"selected_hit_count":selected,"node_id":root_node})
        hp=100
        for completed in range(selected):
            nid=root_node if completed==0 else f"node-{selected}-{completed}"
            nodes.append({"node_id":nid,"selected_hit_count":selected,"completed_hit_count":completed,
                          "target_hp":hp,"attacker_hp":100,"attacker_condition":"none",
                          "sturdy_consumed":False,"focus_sash_consumed":False,"path_local":completed>0})
            index=completed+1
            post=0 if early_reason=="target_fainted" and index==2 else hp-10
            terminal=bool(early_reason and index==2) or index==selected
            eid=f"edge-{selected}-{index}"
            ordered=_hit(selected,index,hp,post,roll=index-1)
            if early_reason=="attacker_fainted_from_contact_reactive_damage" and index==2:
                ordered["attacker_fainted_from_reactive"]=True
                ordered["attacker_post_reactive_hp"]=0
            if early_reason=="effect_spore_sleep_cancels_remaining_hits" and index==2:
                ordered["contact_reactive_status"]={"branch":"sleep","authority":{"reactive_ability":"effect-spore","source_hit":{
                    "hit_index":index,"actual_damage":hp-post,"target_pre_hp":hp,"target_post_hp":post,"target_routing":"target"
                }}}
            edge={"edge_id":eid,"from_node_id":nid,"conditional_probability":_fd(1),
                  "ordered_hit":ordered,"terminal":terminal}
            if terminal:
                edge["terminal_reason"]=early_reason or "selected_hit_count_reached"
                edge["terminal_consequences"]={"target_final_hp":post,"target_ko":post==0}
                edges.append(edge)
                break
            next_id=f"node-{selected}-{index}"
            edge["to_node_id"]=next_id
            edges.append(edge);hp=post
    return {"status":"evaluable","schema_version":"detached-variable-two-to-five-hit-per-hit-predictive-materialization-v1",
            "horizon":"immediate_action_consequence","session_id":SESSION,"source_runtime_fingerprint":"runtime-fp",
            "source_branch_fingerprint":"branch-fp","decision_owner":deepcopy(ACTOR),"action_id":f"attack:{move_id}",
            "move_id":move_id,"attacker":deepcopy(ACTOR),"target":deepcopy(TARGET),
            "action_accuracy":{"status":"resolved","probability_percent":accuracy},
            "execution_authority":{"status":"resolved","schema_version":"runtime-d0-variable-two-to-five-hit-count-execution-authority-v1",
                "session_id":SESSION,"source_runtime_fingerprint":"runtime-fp","source_branch_fingerprint":"branch-fp",
                "action_id":f"attack:{move_id}","move_id":move_id,"attacker":deepcopy(ACTOR),"target":deepcopy(TARGET),
                "hit_count_execution":{"status":"resolved","semantics":"canonical_standard_two_to_five_hit_count_before_per_hit_execution",
                                       "distribution":distribution,"root_mass":_fd(1)},
                "accuracy_execution":{"status":"resolved","semantics":"action_level_once_before_hit_sequence","accuracy":accuracy}},
            "terminal_leaf_representation":"exact_root_to_terminal_path_graph_no_final_state_aggregation",
            "terminal_leaf_roots":tuple(roots),"terminal_leaf_nodes":tuple(nodes),"terminal_leaf_edges":tuple(edges),
            "terminal_probability_mass":_fd(1),"provenance":"test-variable-graph"}

def _retain(a):
    return retain_historical_variable_two_to_five_prediction(
        predictive_artifact=a,turn_number=1,decision_point="decision:1:self",source_action_id=a["action_id"])

def _execution(r):
    return {"event_kind":"executed_move_observed","observation_id":"exec","observation_sequence":1,
            "session_id":SESSION,"turn_number":1,"side":"self","slot_index":0,"pokemon_id":"attacker",
            "source":"ui_executed_move_confirmation","trust":"user_confirmed_observation","confirmed":True,"observed":True,
            "payload":{"move_id":r["move_id"],"source_action_id":r["source_action_id"]}}

def _parent(r,count,reason,outcome="landed"):
    return {"event_kind":"multi_hit_action_result_observed","observation_id":"parent","observation_sequence":2,
            "session_id":SESSION,"turn_number":1,"side":"self","slot_index":0,"pokemon_id":"attacker",
            "source":"ui_multi_hit_action_result_confirmation","trust":"user_confirmed_observation","confirmed":True,"observed":True,
            "payload":{"family":"variable_two_to_five","decision_point":r["decision_point"],"action_id":r["action_id"],
                       "move_id":r["move_id"],"actor":deepcopy(ACTOR),"target":deepcopy(TARGET),
                       "action_outcome":outcome,"landed_hit_count":count,"terminal_reason":reason,
                       "source_execution_observation_id":"exec","predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"]}}

def _children(r,selected,count,*,critical=None):
    hp=100;out=[]
    for i in range(1,count+1):
        post=0 if count==2 and i==2 and r.get("_test_early_reason")=="target_fainted" else hp-10
        out.append({"event_kind":"multi_hit_ordered_hit_observed","observation_id":f"hit-{i}","observation_sequence":2+i,
                    "session_id":SESSION,"turn_number":1,"side":"self","slot_index":0,"pokemon_id":"attacker",
                    "source":"ui_multi_hit_ordered_hit_confirmation","trust":"user_confirmed_observation","confirmed":True,"observed":True,
                    "payload":{"family":"variable_two_to_five","decision_point":r["decision_point"],"action_id":r["action_id"],
                               "move_id":r["move_id"],"actor":deepcopy(ACTOR),"target":deepcopy(TARGET),
                               "parent_multi_hit_observation_id":"parent","hit_index":i,"hp_before":hp,"hp_after":post,
                               "target_fainted_after_hit":post==0,"critical_state":critical,
                               "related_contact_observation_ids":()}})
        hp=post
    return tuple(out)

def _mass(rec):
    x=rec["compatible_original_probability_mass"];return Fraction(x["numerator"],x["denominator"])

def _retained(*,early_reason=None,**kwargs):
    r=_retain(_artifact(early_reason=early_reason,**kwargs));r["_test_early_reason"]=early_reason;return r

@pytest.mark.parametrize("move_id",["bullet-seed","rock-blast"])
def test_valid_retention_root_mass_and_no_observation_preserves_unit_mass(move_id):
    r=_retained(move_id=move_id)
    assert validate_historical_variable_two_to_five_prediction(r)["status"]=="resolved"
    rec=reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r)
    assert rec["status"]=="incomplete" and rec["reason"]=="insufficient_observation" and _mass(rec)==1
    assert rec["probability_normalization"]=="none_preserve_original_mass"
    assert {p["selected_hit_count"] for p in rec["compatible_source_paths"]}=={2,3,4,5}

def test_strict_identity_fingerprint_family_and_population_bomb_reject():
    r=_retained()
    for key,value in (("session_id","other"),("turn_number",2),("actor",{**ACTOR,"pokemon_id":"x"}),
                      ("target",{**TARGET,"pokemon_id":"x"}),("action_id","attack:x"),("move_id","rock-blast")):
        bad=deepcopy(r);bad[key]=value
        assert validate_historical_variable_two_to_five_prediction(bad)["status"]=="rejected"
    bad=deepcopy(r);bad["predictive_artifact"]["terminal_leaf_edges"][0]["edge_id"]="forged"
    assert validate_historical_variable_two_to_five_prediction(bad)["status"]=="rejected"
    bad=deepcopy(r);bad["family"]="fixed_two_hit"
    assert validate_historical_variable_two_to_five_prediction(bad)["status"]=="rejected"
    pop=_artifact(move_id="population-bomb")
    assert retain_historical_variable_two_to_five_prediction(predictive_artifact=pop,turn_number=1,decision_point="d")["status"]=="rejected"

def test_action_miss_filters_original_miss_mass_and_rejects_children():
    r=_retained(accuracy=50)
    p=_parent(r,0,"action_miss","miss")
    rec=reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r,source_execution_observation=_execution(r),parent_observation=p,hit_observations=())
    assert rec["match_outcome"]=="uniquely_matched" and _mass(rec)==Fraction(1,2)
    child=_children(r,2,1)
    assert reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r,source_execution_observation=_execution(r),parent_observation=p,hit_observations=child)["status"]=="rejected"

@pytest.mark.parametrize("selected",[2,3,4,5])
def test_selected_count_exhaustion_resolves_from_graph(selected):
    r=_retained()
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,selected,"selected_hit_count_reached"),
        hit_observations=_children(r,selected,selected))
    assert rec["compatible_source_paths"]
    assert {x["selected_hit_count"] for x in rec["compatible_source_paths"]}=={selected}
    assert "selected_hit_count" not in rec["unresolved_hidden_dimensions"]

@pytest.mark.parametrize("reason",["target_fainted","attacker_fainted_from_contact_reactive_damage","effect_spore_sleep_cancels_remaining_hits"])
def test_early_terminal_prefix_censors_hidden_selected_count(reason):
    r=_retained(early_reason=reason)
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,reason),hit_observations=_children(r,2,2))
    assert {x["selected_hit_count"] for x in rec["compatible_source_paths"]}=={2,3,4,5}
    assert "selected_hit_count" in rec["unresolved_hidden_dimensions"]
    assert _mass(rec)==1

def test_ordered_hp_gap_reorder_crit_and_roll_ambiguity_contracts():
    r=_retained()
    children=list(_children(r,2,2))
    rec=reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=children)
    assert rec["compatible_source_paths"]
    children[1]["payload"]["hit_index"]=3
    assert reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=children)["status"]=="rejected"
    children=list(_children(r,2,2));children[0]["payload"]["critical_state"]="critical"
    rec=reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=children)
    assert rec["match_outcome"]=="incompatible_observation"

def test_modifier_shaped_retained_graphs_are_consumed_without_recalculation():
    skill=_retained(root_counts=(5,))
    rec=reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=skill)
    assert {x["selected_hit_count"] for x in rec["compatible_source_paths"]}=={5} and _mass(rec)==1
    dice=_retained(root_counts=(4,5))
    rec=reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=dice)
    assert {x["selected_hit_count"] for x in rec["compatible_source_paths"]}=={4,5} and _mass(rec)==1

def test_exact_contact_reactive_link_filters_existing_source_branch_without_probability_reweight():
    a=_artifact(early_reason="target_fainted")
    selected3=next(e for e in a["terminal_leaf_edges"] if e["edge_id"]=="edge-3-1")
    selected3["ordered_hit"]["contact_reactive_status"]={
        "branch":"sleep",
        "authority":{"reactive_ability":"effect-spore","source_hit":{
            "hit_index":1,"actual_damage":10,"target_pre_hp":100,"target_post_hp":90,"target_routing":"target"
        }},
    }
    r=_retain(a);r["_test_early_reason"]="target_fainted"
    children=list(_children(r,2,2))
    children[0]["payload"]["related_contact_observation_ids"]=("reactive-1",)
    related={"event_kind":"contact_reactive_status_result_observed","observation_id":"reactive-1","observation_sequence":9,
             "session_id":SESSION,"turn_number":1,"source":"runtime_observed_contact_reactive_status_result",
             "trust":"user_confirmed_observation","confirmed":True,"observed":True,
             "payload":{"source_action_id":r["source_action_id"],"move_id":r["move_id"],"reactive_ability":"effect-spore",
                        "outcome":"sleep","attacker_side":"self","attacker_slot_index":0,"attacker_pokemon_id":"attacker",
                        "defender_side":"opponent","defender_slot_index":0,"defender_pokemon_id":"target",
                        "hp_before":100,"hp_after":90}}
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"target_fainted"),hit_observations=children,related_observations=(related,))
    assert {x["selected_hit_count"] for x in rec["compatible_source_paths"]}=={3}
    assert _mass(rec)==Fraction(1,4)
    assert rec["source_observation_ids"]==("parent","hit-1","hit-2","reactive-1")


def test_graph_validation_rejects_tampered_node_edge_count_and_probability():
    r=_retained()
    for mutate in ("node","edge","mass"):
        bad=deepcopy(r)
        if mutate=="node": bad["predictive_artifact"]["terminal_leaf_nodes"][0]["completed_hit_count"]=99
        elif mutate=="edge": bad["predictive_artifact"]["terminal_leaf_edges"][0]["ordered_hit"]["selected_hit_count"]=5
        else: bad["predictive_artifact"]["terminal_probability_mass"]=_fd(1,2)
        assert validate_historical_variable_two_to_five_prediction(bad)["status"]=="rejected"

def test_source_graph_is_immutable_and_fixed_validator_remains_strict():
    a=_artifact();before=deepcopy(a);r=_retain(a);r["_test_early_reason"]=None
    reconcile_observed_variable_two_to_five_hit_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=_children(r,2,2))
    assert a==before
    assert retain_historical_fixed_two_hit_prediction(predictive_artifact=a,turn_number=1,decision_point="d")["status"]=="rejected"


@pytest.mark.parametrize("value",[None,0,-1,False])
def test_provenance_rejects_invalid_execution_observation_sequence(value):
    r=_retained();execution=_execution(r);execution["observation_sequence"]=value
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=execution,
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=_children(r,2,2))
    assert rec=={"status":"rejected","reason":"multi_hit_source_execution_order_invalid"}


def test_provenance_rejects_parent_not_after_execution():
    r=_retained();parent=_parent(r,2,"selected_hit_count_reached");parent["observation_sequence"]=1
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=parent,hit_observations=_children(r,2,2))
    assert rec=={"status":"rejected","reason":"multi_hit_source_execution_order_invalid"}


@pytest.mark.parametrize(("field","value"),[
    ("side","opponent"),("slot_index",1),("pokemon_id","forged-attacker"),
])
def test_provenance_rejects_parent_outer_actor_mismatch(field,value):
    r=_retained();parent=_parent(r,2,"selected_hit_count_reached");parent[field]=value
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=parent,hit_observations=_children(r,2,2))
    assert rec["status"]=="rejected" and rec["reason"]=="multi_hit_parent_outer_actor_mismatch"


@pytest.mark.parametrize("value",[None,0,-1,False])
def test_provenance_rejects_invalid_parent_observation_sequence(value):
    r=_retained();parent=_parent(r,2,"selected_hit_count_reached");parent["observation_sequence"]=value
    execution=_execution(r);execution["observation_sequence"]=1 if value not in (None,0,-1,False) else 2
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=execution,
        parent_observation=parent,hit_observations=_children(r,2,2))
    assert rec["status"]=="rejected"


@pytest.mark.parametrize(("field","value","reason"),[
    ("event_kind","forged","invalid_multi_hit_ordered_hit_observation"),
    ("source","forged","invalid_multi_hit_ordered_hit_observation"),
    ("trust","forged","invalid_multi_hit_ordered_hit_observation"),
    ("confirmed",False,"invalid_multi_hit_ordered_hit_observation"),
    ("observed",False,"invalid_multi_hit_ordered_hit_observation"),
    ("session_id","other-session","multi_hit_ordered_hit_session_turn_mismatch"),
    ("turn_number",2,"multi_hit_ordered_hit_session_turn_mismatch"),
    ("side","opponent","multi_hit_ordered_hit_outer_actor_mismatch"),
    ("slot_index",1,"multi_hit_ordered_hit_outer_actor_mismatch"),
    ("pokemon_id","forged-attacker","multi_hit_ordered_hit_outer_actor_mismatch"),
    ("observation_sequence",0,"multi_hit_ordered_hit_order_invalid"),
])
def test_provenance_rejects_forged_variable_child_record(field,value,reason):
    r=_retained();children=list(_children(r,2,2));children[0][field]=value
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=children)
    assert rec=={"status":"rejected","reason":reason}


def test_provenance_rejects_missing_variable_child_observation_sequence():
    r=_retained();children=list(_children(r,2,2));children[0].pop("observation_sequence")
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=children)
    assert rec=={"status":"rejected","reason":"multi_hit_ordered_hit_order_invalid"}


def test_provenance_rejects_variable_child_not_after_parent_and_nonmonotonic_children():
    r=_retained();parent=_parent(r,2,"selected_hit_count_reached")
    children=list(_children(r,2,2));children[0]["observation_sequence"]=parent["observation_sequence"]
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,hit_observations=children)
    assert rec=={"status":"rejected","reason":"multi_hit_ordered_hit_order_invalid"}
    children=list(_children(r,2,2));children[1]["observation_sequence"]=children[0]["observation_sequence"]
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,hit_observations=children)
    assert rec=={"status":"rejected","reason":"multi_hit_ordered_hit_order_invalid"}


def test_valid_variable_provenance_preserves_graph_mass_and_no_normalization():
    a=_artifact();before=deepcopy(a);r=_retain(a);r["_test_early_reason"]=None
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,"selected_hit_count_reached"),hit_observations=_children(r,2,2))
    assert rec["status"]=="resolved" and rec["match_outcome"]=="uniquely_matched"
    assert _mass(rec)==Fraction(1,4)
    assert rec["probability_normalization"]=="none_preserve_original_mass"
    assert a==before


def test_variable_provenance_emits_only_consumed_observations():
    r=_retained(root_counts=(2,));parent=_parent(r,2,"selected_hit_count_reached");children=_children(r,2,2)
    extra=(
        {"observation_id":"unrelated","event_kind":"executed_move_observed"},
        {"observation_id":"hit-1:hp","event_kind":"exact_hp_transition_observed"},
        {"observation_id":"hit-1:faint","event_kind":"faint_observed"},
    )
    rec=reconcile_observed_variable_two_to_five_hit_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,
        hit_observations=children,related_observations=extra)
    assert rec["status"]=="resolved"
    assert rec["source_observation_ids"]==("parent",*(x["observation_id"] for x in children))
