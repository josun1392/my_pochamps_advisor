"""Strict C5 retention/reconciliation for ordinary variable 2--5 hit graphs."""
from __future__ import annotations
import hashlib, json
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping, Sequence

from llm.advisor_multi_hit_graph_reconciliation import _consumed_related_observations, _related_contact_matches_hit

RETENTION_SCHEMA="historical-multi-hit-predictive-graph-v1"
RECONCILIATION_SCHEMA="observed-multi-hit-graph-reconciliation-v1"
PREDICTIVE_SCHEMA="detached-variable-two-to-five-hit-per-hit-predictive-materialization-v1"
FAMILY="variable_two_to_five"
SUPPORTED_MOVES=frozenset({"bullet-seed","rock-blast"})
TERMINAL_REASONS=frozenset({"target_fainted","attacker_fainted_from_contact_reactive_damage","effect_spore_sleep_cancels_remaining_hits","selected_hit_count_reached"})

def retain_historical_variable_two_to_five_prediction(*,predictive_artifact:Mapping[str,Any],turn_number:int,decision_point:str,source_action_id:str|None=None)->dict[str,Any]:
    checked=_validate_artifact(predictive_artifact)
    if checked.get("status")!="resolved": return checked
    if not _pos(turn_number) or not _text(decision_point): return _result("rejected","invalid_historical_multi_hit_identity")
    a=deepcopy(dict(predictive_artifact)); source_action_id=source_action_id or a["action_id"]
    if not _text(source_action_id): return _result("rejected","historical_multi_hit_source_action_id_invalid")
    fp=_fingerprint(a)
    core={"family":FAMILY,"session_id":a["session_id"],"turn_number":turn_number,"actor":a["attacker"],"target":a["target"],
          "decision_point":decision_point,"action_id":a["action_id"],"source_action_id":source_action_id,"move_id":a["move_id"],
          "source_runtime_fingerprint":a["source_runtime_fingerprint"],"source_branch_fingerprint":a["source_branch_fingerprint"],
          "predictive_artifact_fingerprint":fp}
    return {"status":"resolved","schema_version":RETENTION_SCHEMA,"family":FAMILY,"source_predictive_schema_version":PREDICTIVE_SCHEMA,
            **deepcopy(core),"predictive_artifact":a,"retention_fingerprint":_fingerprint(core),
            "provenance":"authenticated_pre_observation_variable_two_to_five_predictive_artifact_v1"}

