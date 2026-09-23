from copy import deepcopy
from fractions import Fraction

import pytest

from llm.advisor_multi_hit_graph_reconciliation import retain_historical_fixed_two_hit_prediction
from llm.advisor_population_bomb_attempt_graph_reconciliation import (
    reconcile_observed_population_bomb_attempt_graph,
    retain_historical_population_bomb_prediction,
    validate_historical_population_bomb_prediction,
)
from llm.advisor_variable_two_to_five_hit_graph_reconciliation import retain_historical_variable_two_to_five_prediction

SESSION="population-bomb-c5"
ACTOR={"session_id":SESSION,"side":"self","slot_index":0,"pokemon_id":"attacker"}
TARGET={"session_id":SESSION,"side":"opponent","slot_index":0,"pokemon_id":"target"}

def _fd(n,d=1):return {"numerator":n,"denominator":d}

def _hit(attempt,hit_index,pre,post,roll=0,critical="non_critical",**extra):
    return {"attempt_index":attempt,"hit_index":hit_index,"pre_hp":pre,"post_hp":post,
            "critical_state":critical,"roll_index":roll,"probability":_fd(1),**extra}

def _authority(kind,hit=Fraction(1,1)):
    plan={"kind":kind}
    if kind=="existing_independent_multiaccuracy":plan.update(count=10,semantics="exact_known_non_applicability")
    elif kind=="single_accuracy_then_fixed_guaranteed_hits":plan.update(count=10,semantics="skill_link_fixed_ten")
    else:plan.update(support=tuple(range(4,11)),conditional_probability=_fd(1,7),semantics="loaded_dice_precedes_skill_link",selected_count_source="loaded-dice")
    return {"status":"resolved","schema_version":"runtime-d0-population-bomb-per-hit-accuracy-execution-authority-v1",
            "session_id":SESSION,"source_runtime_fingerprint":"runtime-fp","source_branch_fingerprint":"branch-fp",
            "action_id":"attack:population-bomb","move_id":"population-bomb","attacker":deepcopy(ACTOR),"target":deepcopy(TARGET),
            "maximum_attempt_execution":{"status":"resolved","maximum_attempts":10,"semantics":"canonical_fixed_ten_attempt_multiaccuracy"},
            "per_attempt_accuracy_execution":{"status":"resolved","semantics":"independent_accuracy_check_per_attempt_stop_on_first_miss",
                "hit_probability":_fd(hit.numerator,hit.denominator),"miss_probability":_fd((1-hit).numerator,(1-hit).denominator),"root_mass":_fd(1)},
            "modifier_authority":{"status":"resolved","modifier_execution_plan":plan}}

