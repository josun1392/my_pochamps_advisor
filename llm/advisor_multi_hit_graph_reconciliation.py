"""Detached historical retention and C5 reconciliation for exact multi-hit predictions.

Only family=fixed_two_hit is supported in v1.  Later graph families must add
their own strict validators rather than weakening this one.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping, Sequence

RETENTION_SCHEMA="historical-multi-hit-predictive-graph-v1"
RECONCILIATION_SCHEMA="observed-multi-hit-graph-reconciliation-v1"
FIXED_SCHEMA="detached-fixed-two-hit-per-hit-predictive-materialization-v1"
FAMILY="fixed_two_hit"
SUPPORTED_MOVES=frozenset({"double-hit","double-kick"})
TERMINAL_REASONS=frozenset({
    "target_fainted","attacker_fainted_from_contact_reactive_damage",
    "effect_spore_sleep_cancels_remaining_hits","all_hits_landed",
})


def retain_historical_fixed_two_hit_prediction(*, predictive_artifact: Mapping[str,Any],
                                               turn_number: int, decision_point: str,
                                               source_action_id: str | None = None) -> dict[str,Any]:
    checked=_validate_fixed_artifact(predictive_artifact)
    if checked.get("status")!="resolved":
        return checked
    if not _pos_int(turn_number) or not _text(decision_point):
        return _result("rejected","invalid_historical_multi_hit_identity")
    artifact=deepcopy(dict(predictive_artifact))
    source_action_id = source_action_id or artifact["action_id"]
    if not _text(source_action_id):
        return _result("rejected","historical_multi_hit_source_action_id_invalid")
    return {
        "status":"resolved","schema_version":RETENTION_SCHEMA,"family":FAMILY,
        "source_predictive_schema_version":FIXED_SCHEMA,
        "session_id":artifact["session_id"],"turn_number":turn_number,
        "actor":deepcopy(artifact["attacker"]),"target":deepcopy(artifact["target"]),
        "decision_point":decision_point,"action_id":artifact["action_id"],"source_action_id":source_action_id,"move_id":artifact["move_id"],
        "source_runtime_fingerprint":artifact["source_runtime_fingerprint"],
        "source_branch_fingerprint":artifact["source_branch_fingerprint"],
        "predictive_artifact":artifact,
        "predictive_artifact_fingerprint":_fingerprint(artifact),
        "retention_fingerprint":_fingerprint({
            "family":FAMILY,"session_id":artifact["session_id"],"turn_number":turn_number,
            "actor":artifact["attacker"],"target":artifact["target"],"decision_point":decision_point,
            "action_id":artifact["action_id"],"source_action_id":source_action_id,"move_id":artifact["move_id"],
            "source_runtime_fingerprint":artifact["source_runtime_fingerprint"],
            "source_branch_fingerprint":artifact["source_branch_fingerprint"],
            "predictive_artifact_fingerprint":_fingerprint(artifact),
        }),
        "provenance":"authenticated_pre_observation_fixed_two_hit_predictive_artifact_v1",
    }


def validate_historical_multi_hit_prediction(value: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("schema_version")!=RETENTION_SCHEMA:
        return _result("rejected","historical_multi_hit_prediction_missing")
    if value.get("family")!=FAMILY:
        return _result("rejected","unsupported_multi_hit_family")
    artifact=value.get("predictive_artifact")
    checked=_validate_fixed_artifact(artifact)
    if checked.get("status")!="resolved":
        return checked
    expected={
        "source_predictive_schema_version":FIXED_SCHEMA,
        "session_id":artifact["session_id"],"actor":artifact["attacker"],"target":artifact["target"],
        "action_id":artifact["action_id"],"move_id":artifact["move_id"],
        "source_runtime_fingerprint":artifact["source_runtime_fingerprint"],
        "source_branch_fingerprint":artifact["source_branch_fingerprint"],
    }
    if any(value.get(k)!=v for k,v in expected.items()):
        return _result("rejected","historical_multi_hit_identity_mismatch")
    if not _pos_int(value.get("turn_number")) or not _text(value.get("decision_point")) or not _text(value.get("source_action_id")):
        return _result("rejected","historical_multi_hit_identity_invalid")
    if value.get("predictive_artifact_fingerprint")!=_fingerprint(artifact):
        return _result("rejected","historical_multi_hit_predictive_fingerprint_mismatch")
    expected_retention=_fingerprint({
        "family":FAMILY,"session_id":value["session_id"],"turn_number":value["turn_number"],
        "actor":value["actor"],"target":value["target"],"decision_point":value["decision_point"],
        "action_id":value["action_id"],"source_action_id":value["source_action_id"],"move_id":value["move_id"],
        "source_runtime_fingerprint":value["source_runtime_fingerprint"],
        "source_branch_fingerprint":value["source_branch_fingerprint"],
        "predictive_artifact_fingerprint":value["predictive_artifact_fingerprint"],
    })
    if value.get("retention_fingerprint")!=expected_retention:
        return _result("rejected","historical_multi_hit_retention_fingerprint_mismatch")
    return deepcopy(dict(value))


def reconcile_observed_fixed_two_hit_graph(*, retained_prediction: Mapping[str,Any],
                                           source_execution_observation: Mapping[str,Any]|None=None,
                                           parent_observation: Mapping[str,Any]|None=None,
                                           hit_observations: Sequence[Mapping[str,Any]]|None=None,
                                           related_observations: Sequence[Mapping[str,Any]]|None=None) -> dict[str,Any]:
    retained=validate_historical_multi_hit_prediction(retained_prediction)
    if retained.get("status")!="resolved":
        return retained
    leaves=tuple(retained["predictive_artifact"]["terminal_leaves"])
    if parent_observation is None:
        return _reconciliation(retained=retained, status="incomplete", reason="insufficient_observation",
                               leaves=leaves, observations=(), unresolved=("action_outcome","ordered_hits"))
    error=_validate_source_execution(source_execution_observation,parent_observation,retained)
    if error:
        return _result("rejected",error)
    error=_validate_parent(parent_observation,retained)
    if error:
        return _result("rejected",error)
    hits=tuple(hit_observations or ())
    error=_validate_children(parent_observation,hits,retained)
    if error:
        return _result("rejected",error)
    related={row.get("observation_id"):row for row in (related_observations or ()) if isinstance(row,Mapping)}
    for child in hits:
        for oid in child["payload"].get("related_contact_observation_ids",()):
            if oid not in related:
                return _result("rejected","multi_hit_related_contact_observation_missing")
    payload=parent_observation["payload"]
    compatible=[]
    for leaf in leaves:
        if not _parent_matches_leaf(payload,leaf):
            continue
        if not _children_match_leaf(hits,leaf,related,retained):
            continue
        compatible.append(leaf)
    unresolved=_unresolved(compatible)
    return _reconciliation(retained=retained,status="resolved",reason=None,leaves=tuple(compatible),
                           observations=(parent_observation,*hits,*tuple(related.values())),unresolved=unresolved)


def _validate_fixed_artifact(value: Any) -> dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("status")!="evaluable" or value.get("schema_version")!=FIXED_SCHEMA:
        return _result("rejected","invalid_fixed_two_hit_predictive_artifact")
    if value.get("horizon")!="immediate_action_consequence" or value.get("move_id") not in SUPPORTED_MOVES:
        return _result("rejected","unsupported_fixed_two_hit_predictive_artifact")
    for key in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","action_id","move_id"):
        if not _text(value.get(key)):
            return _result("rejected","fixed_two_hit_predictive_identity_invalid")
    for key in ("attacker","target","decision_owner"):
        if not _owner(value.get(key),value["session_id"]):
            return _result("rejected","fixed_two_hit_predictive_owner_invalid")
    if value.get("attacker")!=value.get("decision_owner"):
        return _result("rejected","fixed_two_hit_attacker_decision_owner_mismatch")
    leaves=value.get("terminal_leaves")
    if not isinstance(leaves,(tuple,list)) or not leaves:
        return _result("rejected","fixed_two_hit_terminal_leaves_missing")
    mass=Fraction()
    seen=set()
    for leaf in leaves:
        if not isinstance(leaf,Mapping) or not _text(leaf.get("leaf_id")):
            return _result("rejected","fixed_two_hit_terminal_leaf_identity_invalid")
        stable=_stable_path_id(leaf)
        if stable in seen:
            return _result("rejected","fixed_two_hit_terminal_path_identity_duplicate")
        seen.add(stable)
        probability=_fraction(leaf.get("probability"))
        if probability is None or probability<=0:
            return _result("rejected","fixed_two_hit_terminal_leaf_probability_invalid")
        mass+=probability
        provenance=leaf.get("provenance")
        if not isinstance(provenance,Mapping):
            return _result("rejected","fixed_two_hit_terminal_leaf_provenance_missing")
        for k,v in {
            "session_id":value["session_id"],"source_runtime_fingerprint":value["source_runtime_fingerprint"],
            "source_branch_fingerprint":value["source_branch_fingerprint"],"attacker":value["attacker"],
            "target":value["target"],"move_id":value["move_id"],
        }.items():
            if provenance.get(k)!=v:
                return _result("rejected","fixed_two_hit_terminal_leaf_provenance_mismatch")
        hits=leaf.get("ordered_hits")
        if not isinstance(hits,(tuple,list)) or len(hits) not in {0,1,2}:
            return _result("rejected","fixed_two_hit_ordered_hits_invalid")
        if leaf.get("hit_state")=="miss":
            if hits:
                return _result("rejected","fixed_two_hit_miss_has_ordered_hits")
        elif leaf.get("hit_state")=="hit":
            if not hits:
                return _result("rejected","fixed_two_hit_hit_leaf_missing_hits")
        else:
            return _result("rejected","fixed_two_hit_hit_state_invalid")
        if any(hit.get("hit_index")!=i for i,hit in enumerate(hits,1) if isinstance(hit,Mapping)):
            return _result("rejected","fixed_two_hit_hit_index_invalid")
        if any(not _valid_predictive_hit(hit) for hit in hits):
            return _result("rejected","fixed_two_hit_ordered_hit_invalid")
        reason=leaf.get("consequences",{}).get("terminal_reason")
        if len(hits)==1 and reason not in {"target_fainted","attacker_fainted_from_contact_reactive_damage","effect_spore_sleep_cancels_remaining_hits"}:
            return _result("rejected","fixed_two_hit_one_hit_terminal_reason_invalid")
        if len(hits)==2 and reason not in {"target_fainted","attacker_fainted_from_contact_reactive_damage","all_hits_landed"}:
            return _result("rejected","fixed_two_hit_two_hit_terminal_reason_invalid")
    if mass!=Fraction(1,1) or _fraction(value.get("terminal_probability_mass"))!=Fraction(1,1):
        return _result("rejected","fixed_two_hit_terminal_probability_mass_not_one")
    return {"status":"resolved"}


def _validate_source_execution(obs: Mapping[str,Any]|None,parent: Mapping[str,Any],retained: Mapping[str,Any]) -> str|None:
    if (not isinstance(obs,Mapping) or obs.get("event_kind")!="executed_move_observed"
            or obs.get("source")!="ui_executed_move_confirmation"
            or obs.get("trust")!="user_confirmed_observation"
            or obs.get("confirmed") is not True or obs.get("observed") is not True):
        return "multi_hit_source_execution_observation_invalid"
    actor=retained["actor"]
    if (obs.get("session_id")!=retained["session_id"] or obs.get("turn_number")!=retained["turn_number"]
            or (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(actor["side"],actor["slot_index"],actor["pokemon_id"])):
        return "multi_hit_source_execution_identity_mismatch"
    payload=obs.get("payload")
    if not isinstance(payload,Mapping) or payload.get("move_id")!=retained["move_id"] or payload.get("source_action_id")!=retained["source_action_id"]:
        return "multi_hit_source_execution_payload_mismatch"
    if parent.get("payload",{}).get("source_execution_observation_id")!=obs.get("observation_id"):
        return "multi_hit_source_execution_link_mismatch"
    if not _pos_int(obs.get("observation_sequence")) or parent.get("observation_sequence",0)<=obs["observation_sequence"]:
        return "multi_hit_source_execution_order_invalid"
    return None


def _validate_parent(obs: Mapping[str,Any],retained: Mapping[str,Any]) -> str|None:
    if (not isinstance(obs,Mapping) or obs.get("event_kind")!="multi_hit_action_result_observed"
            or obs.get("source")!="ui_multi_hit_action_result_confirmation"
            or obs.get("trust")!="user_confirmed_observation"
            or obs.get("confirmed") is not True or obs.get("observed") is not True):
        return "invalid_multi_hit_parent_observation"
    p=obs.get("payload")
    expected_keys={"family","decision_point","action_id","move_id","actor","target","action_outcome",
                   "landed_hit_count","terminal_reason","source_execution_observation_id",
                   "predictive_artifact_fingerprint"}
    if not isinstance(p,Mapping) or set(p)!=expected_keys:
        return "invalid_multi_hit_parent_payload"
    if p.get("family")!=FAMILY or p.get("predictive_artifact_fingerprint")!=retained["predictive_artifact_fingerprint"]:
        return "multi_hit_parent_prediction_mismatch"
    for key in ("decision_point","action_id","move_id"):
        if p.get(key)!=retained[key]:
            return f"multi_hit_parent_{key}_mismatch"
    if p.get("actor")!=retained["actor"] or p.get("target")!=retained["target"]:
        return "multi_hit_parent_actor_target_mismatch"
    if obs.get("session_id")!=retained["session_id"] or obs.get("turn_number")!=retained["turn_number"]:
        return "multi_hit_parent_session_turn_mismatch"
    actor=retained["actor"]
    if (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(actor["side"],actor["slot_index"],actor["pokemon_id"]):
        return "multi_hit_parent_outer_actor_mismatch"
    outcome=p.get("action_outcome"); count=p.get("landed_hit_count"); reason=p.get("terminal_reason")
    if outcome=="miss":
        if count!=0 or reason!="action_miss": return "multi_hit_parent_miss_contract_invalid"
    elif outcome=="landed":
        if count not in {1,2} or reason not in TERMINAL_REASONS: return "multi_hit_parent_landed_contract_invalid"
    else:
        return "multi_hit_parent_action_outcome_invalid"
    return None


def _validate_children(parent: Mapping[str,Any],hits: Sequence[Mapping[str,Any]],retained: Mapping[str,Any]) -> str|None:
    pp=parent["payload"]; count=pp["landed_hit_count"]
    if len(hits)!=count:
        return "multi_hit_ordered_hit_count_mismatch"
    seen=set()
    for index,obs in enumerate(hits,1):
        if (not isinstance(obs,Mapping) or obs.get("event_kind")!="multi_hit_ordered_hit_observed"
                or obs.get("source")!="ui_multi_hit_ordered_hit_confirmation"
                or obs.get("trust")!="user_confirmed_observation"
                or obs.get("confirmed") is not True or obs.get("observed") is not True):
            return "invalid_multi_hit_ordered_hit_observation"
        p=obs.get("payload")
        required={"family","decision_point","action_id","move_id","actor","target","parent_multi_hit_observation_id",
                  "hit_index","hp_before","hp_after","target_fainted_after_hit","critical_state","related_contact_observation_ids"}
        if not isinstance(p,Mapping) or set(p)!=required:
            return "invalid_multi_hit_ordered_hit_payload"
        if p["hit_index"] in seen or p["hit_index"]!=index:
            return "multi_hit_ordered_hit_index_invalid"
        seen.add(p["hit_index"])
        if (p["family"]!=FAMILY or p["decision_point"]!=retained["decision_point"]
                or p["action_id"]!=retained["action_id"] or p["move_id"]!=retained["move_id"]
                or p["actor"]!=retained["actor"] or p["target"]!=retained["target"]):
            return "multi_hit_ordered_hit_identity_mismatch"
        if p["parent_multi_hit_observation_id"]!=parent.get("observation_id"):
            return "multi_hit_ordered_hit_parent_mismatch"
        if not _pos_int(obs.get("observation_sequence")) or obs["observation_sequence"]<=parent.get("observation_sequence",0):
            return "multi_hit_ordered_hit_order_invalid"
        if index>1 and obs["observation_sequence"]<=hits[index-2].get("observation_sequence",0):
            return "multi_hit_ordered_hit_order_invalid"
        if obs.get("session_id")!=retained["session_id"] or obs.get("turn_number")!=retained["turn_number"]:
            return "multi_hit_ordered_hit_session_turn_mismatch"
        actor=retained["actor"]
        if (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(actor["side"],actor["slot_index"],actor["pokemon_id"]):
            return "multi_hit_ordered_hit_outer_actor_mismatch"
        if not _nonneg(p["hp_before"]) or not _nonneg(p["hp_after"]) or p["hp_after"]>p["hp_before"]:
            return "multi_hit_ordered_hit_hp_invalid"
        if p["target_fainted_after_hit"] is not (p["hp_after"]==0):
            return "multi_hit_ordered_hit_faint_mismatch"
        if p["critical_state"] not in {None,"critical","non_critical"}:
            return "multi_hit_ordered_hit_critical_invalid"
        ids=p["related_contact_observation_ids"]
        if not isinstance(ids,(tuple,list)) or len(ids)!=len(set(ids)) or any(not _text(x) for x in ids):
            return "multi_hit_ordered_hit_contact_links_invalid"
    if count==1 and pp["terminal_reason"]=="all_hits_landed":
        return "multi_hit_parent_terminal_reason_conflicts_with_hit_count"
    if count==2 and pp["terminal_reason"]=="effect_spore_sleep_cancels_remaining_hits":
        return "multi_hit_parent_effect_spore_after_second_hit_invalid"
    return None


def _parent_matches_leaf(parent: Mapping[str,Any],leaf: Mapping[str,Any]) -> bool:
    hits=leaf["ordered_hits"]; reason=leaf.get("consequences",{}).get("terminal_reason")
    if parent["action_outcome"]=="miss":
        return leaf.get("hit_state")=="miss" and len(hits)==0
    return leaf.get("hit_state")=="hit" and len(hits)==parent["landed_hit_count"] and reason==parent["terminal_reason"]


def _children_match_leaf(observed: Sequence[Mapping[str,Any]],leaf: Mapping[str,Any],
                         related: Mapping[str,Mapping[str,Any]],retained: Mapping[str,Any]) -> bool:
    predicted=leaf["ordered_hits"]
    if len(observed)!=len(predicted):
        return False
    for obs,hit in zip(observed,predicted):
        p=obs["payload"]
        if (hit.get("hit_index")!=p["hit_index"] or hit.get("pre_hp")!=p["hp_before"]
                or hit.get("post_hp")!=p["hp_after"] or (hit.get("post_hp")==0) is not p["target_fainted_after_hit"]):
            return False
        if p["critical_state"] is not None and hit.get("critical_state")!=p["critical_state"]:
            return False
        for oid in p["related_contact_observation_ids"]:
            if not _related_contact_matches_hit(related[oid],hit,p,obs,retained):
                return False
    return True


def _related_contact_matches_hit(obs: Mapping[str,Any],hit: Mapping[str,Any],child: Mapping[str,Any],
                                 child_observation: Mapping[str,Any],retained: Mapping[str,Any]) -> bool:
    kind=obs.get("event_kind"); p=obs.get("payload")
    if (not isinstance(p,Mapping)
            or obs.get("session_id")!=retained["session_id"]
            or obs.get("turn_number")!=retained["turn_number"]
            or obs.get("trust")!="user_confirmed_observation"
            or obs.get("confirmed") is not True or obs.get("observed") is not True
            or not _pos_int(obs.get("observation_sequence"))
            or child_observation.get("session_id")!=retained["session_id"]
            or child_observation.get("turn_number")!=retained["turn_number"]
            or p.get("source_action_id")!=retained["source_action_id"]
            or p.get("move_id")!=retained["move_id"]):
        return False
    actor,target=retained["actor"],retained["target"]
    if ((p.get("attacker_side"),p.get("attacker_slot_index"),p.get("attacker_pokemon_id"))
            !=(actor["side"],actor["slot_index"],actor["pokemon_id"])
            or (p.get("defender_side"),p.get("defender_slot_index"),p.get("defender_pokemon_id"))
            !=(target["side"],target["slot_index"],target["pokemon_id"])):
        return False
    if kind=="contact_reactive_damage_result_observed":
        if obs.get("source")!="runtime_observed_contact_reactive_damage_result":
            return False
        embedded=hit.get("contact_reactive_damage")
        authority=embedded.get("authority") if isinstance(embedded,Mapping) else None
        source_hit=authority.get("source_hit") if isinstance(authority,Mapping) else None
        return (isinstance(authority,Mapping) and authority.get("outcome")=="applies"
                and p.get("hp_before")==authority.get("pre_hp") and p.get("hp_after")==authority.get("post_hp")
                and p.get("source_hit_actual_damage")==source_hit.get("actual_damage")
                and p.get("source_hit_target_routing")==source_hit.get("target_routing")
                and source_hit.get("hit_index")==child["hit_index"]
                and source_hit.get("target_pre_hp")==child["hp_before"]
                and source_hit.get("target_post_hp")==child["hp_after"]
                and _canonical(p.get("ordered_sources"))==_canonical(authority.get("ordered_sources")))
    if kind=="contact_reactive_status_result_observed":
        if obs.get("source")!="runtime_observed_contact_reactive_status_result":
            return False
        embedded=hit.get("contact_reactive_status")
        authority=embedded.get("authority") if isinstance(embedded,Mapping) else None
        source_hit=authority.get("source_hit") if isinstance(authority,Mapping) else None
        return (isinstance(embedded,Mapping) and isinstance(authority,Mapping)
                and p.get("reactive_ability")==authority.get("reactive_ability")
                and p.get("outcome")==embedded.get("branch")
                and p.get("hp_before")==child["hp_before"] and p.get("hp_after")==child["hp_after"]
                and source_hit.get("hit_index")==child["hit_index"]
                and source_hit.get("actual_damage")==child["hp_before"]-child["hp_after"]
                and source_hit.get("target_pre_hp")==child["hp_before"]
                and source_hit.get("target_post_hp")==child["hp_after"]
                and source_hit.get("target_routing")=="target")
    return False

def _reconciliation(*,retained:Mapping[str,Any],status:str,reason:str|None,leaves:Sequence[Mapping[str,Any]],
                    observations:Sequence[Mapping[str,Any]],unresolved:Sequence[str]) -> dict[str,Any]:
    mass=sum((_fraction(row.get("probability")) or Fraction() for row in leaves),Fraction())
    outcome=None
    if status=="resolved":
        outcome="incompatible_observation" if not leaves else "uniquely_matched" if len(leaves)==1 else "multiple_compatible_paths"
    return {
        "status":status,"schema_version":RECONCILIATION_SCHEMA,"reason":reason,
        "source_prediction_kind":"fixed_two_hit_ordered_graph",
        "family":FAMILY,"session_id":retained["session_id"],"turn_number":retained["turn_number"],
        "actor":deepcopy(retained["actor"]),"target":deepcopy(retained["target"]),
        "decision_point":retained["decision_point"],"action_id":retained["action_id"],"move_id":retained["move_id"],
        "predictive_artifact_fingerprint":retained["predictive_artifact_fingerprint"],
        "match_outcome":outcome,
        "compatible_terminal_leaf_ids":tuple(_stable_path_id(row) for row in leaves),
        "compatible_source_paths":tuple({
            "leaf_id":row["leaf_id"],"source_path_id":_stable_path_id(row),
            "ordered_hits":tuple({"hit_index":h.get("hit_index"),"critical_state":h.get("critical_state"),
                                  "roll_index":h.get("roll_index"),"pre_hp":h.get("pre_hp"),"post_hp":h.get("post_hp")}
                                 for h in row["ordered_hits"])
        } for row in leaves),
        "compatible_original_probability_mass":_fd(mass),
        "probability_normalization":"none_preserve_original_mass",
        "source_observation_ids":tuple(row.get("observation_id") for row in observations if _text(row.get("observation_id"))),
        "unresolved_hidden_dimensions":tuple(unresolved),
        "provenance":"filter_immutable_original_fixed_two_hit_terminal_leaves_v1",
    }


def _unresolved(leaves: Sequence[Mapping[str,Any]]) -> tuple[str,...]:
    if len(leaves)<2:return ()
    dims=[]
    for label,extract in (
        ("terminal_leaf_id",lambda l:l.get("leaf_id")),
        ("critical_state",lambda l:tuple(h.get("critical_state") for h in l.get("ordered_hits",()))),
        ("roll_index",lambda l:tuple(h.get("roll_index") for h in l.get("ordered_hits",()))),
        ("sturdy",lambda l:l.get("consequences",{}).get("sturdy")),
        ("focus_sash",lambda l:l.get("consequences",{}).get("focus_sash")),
        ("contact_reactive",lambda l:tuple((h.get("contact_reactive_damage"),h.get("contact_reactive_status")) for h in l.get("ordered_hits",()))),
    ):
        if len({_canonical(extract(x)) for x in leaves})>1:dims.append(label)
    return tuple(dims)


def _valid_predictive_hit(hit: Any) -> bool:
    return (isinstance(hit,Mapping) and _pos_int(hit.get("hit_index")) and hit["hit_index"] in {1,2}
            and _nonneg(hit.get("pre_hp")) and _nonneg(hit.get("post_hp")) and hit["post_hp"]<=hit["pre_hp"]
            and hit.get("critical_state") in {"critical","non_critical"} and isinstance(hit.get("roll_index"),int)
            and not isinstance(hit.get("roll_index"),bool) and 0<=hit["roll_index"]<16)


def _owner(value:Any,session:str)->bool:
    return isinstance(value,Mapping) and set(value)=={"session_id","side","slot_index","pokemon_id"} and value.get("session_id")==session and value.get("side") in {"self","opponent"} and isinstance(value.get("slot_index"),int) and not isinstance(value.get("slot_index"),bool) and value["slot_index"]>=0 and _text(value.get("pokemon_id"))


def _fraction(value:Any)->Fraction|None:
    try:
        if isinstance(value,Fraction):return value
        return Fraction(value["numerator"],value["denominator"])
    except (TypeError,KeyError,ValueError,ZeroDivisionError):
        return None


def _stable_path_id(leaf:Mapping[str,Any])->str:
    return f"{leaf.get('leaf_id')}:{_fingerprint(leaf)[:16]}"

def _fingerprint(value:Any)->str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _canonical(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=lambda x:str(x))


def _fd(value:Fraction)->dict[str,int]:
    return {"numerator":value.numerator,"denominator":value.denominator}


def _text(value:Any)->bool:return isinstance(value,str) and bool(value)
def _pos_int(value:Any)->bool:return isinstance(value,int) and not isinstance(value,bool) and value>0
def _nonneg(value:Any)->bool:return isinstance(value,int) and not isinstance(value,bool) and value>=0
def _result(status:str,reason:str)->dict[str,Any]:return {"status":status,"reason":reason}
