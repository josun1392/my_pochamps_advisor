"""D0-bound, hit-assumed non-critical Water Gun interval authority."""
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_substitute import substitute_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state

def build_predictive_water_gun_interval(*, branch_state: Mapping[str, Any], decision_owner: Mapping[str, Any], target_owner: Mapping[str, Any], snapshot_damage_input: Mapping[str, Any], stat_provenance: Mapping[str, Any], trusted_level: int | None) -> dict[str, Any]:
    fp=fingerprint_transition_preview_state(branch_state)
    if not isinstance(fp,str) or not _owners(branch_state,decision_owner,target_owner): return _r("rejected","invalid_d0_authority")
    if not _matches(snapshot_damage_input,stat_provenance,decision_owner,target_owner): return _r("rejected","foreign_or_invalid_frozen_input")
    substitute=substitute_state(branch_state,target_owner)
    if substitute["state"] in {"unknown","legacy_untracked"}: return _base(fp,decision_owner,target_owner,"exact_incomplete","substitute_state_unknown")
    native=evaluate_direct_damage_mechanics(deepcopy(dict(snapshot_damage_input)),stat_provenance=deepcopy(dict(stat_provenance)),trusted_level=trusted_level)
    if native.get("status")!="known": return _base(fp,decision_owner,target_owner,"unsupported" if native.get("status")=="unsupported_mechanic" else "exact_incomplete",native.get("unsupported_reason") or "native_evaluator_incomplete",native=native)
    rolls=native.get("exact_damage_rolls")
    if not isinstance(rolls,tuple) or len(rolls)!=16 or any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in rolls): return _base(fp,decision_owner,target_owner,"exact_incomplete","native_roll_set_unavailable",native=native)
    hp=branch_state["active"][target_owner["side"]]["current_hp"]
    route="substitute" if substitute["state"]=="known_active" else "target"
    pool=substitute["substitute_hp"] if route=="substitute" else hp
    lo,hi=min(rolls),max(rolls); remaining=tuple(sorted({max(0,pool-x) for x in rolls}))
    facts={"guaranteed_target_KO":False,"guaranteed_target_survival":False,"possible_target_KO":False,"guaranteed_substitute_break":False,"guaranteed_substitute_survival":False,"possible_substitute_break":False}
    if route=="target": facts.update(guaranteed_target_KO=lo>=hp,guaranteed_target_survival=hi<hp,possible_target_KO=lo<hp<=hi)
    else: facts.update(guaranteed_substitute_break=lo>=pool,guaranteed_substitute_survival=hi<pool,possible_substitute_break=lo<pool<=hi)
    return {**_base(fp,decision_owner,target_owner,"exact_complete","native_q12_exact_roll_set",native=native),"exact_damage_rolls":rolls,"min_damage":lo,"max_damage":hi,"target_routing":route,"reachable_post_hit_hp":remaining if route=="target" else None,"post_hit_hp_min":min(remaining) if route=="target" else None,"post_hit_hp_max":max(remaining) if route=="target" else None,"reachable_substitute_hp":remaining if route=="substitute" else None,"guaranteed_facts":facts}

def project_guaranteed_water_gun_facts(interval: Mapping[str,Any])->dict[str,Any]:
    if not isinstance(interval,Mapping) or interval.get("schema_version")!="deterministic-predictive-damage-interval-v1" or interval.get("completeness")!="exact_complete": return _r("incomplete","interval_authority_incomplete")
    return {"status":"resolved","schema_version":"deterministic-predictive-guaranteed-facts-v1","source_branch_fingerprint":interval["source_branch_fingerprint"],"facts":deepcopy(interval["guaranteed_facts"]),"provenance":"current_predictive_normal_formula_interval_v1"}

def _base(fp,o,t,completeness,reason,native=None):
 r={"status":"resolved","schema_version":"deterministic-predictive-damage-interval-v1","session_id":o["session_id"],"source_branch_fingerprint":fp,"decision_owner":deepcopy(dict(o)),"attacker":deepcopy(dict(o)),"target":deepcopy(dict(t)),"move_id":"water-gun","scope":{"hit":"assumed","critical":"non_critical_assumed","hit_count":1},"completeness":completeness,"reason":reason,"provenance":"current_predictive_normal_formula_interval_v1"}
 if native is not None:r["native_evaluator_result"]=deepcopy(dict(native))
 return r
def _matches(d,p,o,t):
 return isinstance(d,Mapping) and isinstance(p,Mapping) and d.get("move",{}).get("move_id")=="water-gun" and d.get("attacker",{}).get("session_id")==o.get("session_id") and d.get("defender",{}).get("session_id")==t.get("session_id") and d.get("attacker",{}).get("species_id")==o.get("pokemon_id") and d.get("defender",{}).get("species_id")==t.get("pokemon_id") and p.get("attacker",{}).get("pokemon_identity")==o.get("pokemon_id") and p.get("defender",{}).get("pokemon_identity")==t.get("pokemon_id")
def _owners(s,o,t):
 a=s.get("active",{}) if isinstance(s,Mapping) else {};return o.get("side")!=t.get("side") and all(isinstance(x,Mapping) and dict(y)=={k:x.get(k) for k in ("session_id","side","slot_index","pokemon_id")} for x,y in ((a.get(o.get("side")),o),(a.get(t.get("side")),t)))
def _r(status,reason):return {"status":status,"reason":reason}