def _artifact(kind="existing_independent_multiaccuracy", *, stop=3, terminal="first_miss_terminates_remaining_attempts", early=False):
    hitprob=Fraction(1,2) if kind=="existing_independent_multiaccuracy" and terminal=="first_miss_terminates_remaining_attempts" else Fraction(1,1)
    authority=_authority(kind,hitprob)
    roots=[];nodes=[];edges=[]
    counts=range(4,11) if kind=="single_accuracy_then_uniform_guaranteed_hits" else (10,)
    for planned in counts:
        rootp=Fraction(1,7) if kind=="single_accuracy_then_uniform_guaranteed_hits" else Fraction(1)
        root=f"root-{planned}"
        roots.append({"root_id":f"planned-hits:{planned}","probability":_fd(rootp.numerator,rootp.denominator),"terminal":False,
                      "node_id":root,"modifier_execution_plan":kind,
                      "selected_hit_count":planned if kind=="single_accuracy_then_uniform_guaranteed_hits" else None})
        hp=100;landed=0
        max_attempt=planned if kind!="existing_independent_multiaccuracy" else 10
        for attempt in range(1,max_attempt+1):
            nid=root if attempt==1 else f"node-{planned}-{attempt}"
            nodes.append({"node_id":nid,"attempt_index":attempt,"landed_hit_count":landed,"maximum_attempts":max_attempt,
                          "target_hp":hp,"attacker_hp":100,"attacker_condition":"none","sturdy_consumed":False,
                          "focus_sash_consumed":False,"path_local":attempt>1})
            independent=kind=="existing_independent_multiaccuracy"
            if independent and hitprob<1:
                missp=1-hitprob
                edges.append({"edge_id":f"{nid}:miss","from_node_id":nid,"conditional_probability":_fd(missp.numerator,missp.denominator),
                              "attempt_outcome":{"attempt_index":attempt,"outcome":"miss"},"terminal":True,
                              "terminal_reason":"first_miss_terminates_remaining_attempts",
                              "terminal_consequences":{"landed_hit_count":landed}})
            post=0 if early and attempt==stop and terminal=="target_fainted" else hp-5
            ordered=_hit(attempt,landed+1,hp,post,roll=attempt-1)
            if early and attempt==stop and terminal=="attacker_fainted_from_contact_reactive_damage":
                ordered["attacker_fainted_from_reactive"]=True
            if early and attempt==stop and terminal=="effect_spore_sleep_cancels_remaining_hits":
                ordered["contact_reactive_status"]={"branch":"sleep","authority":{"reactive_ability":"effect-spore","source_hit":{
                    "hit_index":landed+1,"actual_damage":hp-post,"target_pre_hp":hp,"target_post_hp":post,"target_routing":"target"}}}
            planned_end=attempt==max_attempt
            terminate=(early and attempt==stop) or (independent and attempt==10) or (terminal=="maximum_ten_attempts_reached" and attempt==10) or (terminal=="planned_hit_count_reached" and planned_end)
            hitfactor=hitprob if independent else (hitprob if attempt==1 else Fraction(1))
            edge={"edge_id":f"{nid}:hit","from_node_id":nid,"conditional_probability":_fd(hitfactor.numerator,hitfactor.denominator),
                  "attempt_outcome":{"attempt_index":attempt,"outcome":"hit","ordered_hit":ordered},"terminal":terminate}
            if terminate:
                edge["terminal_reason"]="maximum_ten_attempts_reached" if independent and attempt==10 and not early else terminal
                edge["terminal_consequences"]={"landed_hit_count":landed+1,"target_final_hp":post}
                edges.append(edge);break
            nextid=f"node-{planned}-{attempt+1}";edge["to_node_id"]=nextid;edges.append(edge)
            landed+=1;hp=post
            if independent and terminal=="first_miss_terminates_remaining_attempts" and attempt>=stop:
                # Graph still retains later branches, observation selects exact first miss.
                continue
    return {"status":"evaluable","schema_version":"detached-population-bomb-per-hit-accuracy-predictive-graph-materialization-v1",
            "horizon":"immediate_action_consequence","session_id":SESSION,"source_runtime_fingerprint":"runtime-fp",
            "source_branch_fingerprint":"branch-fp","decision_owner":deepcopy(ACTOR),"action_id":"attack:population-bomb",
            "move_id":"population-bomb","attacker":deepcopy(ACTOR),"target":deepcopy(TARGET),"execution_authority":authority,
            "terminal_leaf_roots":tuple(roots),"terminal_leaf_nodes":tuple(nodes),"terminal_leaf_edges":tuple(edges),
            "terminal_probability_mass":_fd(1)}

def _retain(a):
    return retain_historical_population_bomb_prediction(predictive_artifact=a,turn_number=1,decision_point="decision:1:self",source_action_id="attack:population-bomb")

def _execution(r):
    return {"event_kind":"executed_move_observed","observation_id":"exec","observation_sequence":1,"session_id":SESSION,"turn_number":1,
            "side":"self","slot_index":0,"pokemon_id":"attacker","source":"ui_executed_move_confirmation","trust":"user_confirmed_observation",
            "confirmed":True,"observed":True,"payload":{"move_id":"population-bomb","source_action_id":r["source_action_id"]}}

def _parent(r,landed,attempts,reason):
    return {"event_kind":"multi_hit_action_result_observed","observation_id":"parent","observation_sequence":2,"session_id":SESSION,"turn_number":1,
            "side":"self","slot_index":0,"pokemon_id":"attacker","source":"ui_multi_hit_action_result_confirmation","trust":"user_confirmed_observation",
            "confirmed":True,"observed":True,"payload":{"family":"population_bomb_attempt_graph","decision_point":r["decision_point"],
            "action_id":r["action_id"],"move_id":"population-bomb","actor":deepcopy(ACTOR),"target":deepcopy(TARGET),
            "action_outcome":"miss" if landed==0 else "landed","landed_hit_count":landed,"attempt_count":attempts,"terminal_reason":reason,
            "source_execution_observation_id":"exec","predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"]}}

