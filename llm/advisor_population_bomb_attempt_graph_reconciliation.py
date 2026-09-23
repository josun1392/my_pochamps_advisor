"""Strict C5 retention and detached reconciliation for Population Bomb attempt graphs."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping, Sequence

from llm.advisor_multi_hit_graph_reconciliation import _related_contact_matches_hit

RETENTION_SCHEMA="historical-multi-hit-predictive-graph-v1"
RECONCILIATION_SCHEMA="observed-multi-hit-graph-reconciliation-v1"
PREDICTIVE_SCHEMA="detached-population-bomb-per-hit-accuracy-predictive-graph-materialization-v1"
EXECUTION_SCHEMA="runtime-d0-population-bomb-per-hit-accuracy-execution-authority-v1"
FAMILY="population_bomb_attempt_graph"
MOVE_ID="population-bomb"
PLAN_KINDS=frozenset({
    "existing_independent_multiaccuracy",
    "single_accuracy_then_fixed_guaranteed_hits",
    "single_accuracy_then_uniform_guaranteed_hits",
})
TERMINAL_REASONS=frozenset({
    "first_miss_terminates_remaining_attempts",
    "target_fainted",
    "attacker_fainted_from_contact_reactive_damage",
    "effect_spore_sleep_cancels_remaining_hits",
    "maximum_ten_attempts_reached",
    "planned_hit_count_reached",
})


def retain_historical_population_bomb_prediction(*,predictive_artifact:Mapping[str,Any],turn_number:int,
        decision_point:str,source_action_id:str|None=None)->dict[str,Any]:
    checked=_validate_artifact(predictive_artifact)
    if checked.get("status")!="resolved":return checked
    if not _pos(turn_number) or not _text(decision_point):return _result("rejected","invalid_historical_multi_hit_identity")
    a=deepcopy(dict(predictive_artifact));source_action_id=source_action_id or a["action_id"]
    if not _text(source_action_id):return _result("rejected","historical_multi_hit_source_action_id_invalid")
    fp=_fingerprint(a)
    core={"family":FAMILY,"session_id":a["session_id"],"turn_number":turn_number,"actor":a["attacker"],"target":a["target"],
          "decision_point":decision_point,"action_id":a["action_id"],"source_action_id":source_action_id,"move_id":a["move_id"],
          "source_runtime_fingerprint":a["source_runtime_fingerprint"],"source_branch_fingerprint":a["source_branch_fingerprint"],
          "predictive_artifact_fingerprint":fp}
    return {"status":"resolved","schema_version":RETENTION_SCHEMA,"family":FAMILY,
            "source_predictive_schema_version":PREDICTIVE_SCHEMA,**deepcopy(core),
            "predictive_artifact":a,"retention_fingerprint":_fingerprint(core),
            "provenance":"authenticated_pre_observation_population_bomb_attempt_graph_v1"}


def validate_historical_population_bomb_prediction(value:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("schema_version")!=RETENTION_SCHEMA:return _result("rejected","historical_multi_hit_prediction_missing")
    if value.get("family")!=FAMILY:return _result("rejected","unsupported_multi_hit_family")
    a=value.get("predictive_artifact");checked=_validate_artifact(a)
    if checked.get("status")!="resolved":return checked
    expected={"source_predictive_schema_version":PREDICTIVE_SCHEMA,"session_id":a["session_id"],"actor":a["attacker"],
              "target":a["target"],"action_id":a["action_id"],"move_id":a["move_id"],
              "source_runtime_fingerprint":a["source_runtime_fingerprint"],"source_branch_fingerprint":a["source_branch_fingerprint"]}
    if any(value.get(k)!=v for k,v in expected.items()):return _result("rejected","historical_multi_hit_identity_mismatch")
    if not _pos(value.get("turn_number")) or not _text(value.get("decision_point")) or not _text(value.get("source_action_id")):
        return _result("rejected","historical_multi_hit_identity_invalid")
    if value.get("predictive_artifact_fingerprint")!=_fingerprint(a):return _result("rejected","historical_multi_hit_predictive_fingerprint_mismatch")
    core={k:value[k] for k in ("family","session_id","turn_number","actor","target","decision_point","action_id","source_action_id",
                               "move_id","source_runtime_fingerprint","source_branch_fingerprint","predictive_artifact_fingerprint")}
    if value.get("retention_fingerprint")!=_fingerprint(core):return _result("rejected","historical_multi_hit_retention_fingerprint_mismatch")
    return deepcopy(dict(value))


def reconcile_observed_population_bomb_attempt_graph(*,retained_prediction:Mapping[str,Any],
        source_execution_observation:Mapping[str,Any]|None=None,parent_observation:Mapping[str,Any]|None=None,
        attempt_observations:Sequence[Mapping[str,Any]]|None=None,
        related_observations:Sequence[Mapping[str,Any]]|None=None)->dict[str,Any]:
    r=validate_historical_population_bomb_prediction(retained_prediction)
    if r.get("status")!="resolved":return r
    if parent_observation is None:return _incomplete(r)
    err=_validate_execution(source_execution_observation,parent_observation,r) or _validate_parent(parent_observation,r)
    if err:return _result("rejected",err)
    attempts=tuple(attempt_observations or ())
    err=_validate_attempts(parent_observation,attempts,r)
    if err:return _result("rejected",err)
    related={x.get("observation_id"):x for x in (related_observations or ()) if isinstance(x,Mapping)}
    for obs in attempts:
        p=obs["payload"]
        if p["attempt_outcome"]=="hit" and any(oid not in related for oid in p.get("related_contact_observation_ids",())):
            return _result("rejected","multi_hit_related_contact_observation_missing")
    compatible=_compatible_paths(r["predictive_artifact"],parent_observation["payload"],attempts,related,r)
    return _reconciliation(r,compatible,(parent_observation,*attempts,*tuple(related.values())),_unresolved(compatible))


def _validate_artifact(v:Any)->dict[str,Any]:
    if not isinstance(v,Mapping) or v.get("status")!="evaluable" or v.get("schema_version")!=PREDICTIVE_SCHEMA:
        return _result("rejected","invalid_population_bomb_predictive_artifact")
    if v.get("horizon")!="immediate_action_consequence" or v.get("move_id")!=MOVE_ID:
        return _result("rejected","unsupported_population_bomb_predictive_artifact")
    for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","action_id","move_id"):
        if not _text(v.get(k)):return _result("rejected","population_bomb_predictive_identity_invalid")
    for k in ("attacker","target","decision_owner"):
        if not _owner(v.get(k),v["session_id"]):return _result("rejected","population_bomb_predictive_owner_invalid")
    if v["attacker"]!=v["decision_owner"]:return _result("rejected","population_bomb_attacker_decision_owner_mismatch")
    execution=v.get("execution_authority")
    if not isinstance(execution,Mapping) or execution.get("status")!="resolved" or execution.get("schema_version")!=EXECUTION_SCHEMA:
        return _result("rejected","population_bomb_execution_authority_invalid")
    for k,expected in (("session_id",v["session_id"]),("source_runtime_fingerprint",v["source_runtime_fingerprint"]),
                       ("source_branch_fingerprint",v["source_branch_fingerprint"]),("action_id",v["action_id"]),
                       ("move_id",MOVE_ID),("attacker",v["attacker"]),("target",v["target"])):
        if execution.get(k)!=expected:return _result("rejected","population_bomb_execution_authority_identity_mismatch")
    maximum=execution.get("maximum_attempt_execution")
    if not isinstance(maximum,Mapping) or maximum.get("status")!="resolved" or maximum.get("maximum_attempts")!=10 or maximum.get("semantics")!="canonical_fixed_ten_attempt_multiaccuracy":
        return _result("rejected","population_bomb_maximum_attempt_authority_invalid")
    accuracy=execution.get("per_attempt_accuracy_execution")
    if not isinstance(accuracy,Mapping) or accuracy.get("status")!="resolved" or accuracy.get("semantics")!="independent_accuracy_check_per_attempt_stop_on_first_miss":
        return _result("rejected","population_bomb_per_attempt_accuracy_authority_invalid")
    hit=_fraction(accuracy.get("hit_probability"));miss=_fraction(accuracy.get("miss_probability"))
    if hit is None or miss is None or hit<0 or miss<0 or hit+miss!=1 or _fraction(accuracy.get("root_mass"))!=1:
        return _result("rejected","population_bomb_attempt_probability_invalid")
    plan=execution.get("modifier_authority",{}).get("modifier_execution_plan")
    kind=plan.get("kind") if isinstance(plan,Mapping) else None
    if kind not in PLAN_KINDS:return _result("rejected","population_bomb_modifier_execution_plan_invalid")
    if kind=="single_accuracy_then_fixed_guaranteed_hits" and plan.get("count")!=10:
        return _result("rejected","population_bomb_fixed_plan_invalid")
    if kind=="single_accuracy_then_uniform_guaranteed_hits":
        if tuple(plan.get("support",()))!=tuple(range(4,11)) or _fraction(plan.get("conditional_probability"))!=Fraction(1,7):
            return _result("rejected","population_bomb_uniform_plan_invalid")
    roots,nodes,edges=v.get("terminal_leaf_roots"),v.get("terminal_leaf_nodes"),v.get("terminal_leaf_edges")
    if not isinstance(roots,(tuple,list)) or not roots or not isinstance(nodes,(tuple,list)) or not nodes or not isinstance(edges,(tuple,list)) or not edges:
        return _result("rejected","population_bomb_graph_missing")
    if _fraction(v.get("terminal_probability_mass"))!=1:return _result("rejected","population_bomb_terminal_probability_mass_not_one")
    node_by_id={}
    for n in nodes:
        if not isinstance(n,Mapping) or not _text(n.get("node_id")) or n["node_id"] in node_by_id:return _result("rejected","population_bomb_node_identity_invalid")
        if not _pos(n.get("attempt_index")) or n["attempt_index"]>10 or not _nn(n.get("landed_hit_count")) or n["landed_hit_count"]>10:
            return _result("rejected","population_bomb_node_attempt_state_invalid")
        if not _pos(n.get("maximum_attempts")) or n["maximum_attempts"]>10 or n["attempt_index"]>n["maximum_attempts"]:
            return _result("rejected","population_bomb_node_maximum_invalid")
        if not _nn(n.get("target_hp")) or not _nn(n.get("attacker_hp")):return _result("rejected","population_bomb_node_hp_invalid")
        node_by_id[n["node_id"]]=n
    root_mass=Fraction();root_plans=set();selected=[]
    for root in roots:
        if not isinstance(root,Mapping) or not _text(root.get("root_id")) or root.get("terminal") is not False or root.get("node_id") not in node_by_id:
            return _result("rejected","population_bomb_root_identity_invalid")
        rp=_fraction(root.get("probability"))
        if rp is None or rp<=0:return _result("rejected","population_bomb_root_probability_invalid")
        root_mass+=rp;root_plans.add(root.get("modifier_execution_plan"))
        selected.append(root.get("selected_hit_count"))
    if root_mass!=1 or root_plans!={kind}:return _result("rejected","population_bomb_root_mass_or_plan_invalid")
    if kind=="single_accuracy_then_uniform_guaranteed_hits":
        if sorted(selected)!=list(range(4,11)) or any(_fraction(r.get("probability"))!=Fraction(1,7) for r in roots):
            return _result("rejected","population_bomb_uniform_root_distribution_invalid")
    else:
        if len(roots)!=1 or roots[0].get("selected_hit_count") is not None:
            return _result("rejected","population_bomb_nonuniform_root_invalid")
    edge_ids=set();outgoing={}
    for e in edges:
        if not isinstance(e,Mapping) or not _text(e.get("edge_id")) or e["edge_id"] in edge_ids:return _result("rejected","population_bomb_edge_identity_invalid")
        edge_ids.add(e["edge_id"])
        if e.get("from_node_id") not in node_by_id:return _result("rejected","population_bomb_edge_source_invalid")
        cp=_fraction(e.get("conditional_probability"))
        if cp is None or cp<=0:return _result("rejected","population_bomb_edge_probability_invalid")
        outcome=e.get("attempt_outcome")
        if not isinstance(outcome,Mapping) or outcome.get("outcome") not in {"hit","miss"} or not _pos(outcome.get("attempt_index")):
            return _result("rejected","population_bomb_attempt_outcome_invalid")
        source=node_by_id[e["from_node_id"]]
        if outcome["attempt_index"]!=source["attempt_index"]:return _result("rejected","population_bomb_attempt_index_mismatch")
        if outcome["outcome"]=="miss":
            if set(outcome)!={"attempt_index","outcome"} or e.get("terminal") is not True or e.get("terminal_reason")!="first_miss_terminates_remaining_attempts":
                return _result("rejected","population_bomb_miss_edge_invalid")
            if kind!="existing_independent_multiaccuracy" and source["attempt_index"]!=1:
                return _result("rejected","population_bomb_guaranteed_plan_late_miss_invalid")
        else:
            h=outcome.get("ordered_hit")
            if not _valid_hit(h,source):return _result("rejected","population_bomb_ordered_hit_invalid")
            if e.get("terminal") is False:
                dest=node_by_id.get(e.get("to_node_id"))
                if not isinstance(dest,Mapping) or dest["attempt_index"]!=source["attempt_index"]+1 or dest["landed_hit_count"]!=source["landed_hit_count"]+1 or dest["target_hp"]!=h["post_hp"]:
                    return _result("rejected","population_bomb_edge_destination_invalid")
            else:
                reason=e.get("terminal_reason")
                if reason not in TERMINAL_REASONS:return _result("rejected","population_bomb_terminal_reason_invalid")
                if reason=="target_fainted" and h["post_hp"]!=0:return _result("rejected","population_bomb_target_faint_terminal_invalid")
                if reason=="maximum_ten_attempts_reached" and (kind!="existing_independent_multiaccuracy" or h["attempt_index"]!=10):
                    return _result("rejected","population_bomb_maximum_terminal_invalid")
                if reason=="planned_hit_count_reached" and (kind=="existing_independent_multiaccuracy" or h["attempt_index"]!=source["maximum_attempts"]):
                    return _result("rejected","population_bomb_planned_count_terminal_invalid")
                if reason=="attacker_fainted_from_contact_reactive_damage" and h.get("attacker_fainted_from_reactive") is not True:
                    return _result("rejected","population_bomb_attacker_faint_terminal_invalid")
                if reason=="effect_spore_sleep_cancels_remaining_hits":
                    reactive=h.get("contact_reactive_status")
                    if not isinstance(reactive,Mapping) or reactive.get("branch")!="sleep":return _result("rejected","population_bomb_effect_spore_terminal_invalid")
        outgoing.setdefault(e["from_node_id"],[]).append(e)
    for n in nodes:
        es=outgoing.get(n["node_id"],())
        if not es:return _result("rejected","population_bomb_nonterminal_node_has_no_edges")
        if sum((_fraction(e["conditional_probability"]) or Fraction() for e in es),Fraction())!=1:
            return _result("rejected","population_bomb_outgoing_probability_mass_not_one")
    return {"status":"resolved","modifier_execution_plan":kind}


def _valid_hit(h:Any,source:Mapping[str,Any])->bool:
    return (isinstance(h,Mapping) and h.get("attempt_index")==source["attempt_index"] and h.get("hit_index")==source["landed_hit_count"]+1
            and _nn(h.get("pre_hp")) and _nn(h.get("post_hp")) and h["pre_hp"]==source["target_hp"] and h["post_hp"]<=h["pre_hp"]
            and h.get("critical_state") in {"critical","non_critical"} and isinstance(h.get("roll_index"),int)
            and not isinstance(h.get("roll_index"),bool) and 0<=h["roll_index"]<16)


def _validate_execution(obs,parent,r):
    if not isinstance(obs,Mapping) or obs.get("event_kind")!="executed_move_observed" or obs.get("source")!="ui_executed_move_confirmation" or obs.get("trust")!="user_confirmed_observation" or obs.get("confirmed") is not True or obs.get("observed") is not True:
        return "multi_hit_source_execution_observation_invalid"
    a=r["actor"];p=obs.get("payload")
    if obs.get("session_id")!=r["session_id"] or obs.get("turn_number")!=r["turn_number"] or (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(a["side"],a["slot_index"],a["pokemon_id"]):
        return "multi_hit_source_execution_identity_mismatch"
    if not isinstance(p,Mapping) or p.get("move_id")!=MOVE_ID or p.get("source_action_id")!=r["source_action_id"]:
        return "multi_hit_source_execution_payload_mismatch"
    if parent.get("payload",{}).get("source_execution_observation_id")!=obs.get("observation_id"):
        return "multi_hit_source_execution_link_mismatch"
    return None


def _validate_parent(obs,r):
    if not isinstance(obs,Mapping) or obs.get("event_kind")!="multi_hit_action_result_observed" or obs.get("source")!="ui_multi_hit_action_result_confirmation" or obs.get("trust")!="user_confirmed_observation" or obs.get("confirmed") is not True or obs.get("observed") is not True:
        return "invalid_multi_hit_parent_observation"
    p=obs.get("payload")
    keys={"family","decision_point","action_id","move_id","actor","target","action_outcome","landed_hit_count","attempt_count",
          "terminal_reason","source_execution_observation_id","predictive_artifact_fingerprint"}
    if not isinstance(p,Mapping) or set(p)!=keys:return "invalid_population_bomb_parent_payload"
    if p.get("family")!=FAMILY or p.get("predictive_artifact_fingerprint")!=r["predictive_artifact_fingerprint"]:return "multi_hit_parent_prediction_mismatch"
    if any(p.get(k)!=r[k] for k in ("decision_point","action_id","move_id")) or p.get("actor")!=r["actor"] or p.get("target")!=r["target"]:
        return "multi_hit_parent_identity_mismatch"
    if obs.get("session_id")!=r["session_id"] or obs.get("turn_number")!=r["turn_number"]:return "multi_hit_parent_session_turn_mismatch"
    if p.get("action_outcome") not in {"landed","miss"} or not _nn(p.get("landed_hit_count")) or not _pos(p.get("attempt_count")) or p["attempt_count"]>10 or p.get("terminal_reason") not in TERMINAL_REASONS:
        return "population_bomb_parent_contract_invalid"
    if p["action_outcome"]=="miss" and (p["landed_hit_count"]!=0 or p["attempt_count"]!=1 or p["terminal_reason"]!="first_miss_terminates_remaining_attempts"):
        return "population_bomb_parent_miss_contract_invalid"
    return None


def _validate_attempts(parent,attempts,r):
    pp=parent["payload"]
    if len(attempts)!=pp["attempt_count"]:return "population_bomb_attempt_count_mismatch"
    landed=0;terminal_seen=False
    for index,obs in enumerate(attempts,1):
        if terminal_seen:return "population_bomb_attempt_after_terminal_invalid"
        if not isinstance(obs,Mapping) or obs.get("event_kind")!="multi_hit_ordered_attempt_observed" or obs.get("source")!="ui_multi_hit_ordered_attempt_confirmation" or obs.get("trust")!="user_confirmed_observation" or obs.get("confirmed") is not True or obs.get("observed") is not True:
            return "invalid_population_bomb_attempt_observation"
        p=obs.get("payload")
        common={"family","decision_point","action_id","move_id","actor","target","parent_multi_hit_observation_id","attempt_index","attempt_outcome"}
        hit_keys=common|{"hit_index","hp_before","hp_after","target_fainted_after_hit","critical_state","related_contact_observation_ids"}
        if not isinstance(p,Mapping) or set(p) not in {frozenset(common),frozenset(hit_keys)}:return "invalid_population_bomb_attempt_payload"
        if p["family"]!=FAMILY or p["decision_point"]!=r["decision_point"] or p["action_id"]!=r["action_id"] or p["move_id"]!=MOVE_ID or p["actor"]!=r["actor"] or p["target"]!=r["target"] or p["parent_multi_hit_observation_id"]!=parent.get("observation_id"):
            return "population_bomb_attempt_identity_mismatch"
        if p["attempt_index"]!=index or p["attempt_outcome"] not in {"hit","miss"}:return "population_bomb_attempt_index_or_outcome_invalid"
        if p["attempt_outcome"]=="miss":
            if set(p)!=common:return "population_bomb_miss_attempt_has_hit_fields"
            terminal_seen=True
        else:
            landed+=1
            if set(p)!=hit_keys or p["hit_index"]!=landed:return "population_bomb_hit_index_invalid"
            if not _nn(p["hp_before"]) or not _nn(p["hp_after"]) or p["hp_after"]>p["hp_before"] or p["target_fainted_after_hit"] is not (p["hp_after"]==0):
                return "population_bomb_hit_hp_invalid"
            if p["critical_state"] not in {None,"critical","non_critical"}:return "population_bomb_hit_critical_invalid"
            ids=p["related_contact_observation_ids"]
            if not isinstance(ids,(tuple,list)) or len(ids)!=len(set(ids)) or any(not _text(x) for x in ids):return "population_bomb_contact_links_invalid"
            if index>1:
                prior=attempts[index-2]["payload"]
                if prior["attempt_outcome"]=="hit" and prior["hp_after"]!=p["hp_before"]:return "population_bomb_ordered_hp_chain_invalid"
            if p["target_fainted_after_hit"]:terminal_seen=True
    if landed!=pp["landed_hit_count"]:return "population_bomb_landed_hit_count_mismatch"
    last=attempts[-1]["payload"]
    reason=pp["terminal_reason"]
    if reason=="first_miss_terminates_remaining_attempts" and last["attempt_outcome"]!="miss":return "population_bomb_first_miss_not_observed"
    if reason!="first_miss_terminates_remaining_attempts" and last["attempt_outcome"]!="hit":return "population_bomb_terminal_hit_missing"
    if reason=="target_fainted" and last.get("target_fainted_after_hit") is not True:return "population_bomb_target_faint_observation_mismatch"
    if reason in {"maximum_ten_attempts_reached","planned_hit_count_reached"} and last.get("target_fainted_after_hit") is True:return "population_bomb_exhaustion_after_faint_invalid"
    return None


def _compatible_paths(a,parent,attempts,related,r):
    outgoing={}
    for e in a["terminal_leaf_edges"]:outgoing.setdefault(e["from_node_id"],[]).append(e)
    paths=[]
    for root in a["terminal_leaf_roots"]:
        states=[(root["node_id"],_fraction(root["probability"]),(),())]
        for obs in attempts:
            next_states=[]
            for nid,mass,edges,records in states:
                for edge in outgoing.get(nid,()):
                    if not _edge_matches(edge,obs,related,r):continue
                    nm=mass*(_fraction(edge["conditional_probability"]) or Fraction());ne=edges+(edge["edge_id"],)
                    nr=records+(deepcopy(edge["attempt_outcome"]),)
                    if len(nr)<len(attempts):
                        if edge.get("terminal"):continue
                        next_states.append((edge["to_node_id"],nm,ne,nr))
                    elif edge.get("terminal") and edge.get("terminal_reason")==parent["terminal_reason"]:
                        paths.append({"root_id":root["root_id"],"modifier_execution_plan":root["modifier_execution_plan"],
                                      "planned_hit_count":root.get("selected_hit_count"),"probability":nm,"edge_ids":ne,
                                      "attempts":nr,"terminal_reason":edge["terminal_reason"],"terminal_source_id":edge["edge_id"]})
            states=next_states
    return tuple(paths)


def _edge_matches(edge,obs,related,r):
    p=obs["payload"];outcome=edge.get("attempt_outcome")
    if not isinstance(outcome,Mapping) or outcome.get("attempt_index")!=p["attempt_index"] or outcome.get("outcome")!=p["attempt_outcome"]:
        return False
    if p["attempt_outcome"]=="miss":return set(outcome)=={"attempt_index","outcome"}
    h=outcome.get("ordered_hit")
    if not isinstance(h,Mapping) or h.get("hit_index")!=p["hit_index"] or h.get("pre_hp")!=p["hp_before"] or h.get("post_hp")!=p["hp_after"]:
        return False
    if p["critical_state"] is not None and h.get("critical_state")!=p["critical_state"]:return False
    return all(_related_contact_matches_hit(related[oid],h,p,obs,r) for oid in p["related_contact_observation_ids"])


def _incomplete(r):
    a=r["predictive_artifact"];roots=tuple({"root_id":x.get("root_id"),"modifier_execution_plan":x.get("modifier_execution_plan"),
        "planned_hit_count":x.get("selected_hit_count"),"probability":deepcopy(x.get("probability"))} for x in a["terminal_leaf_roots"])
    return {"status":"incomplete","schema_version":RECONCILIATION_SCHEMA,"reason":"insufficient_observation",
            "source_prediction_kind":"population_bomb_attempt_graph","family":FAMILY,"session_id":r["session_id"],"turn_number":r["turn_number"],
            "actor":deepcopy(r["actor"]),"target":deepcopy(r["target"]),"decision_point":r["decision_point"],"action_id":r["action_id"],"move_id":MOVE_ID,
            "predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"],"match_outcome":None,
            "compatible_terminal_leaf_ids":(),"compatible_source_paths":roots,
            "compatible_original_probability_mass":{"numerator":1,"denominator":1},"probability_normalization":"none_preserve_original_mass",
            "source_observation_ids":(),"unresolved_hidden_dimensions":(("planned_hit_count",) if any(x["planned_hit_count"] is not None for x in roots) else ()),
            "provenance":"preserve_immutable_original_population_bomb_attempt_graph_without_observation_v1"}


def _reconciliation(r,paths,observations,unresolved):
    mass=sum((x["probability"] for x in paths),Fraction())
    outcome="incompatible_observation" if not paths else "uniquely_matched" if len(paths)==1 else "multiple_compatible_paths"
    return {"status":"resolved","schema_version":RECONCILIATION_SCHEMA,"reason":None,
            "source_prediction_kind":"population_bomb_attempt_graph","family":FAMILY,"session_id":r["session_id"],"turn_number":r["turn_number"],
            "actor":deepcopy(r["actor"]),"target":deepcopy(r["target"]),"decision_point":r["decision_point"],"action_id":r["action_id"],"move_id":MOVE_ID,
            "predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"],"match_outcome":outcome,
            "compatible_terminal_leaf_ids":tuple(_path_id(x) for x in paths),
            "compatible_source_paths":tuple({"source_path_id":_path_id(x),"root_id":x["root_id"],"modifier_execution_plan":x["modifier_execution_plan"],
                "planned_hit_count":x["planned_hit_count"],"traversed_edge_ids":x["edge_ids"],"terminal_source_id":x["terminal_source_id"],
                "terminal_reason":x["terminal_reason"],"attempts":tuple({"attempt_index":a["attempt_index"],"attempt_outcome":a["outcome"],
                    **({"hit_index":a["ordered_hit"].get("hit_index"),"critical_state":a["ordered_hit"].get("critical_state"),
                        "roll_index":a["ordered_hit"].get("roll_index"),"pre_hp":a["ordered_hit"].get("pre_hp"),"post_hp":a["ordered_hit"].get("post_hp")}
                       if a["outcome"]=="hit" else {})} for a in x["attempts"])} for x in paths),
            "compatible_original_probability_mass":_fd(mass),"probability_normalization":"none_preserve_original_mass",
            "source_observation_ids":tuple(x.get("observation_id") for x in observations if _text(x.get("observation_id"))),
            "unresolved_hidden_dimensions":tuple(unresolved),
            "provenance":"filter_immutable_original_population_bomb_root_to_terminal_attempt_paths_v1"}


def _unresolved(paths):
    if len(paths)<2:return ()
    dims=[]
    for label,fn in (("planned_hit_count",lambda x:x["planned_hit_count"]),
                     ("critical_state",lambda x:tuple(a.get("ordered_hit",{}).get("critical_state") for a in x["attempts"] if a["outcome"]=="hit")),
                     ("roll_index",lambda x:tuple(a.get("ordered_hit",{}).get("roll_index") for a in x["attempts"] if a["outcome"]=="hit")),
                     ("reactive_branch_identity",lambda x:tuple((a.get("ordered_hit",{}).get("contact_reactive_damage"),a.get("ordered_hit",{}).get("contact_reactive_status")) for a in x["attempts"] if a["outcome"]=="hit"))):
        if len({_canonical(fn(x)) for x in paths})>1:dims.append(label)
    return tuple(dims)


def _owner(v,s):return isinstance(v,Mapping) and set(v)=={"session_id","side","slot_index","pokemon_id"} and v.get("session_id")==s and v.get("side") in {"self","opponent"} and isinstance(v.get("slot_index"),int) and not isinstance(v.get("slot_index"),bool) and v["slot_index"]>=0 and _text(v.get("pokemon_id"))
def _fraction(v):
    try:return v if isinstance(v,Fraction) else Fraction(v["numerator"],v["denominator"])
    except (TypeError,KeyError,ValueError,ZeroDivisionError):return None
def _path_id(p):return f"{p['root_id']}:{p['terminal_source_id']}:{_fingerprint({'e':p['edge_ids'],'a':p['attempts']})[:16]}"
def _fingerprint(v):return hashlib.sha256(_canonical(v).encode()).hexdigest()
def _canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=lambda x:str(x))
def _fd(v):return {"numerator":v.numerator,"denominator":v.denominator}
def _text(v):return isinstance(v,str) and bool(v)
def _pos(v):return isinstance(v,int) and not isinstance(v,bool) and v>0
def _nn(v):return isinstance(v,int) and not isinstance(v,bool) and v>=0
def _result(s,r):return {"status":s,"reason":r}
