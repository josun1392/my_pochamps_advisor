"""Bounded detached Champions paralysis application authority."""
from copy import deepcopy
from typing import Mapping
from llm.advisor_reducer_state_model import state_fingerprint

SCHEMA="champions-paralysis-application-authority-v1"
CATALOG={"thunder-wave":{"accuracy":90,"damaging":False,"contact":False},"nuzzle":{"accuracy":100,"damaging":True,"contact":True,"base_power":20}}

def _raw(state,owner): return state.get(f"{owner['side']}_side",{}).get("pokemon",{}).get(owner["slot_index"])
def _base(d0,actor,target,action,path):
    if not isinstance(d0,Mapping) or d0.get("status")!="resolved" or d0.get("active_owners",{}).get(actor.get("side"))!=dict(actor) or d0.get("active_owners",{}).get(target.get("side"))!=dict(target) or actor.get("side")==target.get("side") or not isinstance(action,Mapping) or not isinstance(action.get("action_id"),str) or not isinstance(action.get("identity"),str): return None
    return {"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(d0["decision_owner"]),"actor":deepcopy(actor),"target":deepcopy(target),"action_id":action["action_id"],"move_id":action["identity"],"path":tuple(path)}
def _bound(value,base): return isinstance(value,Mapping) and value.get("status")=="resolved" and all(value.get(k)==base.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","actor","target","action_id","move_id"))
def _condition(raw):
    p=raw.get("condition_provenance") if isinstance(raw,Mapping) else None; c=raw.get("condition") if isinstance(raw,Mapping) else None
    if not isinstance(p,Mapping) or p.get("event_kind")!="current_condition_observed" or p.get("trust")!="user_confirmed_observation": return None
    if c in (None,"none") and p.get("condition")=="none": return "none"
    return c if c in {"burn","poison","toxic","paralysis","sleep","freeze"} and p.get("condition")==c else None
def _eligibility(state,actor,target):
    raw=_raw(state,target); source=_raw(state,actor); c=_condition(raw)
    if not isinstance(raw,Mapping) or not isinstance(source,Mapping): return "active_identity_missing"
    if c is None:return "target_current_condition_unknown"
    if c!="none":return "target_already_major_statused"
    types=raw.get("current_type"); tp=raw.get("current_type_provenance")
    if not isinstance(types,list) or not isinstance(tp,Mapping) or tp.get("event_kind")!="current_type_observed":return "target_types_unknown"
    if "electric" in types:return "blocked_by_electric_type"
    abilities=[_raw(state,{"side":side,"slot_index":state.get(f"{side}_side",{}).get("active_slot_index")}).get("current_ability") for side in ("self","opponent")]
    if not all(isinstance(x,str) and x for x in abilities):return "paralysis_ability_unknown"
    if raw.get("current_ability")=="limber" and "neutralizing-gas" not in abilities and source.get("current_ability")!="mold-breaker":return "blocked_by_limber"
    return {"condition":c,"types":tuple(types),"abilities":tuple(abilities)}

def freeze_champions_paralysis_application(*,strategy_d0,runtime_snapshot,actor,target,action,move_success_authority,path=(),reflection_authority=None):
    base=_base(strategy_d0,actor,target,action,path)
    if base is None:return {"status":"rejected","reason":"paralysis_application_binding_invalid"}
    rule=CATALOG.get(base["move_id"])
    if rule is None:return {"status":"unsupported","reason":"move_not_in_champions_paralysis_catalog",**base}
    if not isinstance(runtime_snapshot,Mapping) or runtime_snapshot.get("state_fingerprint")!=base["source_runtime_fingerprint"]:return {"status":"rejected","reason":"stale_paralysis_runtime",**base}
    if not _bound(move_success_authority,base):return {"status":"incomplete","reason":"move_success_authority_missing_or_foreign",**base}
    outcome=move_success_authority.get("outcome")
    if outcome not in {"hit","missed","blocked_by_protection"}:return {"status":"rejected","reason":"move_success_outcome_invalid",**base}
    if rule["damaging"] and outcome=="hit" and move_success_authority.get("damage_resolved") is not True:return {"status":"rejected","reason":"nuzzle_requires_post_hit_damage_authority",**base}
    if reflection_authority is not None:
        if not _bound(reflection_authority,base) or reflection_authority.get("outcome") not in {"not_reflected","reflected"}:return {"status":"incomplete","reason":"reflection_authority_required",**base}
        if reflection_authority["outcome"]=="reflected":return {"status":"incomplete","reason":"reflected_paralysis_owner_unavailable",**base}
    prevention="move_missed" if outcome=="missed" else "blocked_by_protection" if outcome=="blocked_by_protection" else _eligibility(runtime_snapshot["state"],actor,target)
    if isinstance(prevention,str) and prevention.endswith(("unknown","missing")):return {"status":"incomplete","reason":prevention,**base}
    return {"status":"resolved","schema_version":SCHEMA,**base,"accuracy":rule["accuracy"],"damaging":rule["damaging"],"contact":rule["contact"],"base_power":rule.get("base_power"),"move_success_authority":deepcopy(move_success_authority),"prevention":deepcopy(prevention),"provenance":"champions_paralysis_application_v1"}

def materialize_champions_paralysis_application(*,authority,runtime_snapshot):
    if not isinstance(authority,Mapping) or authority.get("status")!="resolved" or authority.get("schema_version")!=SCHEMA or runtime_snapshot.get("state_fingerprint")!=authority.get("source_runtime_fingerprint"):return {"status":"rejected","reason":"invalid_or_foreign_paralysis_authority"}
    state=deepcopy(runtime_snapshot["state"]); raw=_raw(state,authority["target"]); applies=isinstance(authority["prevention"],Mapping)
    if applies: raw["condition"]="paralysis";raw["condition_provenance"]={"event_kind":"current_condition_observed","trust":"user_confirmed_observation","turn_number":1,"condition":"paralysis","hypothetical_provenance":"champions_paralysis_application_v1"}
    snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}
    return {"status":"resolved","runtime_snapshot":snapshot,"paralysis_applied":applies,"outcome":"applies" if applies else authority["prevention"],"authority":deepcopy(authority),"provenance":"detached_champions_paralysis_application_v1"}