def _attempts(r,outcomes,*,ko=False,crit=None):
    hp=100;landed=0;rows=[]
    for i,outcome in enumerate(outcomes,1):
        common={"family":"population_bomb_attempt_graph","decision_point":r["decision_point"],"action_id":r["action_id"],
                "move_id":"population-bomb","actor":deepcopy(ACTOR),"target":deepcopy(TARGET),"parent_multi_hit_observation_id":"parent",
                "attempt_index":i,"attempt_outcome":outcome}
        if outcome=="hit":
            landed+=1;post=0 if ko and i==len(outcomes) else hp-5
            common.update(hit_index=landed,hp_before=hp,hp_after=post,target_fainted_after_hit=post==0,
                          critical_state=crit,related_contact_observation_ids=());hp=post
        rows.append({"event_kind":"multi_hit_ordered_attempt_observed","observation_id":f"attempt-{i}","observation_sequence":2+i,
                     "session_id":SESSION,"turn_number":1,"side":"self","slot_index":0,"pokemon_id":"attacker",
                     "source":"ui_multi_hit_ordered_attempt_confirmation","trust":"user_confirmed_observation","confirmed":True,"observed":True,
                     "payload":common})
    return tuple(rows)

def _mass(rec):
    x=rec["compatible_original_probability_mass"];return Fraction(x["numerator"],x["denominator"])

def test_valid_retention_and_no_observation_preserves_original_mass():
    r=_retain(_artifact(stop=3))
    assert validate_historical_population_bomb_prediction(r)["status"]=="resolved"
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r)
    assert rec["status"]=="incomplete" and rec["reason"]=="insufficient_observation" and _mass(rec)==1
    assert rec["probability_normalization"]=="none_preserve_original_mass"
    assert "selected_hit_count" not in rec["unresolved_hidden_dimensions"]

def test_identity_fingerprint_and_cross_family_rejection():
    r=_retain(_artifact())
    for key,value in (("session_id","x"),("turn_number",2),("actor",{**ACTOR,"pokemon_id":"x"}),("target",{**TARGET,"pokemon_id":"x"}),
                      ("action_id","x"),("move_id","rock-blast")):
        bad=deepcopy(r);bad[key]=value
        assert validate_historical_population_bomb_prediction(bad)["status"]=="rejected"
    bad=deepcopy(r);bad["predictive_artifact"]["terminal_leaf_edges"][0]["edge_id"]="forged"
    assert validate_historical_population_bomb_prediction(bad)["status"]=="rejected"
    assert retain_historical_fixed_two_hit_prediction(predictive_artifact=r["predictive_artifact"],turn_number=1,decision_point="d")["status"]=="rejected"
    assert retain_historical_variable_two_to_five_prediction(predictive_artifact=r["predictive_artifact"],turn_number=1,decision_point="d")["status"]=="rejected"

def test_independent_hit_hit_miss_filters_exact_attempt_and_original_mass():
    r=_retain(_artifact(stop=3))
    obs=_attempts(r,("hit","hit","miss"))
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,3,"first_miss_terminates_remaining_attempts"),attempt_observations=obs)
    assert rec["compatible_source_paths"]
    path=rec["compatible_source_paths"][0]
    assert [a["attempt_outcome"] for a in path["attempts"]]==["hit","hit","miss"]
    assert _mass(rec)==Fraction(1,8)
    assert "planned_hit_count" not in rec["unresolved_hidden_dimensions"]

def test_first_miss_must_be_explicit_and_terminal():
    r=_retain(_artifact(stop=3))
    no_miss=_attempts(r,("hit","hit"))
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,2,"first_miss_terminates_remaining_attempts"),attempt_observations=no_miss)
    assert rec["status"]=="rejected"
    after=_attempts(r,("hit","miss","hit"))
    assert reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,3,"first_miss_terminates_remaining_attempts"),attempt_observations=after)["status"]=="rejected"

@pytest.mark.parametrize("reason",["target_fainted","attacker_fainted_from_contact_reactive_damage","effect_spore_sleep_cancels_remaining_hits"])
def test_early_terminal_censors_future_attempts(reason):
    r=_retain(_artifact(stop=2,terminal=reason,early=True))
    obs=_attempts(r,("hit","hit"),ko=reason=="target_fainted")
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,2,reason),attempt_observations=obs)
    assert rec["compatible_source_paths"]
    assert all(len(p["attempts"])==2 for p in rec["compatible_source_paths"])