def validate_historical_variable_two_to_five_prediction(value:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("schema_version")!=RETENTION_SCHEMA: return _result("rejected","historical_multi_hit_prediction_missing")
    if value.get("family")!=FAMILY: return _result("rejected","unsupported_multi_hit_family")
    a=value.get("predictive_artifact"); checked=_validate_artifact(a)
    if checked.get("status")!="resolved": return checked
    expected={"source_predictive_schema_version":PREDICTIVE_SCHEMA,"session_id":a["session_id"],"actor":a["attacker"],"target":a["target"],
              "action_id":a["action_id"],"move_id":a["move_id"],"source_runtime_fingerprint":a["source_runtime_fingerprint"],
              "source_branch_fingerprint":a["source_branch_fingerprint"]}
    if any(value.get(k)!=v for k,v in expected.items()): return _result("rejected","historical_multi_hit_identity_mismatch")
    if not _pos(value.get("turn_number")) or not _text(value.get("decision_point")) or not _text(value.get("source_action_id")): return _result("rejected","historical_multi_hit_identity_invalid")
    if value.get("predictive_artifact_fingerprint")!=_fingerprint(a): return _result("rejected","historical_multi_hit_predictive_fingerprint_mismatch")
    core={k:value[k] for k in ("family","session_id","turn_number","actor","target","decision_point","action_id","source_action_id","move_id","source_runtime_fingerprint","source_branch_fingerprint","predictive_artifact_fingerprint")}
    if value.get("retention_fingerprint")!=_fingerprint(core): return _result("rejected","historical_multi_hit_retention_fingerprint_mismatch")
    return deepcopy(dict(value))

def reconcile_observed_variable_two_to_five_hit_graph(*,retained_prediction:Mapping[str,Any],source_execution_observation:Mapping[str,Any]|None=None,
        parent_observation:Mapping[str,Any]|None=None,hit_observations:Sequence[Mapping[str,Any]]|None=None,related_observations:Sequence[Mapping[str,Any]]|None=None)->dict[str,Any]:
    r=validate_historical_variable_two_to_five_prediction(retained_prediction)
    if r.get("status")!="resolved": return r
    if parent_observation is None:
        return _incomplete_reconciliation(r)
    err=_validate_execution(source_execution_observation,parent_observation,r) or _validate_parent(parent_observation,r)
    if err: return _result("rejected",err)
    hits=tuple(hit_observations or ())
    err=_validate_children(parent_observation,hits,r)
    if err: return _result("rejected",err)
    related={x.get("observation_id"):x for x in (related_observations or ()) if isinstance(x,Mapping)}
    for h in hits:
        if any(oid not in related for oid in h["payload"].get("related_contact_observation_ids",())): return _result("rejected","multi_hit_related_contact_observation_missing")
    consumed_related=_consumed_related_observations(hits,related)
    compatible=_compatible_paths(r["predictive_artifact"],parent_observation["payload"],hits,related,r)
    return _reconciliation(r,"resolved",None,compatible,(parent_observation,*hits,*consumed_related),_unresolved(compatible))

def _validate_artifact(v:Any)->dict[str,Any]:
    if not isinstance(v,Mapping) or v.get("status")!="evaluable" or v.get("schema_version")!=PREDICTIVE_SCHEMA: return _result("rejected","invalid_variable_two_to_five_predictive_artifact")
    if v.get("horizon")!="immediate_action_consequence" or v.get("move_id") not in SUPPORTED_MOVES: return _result("rejected","unsupported_variable_two_to_five_predictive_artifact")
    for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","action_id","move_id"):
        if not _text(v.get(k)): return _result("rejected","variable_two_to_five_predictive_identity_invalid")
    for k in ("attacker","target","decision_owner"):
        if not _owner(v.get(k),v["session_id"]): return _result("rejected","variable_two_to_five_predictive_owner_invalid")
    if v["attacker"]!=v["decision_owner"]: return _result("rejected","variable_two_to_five_attacker_decision_owner_mismatch")
    execution=v.get("execution_authority")
    if (not isinstance(execution,Mapping) or execution.get("status")!="resolved"
            or execution.get("schema_version")!="runtime-d0-variable-two-to-five-hit-count-execution-authority-v1"):
        return _result("rejected","variable_two_to_five_execution_authority_invalid")
    for key,expected in (("session_id",v["session_id"]),("source_runtime_fingerprint",v["source_runtime_fingerprint"]),
                         ("source_branch_fingerprint",v["source_branch_fingerprint"]),("action_id",v["action_id"]),
                         ("move_id",v["move_id"]),("attacker",v["attacker"]),("target",v["target"])):
        if execution.get(key)!=expected:return _result("rejected","variable_two_to_five_execution_authority_identity_mismatch")
    count_execution=execution.get("hit_count_execution")
    distribution=count_execution.get("distribution") if isinstance(count_execution,Mapping) else None
    if (not isinstance(count_execution,Mapping) or count_execution.get("status")!="resolved"
            or count_execution.get("semantics")!="canonical_standard_two_to_five_hit_count_before_per_hit_execution"
            or _fraction(count_execution.get("root_mass"))!=Fraction(1,1) or not isinstance(distribution,(tuple,list))):
        return _result("rejected","variable_two_to_five_hit_count_execution_invalid")
    dist={}
    for row in distribution:
        if not isinstance(row,Mapping) or row.get("hit_count") not in {2,3,4,5}:return _result("rejected","variable_two_to_five_hit_count_distribution_invalid")
        prob=_fraction(row.get("probability"))
        if prob is None or prob<=0 or row["hit_count"] in dist:return _result("rejected","variable_two_to_five_hit_count_distribution_invalid")
        dist[row["hit_count"]]=prob
    if sum(dist.values(),Fraction())!=Fraction(1,1):return _result("rejected","variable_two_to_five_hit_count_distribution_mass_invalid")
    accuracy_execution=execution.get("accuracy_execution")
    if not isinstance(accuracy_execution,Mapping) or accuracy_execution.get("status")!="resolved" or accuracy_execution.get("semantics")!="action_level_once_before_hit_sequence":
        return _result("rejected","variable_two_to_five_accuracy_execution_invalid")
    action_accuracy=v.get("action_accuracy")
    accuracy=action_accuracy.get("probability_percent") if isinstance(action_accuracy,Mapping) else None
    if not isinstance(accuracy,int) or isinstance(accuracy,bool) or not 0<=accuracy<=100:return _result("rejected","variable_two_to_five_action_accuracy_invalid")
    roots,nodes,edges=v.get("terminal_leaf_roots"),v.get("terminal_leaf_nodes"),v.get("terminal_leaf_edges")
    if not isinstance(roots,(tuple,list)) or not isinstance(nodes,(tuple,list)) or not isinstance(edges,(tuple,list)) or not roots: return _result("rejected","variable_two_to_five_graph_missing")
    if _fraction(v.get("terminal_probability_mass"))!=Fraction(1,1): return _result("rejected","variable_two_to_five_terminal_probability_mass_not_one")
    node_ids=[n.get("node_id") for n in nodes if isinstance(n,Mapping)]
    edge_ids=[e.get("edge_id") for e in edges if isinstance(e,Mapping)]
    if len(node_ids)!=len(nodes) or len(node_ids)!=len(set(node_ids)) or any(not _text(x) for x in node_ids): return _result("rejected","variable_two_to_five_node_identity_invalid")
    if len(edge_ids)!=len(edges) or len(edge_ids)!=len(set(edge_ids)) or any(not _text(x) for x in edge_ids): return _result("rejected","variable_two_to_five_edge_identity_invalid")
    root_mass=Fraction(); selected=[]
    for root in roots:
        if not isinstance(root,Mapping) or not _text(root.get("root_id")): return _result("rejected","variable_two_to_five_root_identity_invalid")
        p=_fraction(root.get("probability"))
        if p is None or p<=0: return _result("rejected","variable_two_to_five_root_probability_invalid")
        root_mass+=p
        c=root.get("selected_hit_count")
        if c is None:
            if root.get("root_id")!="miss" or root.get("terminal") is not True: return _result("rejected","variable_two_to_five_miss_root_invalid")
        else:
            if c not in {2,3,4,5} or root.get("terminal") is not False or root.get("node_id") not in node_ids: return _result("rejected","variable_two_to_five_selected_count_root_invalid")
            selected.append(c)
    if root_mass!=Fraction(1,1) or len(selected)!=len(set(selected)): return _result("rejected","variable_two_to_five_root_mass_or_count_invalid")
    if set(selected)!=set(dist):return _result("rejected","variable_two_to_five_root_distribution_identity_mismatch")
    hit_factor=Fraction(accuracy,100);miss_factor=Fraction(100-accuracy,100)
    for root in roots:
        selected_count=root.get("selected_hit_count")
        expected=miss_factor if selected_count is None else hit_factor*dist[selected_count]
        if _fraction(root.get("probability"))!=expected:return _result("rejected","variable_two_to_five_root_probability_mismatch")
    for node in nodes:
        if node.get("selected_hit_count") not in {2,3,4,5} or not isinstance(node.get("completed_hit_count"),int) or not 0<=node["completed_hit_count"]<node["selected_hit_count"]: return _result("rejected","variable_two_to_five_node_state_invalid")
    for edge in edges:
        if edge.get("from_node_id") not in node_ids or (edge.get("terminal") is False and edge.get("to_node_id") not in node_ids): return _result("rejected","variable_two_to_five_edge_link_invalid")
        cp=_fraction(edge.get("conditional_probability")); hit=edge.get("ordered_hit")
        if cp is None or cp<=0 or not _valid_hit(hit): return _result("rejected","variable_two_to_five_edge_probability_or_hit_invalid")
        source=next(n for n in nodes if n["node_id"]==edge["from_node_id"])
        if (hit.get("selected_hit_count")!=source["selected_hit_count"] or hit.get("hit_index")!=source["completed_hit_count"]+1
                or hit.get("pre_hp")!=source.get("target_hp")):
            return _result("rejected","variable_two_to_five_edge_count_identity_invalid")
        if edge.get("terminal") is False:
            destination=next(n for n in nodes if n["node_id"]==edge["to_node_id"])
            if (destination.get("selected_hit_count")!=source["selected_hit_count"]
                    or destination.get("completed_hit_count")!=source["completed_hit_count"]+1
                    or destination.get("target_hp")!=hit.get("post_hp")):
                return _result("rejected","variable_two_to_five_edge_destination_state_invalid")
        else:
            reason=edge.get("terminal_reason")
            if reason not in TERMINAL_REASONS:return _result("rejected","variable_two_to_five_terminal_reason_invalid")
            if reason=="target_fainted" and hit.get("post_hp")!=0:return _result("rejected","variable_two_to_five_target_faint_terminal_invalid")
            if reason=="selected_hit_count_reached" and (hit.get("hit_index")!=hit.get("selected_hit_count") or hit.get("post_hp")==0):
                return _result("rejected","variable_two_to_five_selected_count_terminal_invalid")
            if reason=="attacker_fainted_from_contact_reactive_damage" and hit.get("attacker_fainted_from_reactive") is not True:
                return _result("rejected","variable_two_to_five_attacker_faint_terminal_invalid")
            if reason=="effect_spore_sleep_cancels_remaining_hits":
                reactive=hit.get("contact_reactive_status")
                if not isinstance(reactive,Mapping) or reactive.get("branch")!="sleep":
                    return _result("rejected","variable_two_to_five_effect_spore_terminal_invalid")
    outgoing={}
    for e in edges: outgoing.setdefault(e["from_node_id"],[]).append(e)
    for node in nodes:
        es=outgoing.get(node["node_id"],())
        if not es: return _result("rejected","variable_two_to_five_nonterminal_node_has_no_edges")
        if sum((_fraction(e["conditional_probability"]) or Fraction() for e in es),Fraction())!=Fraction(1,1):
            return _result("rejected","variable_two_to_five_outgoing_probability_mass_not_one")
    return {"status":"resolved"}

def _compatible_paths(a:Mapping[str,Any],parent:Mapping[str,Any],observed:Sequence[Mapping[str,Any]],
                      related:Mapping[str,Mapping[str,Any]],retained:Mapping[str,Any])->tuple[dict[str,Any],...]:
    if parent["action_outcome"]=="miss":
        root=next((r for r in a["terminal_leaf_roots"] if r.get("selected_hit_count") is None and r.get("terminal") is True),None)
        if root is None:return ()
        return ({"root_id":root["root_id"],"selected_hit_count":None,"probability":_fraction(root["probability"]),
                 "ordered_hits":(),"terminal_reason":"action_miss","edge_ids":(),"terminal_source_id":root["root_id"]},)
    outgoing={}
    for e in a["terminal_leaf_edges"]:outgoing.setdefault(e["from_node_id"],[]).append(e)
    out=[]
    for root in a["terminal_leaf_roots"]:
        selected=root.get("selected_hit_count")
        if selected is None:continue
        states=[(root["node_id"],_fraction(root["probability"]),(),())]
        for obs in observed:
            next_states=[]
            for nid,mass,hits,eids in states:
                for e in outgoing.get(nid,()):
                    if not _edge_matches_observation(e,obs,related,retained):continue
                    nm=mass*(_fraction(e["conditional_probability"]) or Fraction())
                    nh=hits+(deepcopy(e["ordered_hit"]),);ne=eids+(e["edge_id"],)
                    if len(nh)<len(observed):
                        if e.get("terminal"):continue
                        next_states.append((e["to_node_id"],nm,nh,ne))
                    elif e.get("terminal") and e.get("terminal_reason")==parent["terminal_reason"]:
                        out.append({"root_id":root["root_id"],"selected_hit_count":selected,"probability":nm,"ordered_hits":nh,
                                    "terminal_reason":e["terminal_reason"],"edge_ids":ne,"terminal_source_id":e["edge_id"]})
            states=next_states
            if not states and len(out)==0 and obs is not observed[-1]:break
    return tuple(out)

def _edge_matches_observation(edge:Mapping[str,Any],obs:Mapping[str,Any],related:Mapping[str,Mapping[str,Any]],retained:Mapping[str,Any])->bool:
    h=edge.get("ordered_hit");p=obs["payload"]
    if not (isinstance(h,Mapping) and h.get("hit_index")==p["hit_index"] and h.get("pre_hp")==p["hp_before"] and h.get("post_hp")==p["hp_after"]
            and (p["critical_state"] is None or h.get("critical_state")==p["critical_state"])):
        return False
    return all(_related_contact_matches_hit(related[oid],h,p,obs,retained) for oid in p["related_contact_observation_ids"])

def _incomplete_reconciliation(r:Mapping[str,Any])->dict[str,Any]:
    a=r["predictive_artifact"]
    roots=tuple({"root_id":x.get("root_id"),"selected_hit_count":x.get("selected_hit_count"),"probability":deepcopy(x.get("probability"))} for x in a["terminal_leaf_roots"])
    return {"status":"incomplete","schema_version":RECONCILIATION_SCHEMA,"reason":"insufficient_observation",
            "source_prediction_kind":"variable_two_to_five_ordered_graph","family":FAMILY,"session_id":r["session_id"],"turn_number":r["turn_number"],
            "actor":deepcopy(r["actor"]),"target":deepcopy(r["target"]),"decision_point":r["decision_point"],"action_id":r["action_id"],"move_id":r["move_id"],
            "predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"],"match_outcome":None,
            "compatible_terminal_leaf_ids":(),"compatible_source_paths":roots,
            "compatible_original_probability_mass":{"numerator":1,"denominator":1},"probability_normalization":"none_preserve_original_mass",
            "source_observation_ids":(),"unresolved_hidden_dimensions":("action_outcome","ordered_hits","selected_hit_count"),
            "provenance":"preserve_immutable_original_variable_two_to_five_graph_without_observation_v1"}

