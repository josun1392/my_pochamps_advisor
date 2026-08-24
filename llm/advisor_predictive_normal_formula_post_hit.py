"""Compose exact normal-formula branches with existing deterministic HP rules."""
from copy import deepcopy
from typing import Any, Mapping
from advisor.damage.recoil import HitResult, RecoilMove, RecoilPokemon, compute_life_orb_recoil

_UNSUPPORTED_RECOIL={"struggle","mind-blown","steel-beam","chloroblast","high-jump-kick","jump-kick"}

def compose_predictive_normal_formula_post_hit(*, interval: Mapping[str, Any], move_metadata: Mapping[str, Any], attacker_hp: Mapping[str, Any], attacker_item: str | None, attacker_ability: str | None, target_ability: str | None = None, attacker_item_known: bool = True) -> dict[str, Any]:
    """Apply move drain/recoil then Life Orb to each exact direct-damage branch."""
    if not isinstance(interval,Mapping) or interval.get("schema_version")!="deterministic-predictive-normal-formula-interval-v1" or interval.get("completeness")!="exact_complete": return _r("incomplete","normal_formula_interval_incomplete")
    if not isinstance(move_metadata,Mapping) or move_metadata.get("move_id")!=interval.get("move_id"): return _r("rejected","post_hit_move_binding_mismatch")
    if not _hp(attacker_hp): return _r("incomplete","attacker_hp_unknown")
    drain=move_metadata.get("drain",0)
    if drain is None: drain=0
    if isinstance(drain,bool) or not isinstance(drain,int) or not -100<=drain<=100: return _r("unsupported","invalid_move_drain_metadata")
    if drain<0 and interval.get("move_id") in _UNSUPPORTED_RECOIL: return _r("unsupported","unsupported_recoil_rule")
    if drain and interval.get("target_routing")=="substitute": return _r("incomplete","substitute_damage_dealt_authority_unavailable")
    if not isinstance(attacker_item_known, bool) or not attacker_item_known: return _r("incomplete","attacker_item_authority_unknown")
    if attacker_item=="life-orb" and (attacker_ability is None or target_ability is None): return _r("incomplete","life_orb_ability_authority_unknown")
    rolls=interval.get("exact_damage_rolls"); target_hp=_target_hp(interval)
    if not isinstance(rolls,tuple) or not isinstance(target_hp,int): return _r("incomplete","target_hp_unknown")
    current,maximum=attacker_hp["current_hp"],attacker_hp["max_hp"]
    branches=[]
    for raw in rolls:
        actual=min(raw,target_hp); native=actual*abs(drain)//100 if drain else 0
        after_native=min(maximum,current+native) if drain>0 else max(0,current-native) if drain<0 else current
        effective_ability=None if target_ability=="neutralizing-gas" else attacker_ability
        life=compute_life_orb_recoil(RecoilPokemon(max_hp=maximum,item=attacker_item,ability=effective_ability),RecoilMove(move_id=interval["move_id"],category=move_metadata.get("category","status")),HitResult(targets_hit=1 if actual>0 else 0)) if attacker_item=="life-orb" else 0
        branches.append({"raw_damage":raw,"actual_damage":actual,"move_native_hp_delta":native if drain>0 else -native,"life_orb_recoil":life,"attacker_post_hit_hp":max(0,after_native-life)})
    hp_values=tuple(sorted({row["attacker_post_hit_hp"] for row in branches})); faints=[value==0 for value in hp_values]
    return {"status":"resolved","schema_version":"deterministic-predictive-normal-formula-post-hit-v1","session_id":interval["session_id"],"source_branch_fingerprint":interval["source_branch_fingerprint"],"decision_owner":deepcopy(dict(interval["decision_owner"])),"move_id":interval["move_id"],"ordering":["direct_damage","move_native_hp_effect","life_orb_post_hit"],"branches":tuple(branches),"attacker_post_hit_hp_values":hp_values,"attacker_post_hit_hp_range":{"minimum":min(hp_values),"maximum":max(hp_values)},"guaranteed_attacker_faint":all(faints),"possible_attacker_faint":any(faints) and not all(faints),"guaranteed_attacker_survival":not any(faints),"provenance":"existing_drain_recoil_then_life_orb_v1"}
def _target_hp(interval):
 value=interval.get("target_hp_before")
 return value if isinstance(value,int) and not isinstance(value,bool) and value>=0 else None
def _hp(value): return isinstance(value,Mapping) and all(isinstance(value.get(k),int) and not isinstance(value.get(k),bool) for k in ("current_hp","max_hp")) and 0<=value["current_hp"]<=value["max_hp"] and value["max_hp"]>0
def _r(status,reason): return {"status":status,"reason":reason}