def test_maximum_ten_attempts_has_no_hidden_selected_count():
    r=_retain(_artifact(terminal="maximum_ten_attempts_reached",stop=10))
    obs=_attempts(r,("hit",)*10)
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,10,10,"maximum_ten_attempts_reached"),attempt_observations=obs)
    assert rec["status"]=="resolved",rec
    assert rec["compatible_source_paths"] and all(p["planned_hit_count"] is None for p in rec["compatible_source_paths"])
    assert "planned_hit_count" not in rec["unresolved_hidden_dimensions"]

def test_fixed_guaranteed_plan_has_no_late_miss_branch():
    r=_retain(_artifact("single_accuracy_then_fixed_guaranteed_hits",terminal="planned_hit_count_reached",stop=10))
    obs=_attempts(r,("hit",)*10)
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,10,10,"planned_hit_count_reached"),attempt_observations=obs)
    assert rec["status"]=="resolved",rec
    assert rec["compatible_source_paths"] and {p["modifier_execution_plan"] for p in rec["compatible_source_paths"]}=={"single_accuracy_then_fixed_guaranteed_hits"}

def test_uniform_planned_count_is_censored_by_early_ko_and_resolved_by_exhaustion():
    r=_retain(_artifact("single_accuracy_then_uniform_guaranteed_hits",stop=2,terminal="target_fainted",early=True))
    obs=_attempts(r,("hit","hit"),ko=True)
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,2,2,"target_fainted"),attempt_observations=obs)
    assert {p["planned_hit_count"] for p in rec["compatible_source_paths"]}==set(range(4,11))
    assert "planned_hit_count" in rec["unresolved_hidden_dimensions"]
    r=_retain(_artifact("single_accuracy_then_uniform_guaranteed_hits",terminal="planned_hit_count_reached"))
    obs=_attempts(r,("hit",)*4)
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,4,4,"planned_hit_count_reached"),attempt_observations=obs)
    assert {p["planned_hit_count"] for p in rec["compatible_source_paths"]}=={4}

def test_attempt_contract_miss_has_no_hit_index_and_hit_indices_increment():
    r=_retain(_artifact(stop=2))
    obs=list(_attempts(r,("hit","miss")))
    obs[1]["payload"]["hit_index"]=2
    assert reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,1,2,"first_miss_terminates_remaining_attempts"),attempt_observations=obs)["status"]=="rejected"
    good=_attempts(r,("hit","miss"))
    assert good[0]["payload"]["hit_index"]==1 and "hit_index" not in good[1]["payload"]

def test_equal_hp_preserves_roll_ambiguity_without_posterior_normalization():
    a=_artifact("single_accuracy_then_fixed_guaranteed_hits",terminal="planned_hit_count_reached",stop=10)
    first=next(e for e in a["terminal_leaf_edges"] if e["from_node_id"]=="root-10" and e["attempt_outcome"]["outcome"]=="hit")
    first["conditional_probability"]=_fd(1,2)
    alt=deepcopy(first);alt["edge_id"]=first["edge_id"]+":alt";alt["conditional_probability"]=_fd(1,2)
    alt["attempt_outcome"]["ordered_hit"]["roll_index"]=1
    a["terminal_leaf_edges"]=tuple([*a["terminal_leaf_edges"],alt])
    r=_retain(a)
    obs=_attempts(r,("hit",)*10)
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,10,10,"planned_hit_count_reached"),attempt_observations=obs)
    rolls={p["attempts"][0]["roll_index"] for p in rec["compatible_source_paths"]}
    assert rolls=={0,1}
    assert "roll_index" in rec["unresolved_hidden_dimensions"]
    assert rec["probability_normalization"]=="none_preserve_original_mass"


def test_exact_contact_reactive_link_filters_source_branch_without_double_count():
    a=_artifact("single_accuracy_then_fixed_guaranteed_hits",terminal="planned_hit_count_reached",stop=10)
    first=next(e for e in a["terminal_leaf_edges"] if e["from_node_id"]=="root-10" and e["attempt_outcome"]["outcome"]=="hit")
    first["attempt_outcome"]["ordered_hit"]["contact_reactive_status"]={
        "branch":"sleep","authority":{"reactive_ability":"effect-spore","source_hit":{
            "hit_index":1,"actual_damage":5,"target_pre_hp":100,"target_post_hp":95,"target_routing":"target"}}}
    r=_retain(a);obs=list(_attempts(r,("hit",)*10))
    obs[0]["payload"]["related_contact_observation_ids"]=("reactive-1",)
    related={"event_kind":"contact_reactive_status_result_observed","observation_id":"reactive-1","observation_sequence":20,
             "session_id":SESSION,"turn_number":1,"source":"runtime_observed_contact_reactive_status_result",
             "trust":"user_confirmed_observation","confirmed":True,"observed":True,
             "payload":{"source_action_id":r["source_action_id"],"move_id":"population-bomb","reactive_ability":"effect-spore",
                        "outcome":"sleep","attacker_side":"self","attacker_slot_index":0,"attacker_pokemon_id":"attacker",
                        "defender_side":"opponent","defender_slot_index":0,"defender_pokemon_id":"target","hp_before":100,"hp_after":95}}
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,10,10,"planned_hit_count_reached"),attempt_observations=obs,related_observations=(related,))
    assert rec["compatible_source_paths"]
    assert _mass(rec)==1
    assert rec["source_observation_ids"]==("parent",*(x["observation_id"] for x in obs),"reactive-1")