def _validate_execution(obs,parent,r):
    if not isinstance(obs,Mapping) or obs.get("event_kind")!="executed_move_observed" or obs.get("source")!="ui_executed_move_confirmation" or obs.get("trust")!="user_confirmed_observation" or obs.get("confirmed") is not True or obs.get("observed") is not True: return "multi_hit_source_execution_observation_invalid"
    a=r["actor"]; p=obs.get("payload")
    if obs.get("session_id")!=r["session_id"] or obs.get("turn_number")!=r["turn_number"] or (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(a["side"],a["slot_index"],a["pokemon_id"]): return "multi_hit_source_execution_identity_mismatch"
    if not isinstance(p,Mapping) or p.get("move_id")!=r["move_id"] or p.get("source_action_id")!=r["source_action_id"]: return "multi_hit_source_execution_payload_mismatch"
    if parent.get("payload",{}).get("source_execution_observation_id")!=obs.get("observation_id"): return "multi_hit_source_execution_link_mismatch"
    if not _pos(obs.get("observation_sequence")) or not _pos(parent.get("observation_sequence")) or parent["observation_sequence"]<=obs["observation_sequence"]:
        return "multi_hit_source_execution_order_invalid"
    return None

def _validate_parent(obs,r):
    if not isinstance(obs,Mapping) or obs.get("event_kind")!="multi_hit_action_result_observed" or obs.get("source")!="ui_multi_hit_action_result_confirmation" or obs.get("trust")!="user_confirmed_observation" or obs.get("confirmed") is not True or obs.get("observed") is not True: return "invalid_multi_hit_parent_observation"
    p=obs.get("payload"); keys={"family","decision_point","action_id","move_id","actor","target","action_outcome","landed_hit_count","terminal_reason","source_execution_observation_id","predictive_artifact_fingerprint"}
    if not isinstance(p,Mapping) or set(p)!=keys: return "invalid_multi_hit_parent_payload"
    if p.get("family")!=FAMILY or p.get("predictive_artifact_fingerprint")!=r["predictive_artifact_fingerprint"]: return "multi_hit_parent_prediction_mismatch"
    if any(p.get(k)!=r[k] for k in ("decision_point","action_id","move_id")) or p.get("actor")!=r["actor"] or p.get("target")!=r["target"]: return "multi_hit_parent_identity_mismatch"
    if obs.get("session_id")!=r["session_id"] or obs.get("turn_number")!=r["turn_number"]: return "multi_hit_parent_session_turn_mismatch"
    a=r["actor"]
    if (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(a["side"],a["slot_index"],a["pokemon_id"]):
        return "multi_hit_parent_outer_actor_mismatch"
    if not _pos(obs.get("observation_sequence")):
        return "multi_hit_parent_observation_sequence_invalid"
    o,c,t=p.get("action_outcome"),p.get("landed_hit_count"),p.get("terminal_reason")
    if o=="miss": return None if c==0 and t=="action_miss" else "multi_hit_parent_miss_contract_invalid"
    if o!="landed" or c not in {1,2,3,4,5} or t not in TERMINAL_REASONS: return "multi_hit_parent_landed_contract_invalid"
    return None

def _validate_children(parent,hits,r):
    pp=parent["payload"]; c=pp["landed_hit_count"]
    if len(hits)!=c: return "multi_hit_ordered_hit_count_mismatch"
    for i,o in enumerate(hits,1):
        if (not isinstance(o,Mapping) or o.get("event_kind")!="multi_hit_ordered_hit_observed"
                or o.get("source")!="ui_multi_hit_ordered_hit_confirmation"
                or o.get("trust")!="user_confirmed_observation"
                or o.get("confirmed") is not True or o.get("observed") is not True):
            return "invalid_multi_hit_ordered_hit_observation"
        a=r["actor"]
        if o.get("session_id")!=r["session_id"] or o.get("turn_number")!=r["turn_number"]:
            return "multi_hit_ordered_hit_session_turn_mismatch"
        if (o.get("side"),o.get("slot_index"),o.get("pokemon_id"))!=(a["side"],a["slot_index"],a["pokemon_id"]):
            return "multi_hit_ordered_hit_outer_actor_mismatch"
        if not _pos(o.get("observation_sequence")) or o["observation_sequence"]<=parent.get("observation_sequence",0):
            return "multi_hit_ordered_hit_order_invalid"
        if i>1 and o["observation_sequence"]<=hits[i-2].get("observation_sequence",0):
            return "multi_hit_ordered_hit_order_invalid"
        p=o.get("payload")
        req={"family","decision_point","action_id","move_id","actor","target","parent_multi_hit_observation_id","hit_index","hp_before","hp_after","target_fainted_after_hit","critical_state","related_contact_observation_ids"}
        if not isinstance(p,Mapping) or set(p)!=req: return "invalid_multi_hit_ordered_hit_payload"
        if p["hit_index"]!=i: return "multi_hit_ordered_hit_index_invalid"
        if p["family"]!=FAMILY or p["decision_point"]!=r["decision_point"] or p["action_id"]!=r["action_id"] or p["move_id"]!=r["move_id"] or p["actor"]!=r["actor"] or p["target"]!=r["target"] or p["parent_multi_hit_observation_id"]!=parent.get("observation_id"): return "multi_hit_ordered_hit_identity_mismatch"
        if not _nn(p["hp_before"]) or not _nn(p["hp_after"]) or p["hp_after"]>p["hp_before"] or p["target_fainted_after_hit"] is not (p["hp_after"]==0): return "multi_hit_ordered_hit_hp_invalid"
        if p["critical_state"] not in {None,"critical","non_critical"}: return "multi_hit_ordered_hit_critical_invalid"
        ids=p["related_contact_observation_ids"]
        if not isinstance(ids,(tuple,list)) or len(ids)!=len(set(ids)): return "multi_hit_ordered_hit_contact_links_invalid"
        if i>1 and hits[i-2]["payload"]["hp_after"]!=p["hp_before"]: return "multi_hit_ordered_hp_chain_invalid"
        if i<c and p["target_fainted_after_hit"]: return "multi_hit_child_after_terminal_ko"
    return None

def _parent_matches(p,path):
    if p["action_outcome"]=="miss": return path["selected_hit_count"] is None and not path["ordered_hits"]
    return len(path["ordered_hits"])==p["landed_hit_count"] and path["terminal_reason"]==p["terminal_reason"]

def _children_match(obs,path):
    if len(obs)!=len(path["ordered_hits"]): return False
    for o,h in zip(obs,path["ordered_hits"]):
        p=o["payload"]
        if h.get("hit_index")!=p["hit_index"] or h.get("pre_hp")!=p["hp_before"] or h.get("post_hp")!=p["hp_after"]: return False
        if p["critical_state"] is not None and h.get("critical_state")!=p["critical_state"]: return False
    return True

def _reconciliation(r,status,reason,paths,observations,unresolved):
    mass=sum((x["probability"] for x in paths),Fraction())
    outcome=None if status!="resolved" else ("incompatible_observation" if not paths else "uniquely_matched" if len(paths)==1 else "multiple_compatible_paths")
    return {"status":status,"schema_version":RECONCILIATION_SCHEMA,"reason":reason,"source_prediction_kind":"variable_two_to_five_ordered_graph","family":FAMILY,
            "session_id":r["session_id"],"turn_number":r["turn_number"],"actor":deepcopy(r["actor"]),"target":deepcopy(r["target"]),"decision_point":r["decision_point"],
            "action_id":r["action_id"],"move_id":r["move_id"],"predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"],"match_outcome":outcome,
            "compatible_terminal_leaf_ids":tuple(_path_id(x) for x in paths),
            "compatible_source_paths":tuple({"source_path_id":_path_id(x),"selected_count_root_id":x["root_id"],"selected_hit_count":x["selected_hit_count"],
                "traversed_edge_ids":x["edge_ids"],"terminal_source_id":x["terminal_source_id"],"terminal_reason":x["terminal_reason"],
                "ordered_hits":tuple({"hit_index":h.get("hit_index"),"critical_state":h.get("critical_state"),"roll_index":h.get("roll_index"),"pre_hp":h.get("pre_hp"),"post_hp":h.get("post_hp")} for h in x["ordered_hits"])} for x in paths),
            "compatible_original_probability_mass":_fd(mass),"probability_normalization":"none_preserve_original_mass",
            "source_observation_ids":tuple(x.get("observation_id") for x in observations if _text(x.get("observation_id"))),
            "unresolved_hidden_dimensions":tuple(unresolved),"provenance":"filter_immutable_original_variable_two_to_five_root_to_terminal_paths_v1"}

def _unresolved(paths):
    if len(paths)<2:return ()
    dims=[]
    for label,fn in (("selected_hit_count",lambda x:x["selected_hit_count"]),("critical_state",lambda x:tuple(h.get("critical_state") for h in x["ordered_hits"])),("roll_index",lambda x:tuple(h.get("roll_index") for h in x["ordered_hits"])),("reactive_branch_identity",lambda x:tuple((h.get("contact_reactive_damage"),h.get("contact_reactive_status")) for h in x["ordered_hits"]))):
        if len({_canonical(fn(x)) for x in paths})>1:dims.append(label)
    return tuple(dims)

def _valid_hit(h): return isinstance(h,Mapping) and _pos(h.get("hit_index")) and h["hit_index"]<=5 and h.get("selected_hit_count") in {2,3,4,5} and _nn(h.get("pre_hp")) and _nn(h.get("post_hp")) and h["post_hp"]<=h["pre_hp"] and h.get("critical_state") in {"critical","non_critical"} and isinstance(h.get("roll_index"),int) and not isinstance(h.get("roll_index"),bool) and 0<=h["roll_index"]<16
def _owner(v,s): return isinstance(v,Mapping) and set(v)=={"session_id","side","slot_index","pokemon_id"} and v.get("session_id")==s and v.get("side") in {"self","opponent"} and isinstance(v.get("slot_index"),int) and not isinstance(v.get("slot_index"),bool) and v["slot_index"]>=0 and _text(v.get("pokemon_id"))
def _fraction(v):
    try:return v if isinstance(v,Fraction) else Fraction(v["numerator"],v["denominator"])
    except (TypeError,KeyError,ValueError,ZeroDivisionError):return None
def _path_id(p): return f"{p['root_id']}:{p['terminal_source_id']}:{_fingerprint({'e':p['edge_ids'],'h':p['ordered_hits']})[:16]}"
def _fingerprint(v): return hashlib.sha256(_canonical(v).encode()).hexdigest()
def _canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=lambda x:str(x))
def _fd(v): return {"numerator":v.numerator,"denominator":v.denominator}
def _text(v): return isinstance(v,str) and bool(v)
def _pos(v): return isinstance(v,int) and not isinstance(v,bool) and v>0
def _nn(v): return isinstance(v,int) and not isinstance(v,bool) and v>=0
def _result(s,r): return {"status":s,"reason":r}
