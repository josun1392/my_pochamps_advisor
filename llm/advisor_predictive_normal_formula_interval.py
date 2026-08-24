"""Generic D0-bound interval authority for simple ordinary direct attacks."""
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_substitute import substitute_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_deterministic_move_stage_effect_metadata import build_deterministic_move_stage_effect_metadata

def normal_formula_eligibility(move: Mapping[str, Any]) -> dict[str, Any]:
    """Metadata-only v1 gate; native direct mechanics remains final authority."""
    if not isinstance(move, Mapping): return {"status":"unsupported","reason":"canonical_move_metadata_required"}
    if not isinstance(move.get("move_id"),str) or not move["move_id"]: return {"status":"unsupported","reason":"canonical_move_identity_required"}
    if move.get("category") not in {"physical","special"} or not isinstance(move.get("power"),int) or isinstance(move.get("power"),bool) or move["power"]<1 or not isinstance(move.get("type"),str) or not move["type"]: return {"status":"unsupported","reason":"not_simple_normal_formula_metadata"}
    if any(move.get(key) not in {None,0,False} for key in ("min_hits","max_hits","recoil","charge_turn","recharge","self_ko")): return {"status":"unsupported","reason":"not_simple_normal_formula_move"}
    if move.get("drain") not in {None,0} and (isinstance(move.get("drain"),bool) or not isinstance(move.get("drain"),int) or not -100 <= move["drain"] <= 100): return {"status":"unsupported","reason":"invalid_move_drain_metadata"}
    return {"status":"eligible","move_id":move["move_id"],"stage_effect_authority":build_deterministic_move_stage_effect_metadata(move)}

def build_predictive_normal_formula_interval(*, branch_state: Mapping[str, Any], decision_owner: Mapping[str, Any], target_owner: Mapping[str, Any], snapshot_damage_input: Mapping[str, Any], stat_provenance: Mapping[str, Any], trusted_level: int | None) -> dict[str, Any]:
    fp=fingerprint_transition_preview_state(branch_state); move=snapshot_damage_input.get("move") if isinstance(snapshot_damage_input,Mapping) else None; eligibility=normal_formula_eligibility(move)
    if eligibility["status"]!="eligible": return _r("unsupported",eligibility["reason"])
    if not isinstance(fp,str) or not _owners(branch_state,decision_owner,target_owner): return _r("rejected","invalid_d0_authority")
    if not _matches(snapshot_damage_input,stat_provenance,decision_owner,target_owner,eligibility["move_id"]): return _r("rejected","foreign_or_invalid_frozen_input")
    substitute=substitute_state(branch_state,target_owner)
    if substitute["state"] in {"unknown","legacy_untracked"}: return _base(fp,decision_owner,target_owner,eligibility["move_id"],"exact_incomplete","substitute_state_unknown")
    native=evaluate_direct_damage_mechanics(deepcopy(dict(snapshot_damage_input)),stat_provenance=deepcopy(dict(stat_provenance)),trusted_level=trusted_level)
    if native.get("status")!="known": return _base(fp,decision_owner,target_owner,eligibility["move_id"],"unsupported" if native.get("status")=="unsupported_mechanic" else "exact_incomplete",native.get("unsupported_reason") or "native_evaluator_incomplete",native=native)
    rolls=native.get("exact_damage_rolls")
    if not isinstance(rolls,tuple) or len(rolls)!=16 or any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in rolls): return _base(fp,decision_owner,target_owner,eligibility["move_id"],"exact_incomplete","native_roll_set_unavailable",native=native)
    hp=branch_state["active"][target_owner["side"]]["current_hp"]; route="substitute" if substitute["state"]=="known_active" else "target"; pool=substitute["substitute_hp"] if route=="substitute" else hp; lo,hi=min(rolls),max(rolls); remaining=tuple(sorted({max(0,pool-x) for x in rolls}))
    facts={"guaranteed_target_KO":False,"guaranteed_target_survival":False,"possible_target_KO":False,"guaranteed_substitute_break":False,"guaranteed_substitute_survival":False,"possible_substitute_break":False}
    if route=="target": facts.update(guaranteed_target_KO=lo>=hp,guaranteed_target_survival=hi<hp,possible_target_KO=lo<hp<=hi)
    else: facts.update(guaranteed_substitute_break=lo>=pool,guaranteed_substitute_survival=hi<pool,possible_substitute_break=lo<pool<=hi)
    return {**_base(fp,decision_owner,target_owner,eligibility["move_id"],"exact_complete","native_q12_exact_roll_set",native=native),"exact_damage_rolls":rolls,"min_damage":lo,"max_damage":hi,"target_routing":route,"target_hp_before":hp if route=="target" else None,"reachable_post_hit_hp":remaining if route=="target" else None,"post_hit_hp_min":min(remaining) if route=="target" else None,"post_hit_hp_max":max(remaining) if route=="target" else None,"reachable_substitute_hp":remaining if route=="substitute" else None,"guaranteed_facts":facts}

def _base(fp,o,t,move_id,completeness,reason,native=None):
 r={"status":"resolved","schema_version":"deterministic-predictive-normal-formula-interval-v1","session_id":o["session_id"],"source_branch_fingerprint":fp,"decision_owner":deepcopy(dict(o)),"attacker":deepcopy(dict(o)),"target":deepcopy(dict(t)),"move_id":move_id,"scope":{"hit":"assumed","critical":"non_critical_assumed","hit_count":1,"secondary_effect":"unmodeled"},"completeness":completeness,"reason":reason,"provenance":"current_predictive_normal_formula_interval_v1"}
 if native is not None:r["native_evaluator_result"]=deepcopy(dict(native))
 return r
def _matches(d,p,o,t,move_id): return isinstance(d,Mapping) and isinstance(p,Mapping) and d.get("move",{}).get("move_id")==move_id and d.get("attacker",{}).get("session_id")==o.get("session_id") and d.get("defender",{}).get("session_id")==t.get("session_id") and d.get("attacker",{}).get("species_id")==o.get("pokemon_id") and d.get("defender",{}).get("species_id")==t.get("pokemon_id") and p.get("attacker",{}).get("pokemon_identity")==o.get("pokemon_id") and p.get("defender",{}).get("pokemon_identity")==t.get("pokemon_id")
def _owners(s,o,t):
 a=s.get("active",{}) if isinstance(s,Mapping) else {}; return o.get("side")!=t.get("side") and all(isinstance(x,Mapping) and dict(y)=={k:x.get(k) for k in ("session_id","side","slot_index","pokemon_id")} for x,y in ((a.get(o.get("side")),o),(a.get(t.get("side")),t)))
def _r(status,reason): return {"status":status,"reason":reason}