def test_crit_filter_and_source_graph_immutability():
    a=_artifact(stop=2);before=deepcopy(a);r=_retain(a)
    obs=_attempts(r,("hit","miss"),crit="critical")
    rec=reconcile_observed_population_bomb_attempt_graph(retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,1,2,"first_miss_terminates_remaining_attempts"),attempt_observations=obs)
    assert rec["match_outcome"]=="incompatible_observation"
    assert a==before


@pytest.mark.parametrize("value",[None,0,-1,False])
def test_population_bomb_rejects_invalid_execution_observation_sequence(value):
    r=_retain(_artifact(stop=2));execution=_execution(r);execution["observation_sequence"]=value
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=execution,
        parent_observation=_parent(r,1,2,"first_miss_terminates_remaining_attempts"),
        attempt_observations=_attempts(r,("hit","miss")))
    assert rec=={"status":"rejected","reason":"multi_hit_source_execution_order_invalid"}


@pytest.mark.parametrize("value",[None,0,-1,False])
def test_population_bomb_rejects_invalid_parent_observation_sequence(value):
    r=_retain(_artifact(stop=2));parent=_parent(r,1,2,"first_miss_terminates_remaining_attempts");parent["observation_sequence"]=value
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,
        attempt_observations=_attempts(r,("hit","miss")))
    assert rec["status"]=="rejected"


def test_population_bomb_rejects_parent_not_after_execution():
    r=_retain(_artifact(stop=2));parent=_parent(r,1,2,"first_miss_terminates_remaining_attempts");parent["observation_sequence"]=1
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,
        attempt_observations=_attempts(r,("hit","miss")))
    assert rec=={"status":"rejected","reason":"multi_hit_source_execution_order_invalid"}


@pytest.mark.parametrize(("field","value"),[
    ("side","opponent"),("slot_index",1),("pokemon_id","forged-attacker"),
])
def test_population_bomb_rejects_parent_outer_actor_mismatch(field,value):
    r=_retain(_artifact(stop=2));parent=_parent(r,1,2,"first_miss_terminates_remaining_attempts");parent[field]=value
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,
        attempt_observations=_attempts(r,("hit","miss")))
    assert rec["status"]=="rejected" and rec["reason"]=="multi_hit_parent_outer_actor_mismatch"


@pytest.mark.parametrize(("field","value","reason"),[
    ("session_id","other-session","population_bomb_attempt_session_turn_mismatch"),
    ("turn_number",2,"population_bomb_attempt_session_turn_mismatch"),
    ("side","opponent","population_bomb_attempt_outer_actor_mismatch"),
    ("slot_index",1,"population_bomb_attempt_outer_actor_mismatch"),
    ("pokemon_id","forged-attacker","population_bomb_attempt_outer_actor_mismatch"),
    ("observation_sequence",0,"population_bomb_attempt_order_invalid"),
])
def test_population_bomb_rejects_forged_attempt_provenance(field,value,reason):
    r=_retain(_artifact(stop=2));attempts=list(_attempts(r,("hit","miss")));attempts[0][field]=value
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,1,2,"first_miss_terminates_remaining_attempts"),attempt_observations=attempts)
    assert rec=={"status":"rejected","reason":reason}


def test_population_bomb_rejects_missing_attempt_observation_sequence():
    r=_retain(_artifact(stop=2));attempts=list(_attempts(r,("hit","miss")));attempts[0].pop("observation_sequence")
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,1,2,"first_miss_terminates_remaining_attempts"),attempt_observations=attempts)
    assert rec=={"status":"rejected","reason":"population_bomb_attempt_order_invalid"}


def test_population_bomb_rejects_attempt_not_after_parent_and_nonmonotonic_attempts():
    r=_retain(_artifact(stop=2));parent=_parent(r,1,2,"first_miss_terminates_remaining_attempts")
    attempts=list(_attempts(r,("hit","miss")));attempts[0]["observation_sequence"]=parent["observation_sequence"]
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,attempt_observations=attempts)
    assert rec=={"status":"rejected","reason":"population_bomb_attempt_order_invalid"}
    attempts=list(_attempts(r,("hit","miss")));attempts[1]["observation_sequence"]=attempts[0]["observation_sequence"]
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,attempt_observations=attempts)
    assert rec=={"status":"rejected","reason":"population_bomb_attempt_order_invalid"}


def test_valid_population_bomb_provenance_preserves_graph_mass_and_no_normalization():
    a=_artifact(stop=2);before=deepcopy(a);r=_retain(a)
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),
        parent_observation=_parent(r,1,2,"first_miss_terminates_remaining_attempts"),
        attempt_observations=_attempts(r,("hit","miss")))
    assert rec["status"]=="resolved" and rec["compatible_source_paths"]
    assert _mass(rec)==Fraction(1,4)
    assert rec["probability_normalization"]=="none_preserve_original_mass"
    assert a==before


def test_population_bomb_provenance_emits_only_consumed_observations():
    r=_retain(_artifact(stop=2));parent=_parent(r,1,2,"first_miss_terminates_remaining_attempts")
    attempts=_attempts(r,("hit","miss"))
    extra=(
        {"observation_id":"unrelated","event_kind":"executed_move_observed"},
        {"observation_id":"attempt-1:hp","event_kind":"exact_hp_transition_observed"},
        {"observation_id":"attempt-1:faint","event_kind":"faint_observed"},
    )
    rec=reconcile_observed_population_bomb_attempt_graph(
        retained_prediction=r,source_execution_observation=_execution(r),parent_observation=parent,
        attempt_observations=attempts,related_observations=extra)
    assert rec["status"]=="resolved"
    assert rec["source_observation_ids"]==("parent",*(x["observation_id"] for x in attempts))


def test_population_bomb_validator_binds_independent_accuracy_edge_split():
    valid=_artifact(stop=2);before=deepcopy(valid)
    assert _retain(valid)["status"]=="resolved"
    assert valid==before

    bad=deepcopy(valid)
    root="root-10"
    hit_edge=next(e for e in bad["terminal_leaf_edges"] if e["from_node_id"]==root and e["attempt_outcome"]["outcome"]=="hit")
    miss_edge=next(e for e in bad["terminal_leaf_edges"] if e["from_node_id"]==root and e["attempt_outcome"]["outcome"]=="miss")
    hit_edge["conditional_probability"]=_fd(4,5);miss_edge["conditional_probability"]=_fd(1,5)
    rejected=_retain(bad)
    assert rejected=={"status":"rejected","reason":"population_bomb_attempt_probability_split_mismatch"}


def test_population_bomb_validator_rejects_wrong_hit_and_miss_splits_with_unit_mass():
    valid=_artifact(stop=2)
    for hit_probability,miss_probability in ((3,1),(1,3)):
        bad=deepcopy(valid);root="root-10"
        hit_edge=next(e for e in bad["terminal_leaf_edges"] if e["from_node_id"]==root and e["attempt_outcome"]["outcome"]=="hit")
        miss_edge=next(e for e in bad["terminal_leaf_edges"] if e["from_node_id"]==root and e["attempt_outcome"]["outcome"]=="miss")
        total=hit_probability+miss_probability
        hit_edge["conditional_probability"]=_fd(hit_probability,total)
        miss_edge["conditional_probability"]=_fd(miss_probability,total)
        assert _retain(bad)=={"status":"rejected","reason":"population_bomb_attempt_probability_split_mismatch"}


def test_population_bomb_guaranteed_plans_keep_initial_accuracy_and_late_guaranteed_hits():
    for kind in ("single_accuracy_then_fixed_guaranteed_hits","single_accuracy_then_uniform_guaranteed_hits"):
        artifact=_artifact(kind,terminal="planned_hit_count_reached")
        before=deepcopy(artifact)
        retained=_retain(artifact)
        assert retained["status"]=="resolved",retained
        assert artifact==before
        assert retained["predictive_artifact"]["terminal_probability_mass"]==_fd(1)
