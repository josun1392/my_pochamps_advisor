"""Compose exact normal-formula branches with existing deterministic HP rules."""
from copy import deepcopy
from typing import Any, Mapping
from advisor.damage.recoil import HitResult, RecoilMove, RecoilPokemon, compute_life_orb_recoil
from llm.advisor_focus_sash_survival import apply_focus_sash_to_hit

_UNSUPPORTED_RECOIL={"struggle","mind-blown","steel-beam","chloroblast","high-jump-kick","jump-kick"}

def compose_predictive_normal_formula_post_hit(*, interval: Mapping[str, Any], move_metadata: Mapping[str, Any], attacker_hp: Mapping[str, Any], attacker_item: str | None, attacker_ability: str | None, target_ability: str | None = None, attacker_item_known: bool = True, target_sturdy_survival_authority: Mapping[str, Any] | None = None, target_focus_sash_survival_authority: Mapping[str, Any] | None = None, focus_sash_consumed: bool = False) -> dict[str, Any]:
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
    sturdy=_sturdy(target_sturdy_survival_authority, interval, move_metadata, target_hp)
    if isinstance(sturdy, str): return _r("unsupported" if sturdy == "sturdy_multi_hit_unsupported" else "rejected", sturdy)
    focus=_focus(target_focus_sash_survival_authority, interval, move_metadata, target_hp)
    if isinstance(focus, str): return _r("unsupported" if focus == "focus_sash_multi_hit_unsupported" else "rejected", focus)
    if sturdy is True and focus is True: return _r("unsupported","simultaneous_sturdy_focus_sash_survival_precedence_unsupported")
    current,maximum=attacker_hp["current_hp"],attacker_hp["max_hp"]
    branches=[]
    for raw in rolls:
        actual=min(raw,target_hp)
        activated=sturdy is True and raw >= target_hp
        if activated: actual=target_hp-1
        focus_row=apply_focus_sash_to_hit(authority=target_focus_sash_survival_authority, consumed=focus_sash_consumed, hp_before=target_hp, raw_damage=raw, actual_damage=actual, source_hit={"move_id":interval["move_id"],"critical_scope":deepcopy(interval.get("scope",{}).get("critical"))}) if focus is True else None
        if isinstance(focus_row,Mapping) and focus_row.get("status") in {"incomplete","unsupported","rejected"}: return _r(focus_row["status"], focus_row["reason"])
        if isinstance(focus_row,Mapping): actual=focus_row["actual_damage"]
        native=actual*abs(drain)//100 if drain else 0
        after_native=min(maximum,current+native) if drain>0 else max(0,current-native) if drain<0 else current
        effective_ability=None if target_ability=="neutralizing-gas" else attacker_ability
        life=compute_life_orb_recoil(RecoilPokemon(max_hp=maximum,item=attacker_item,ability=effective_ability),RecoilMove(move_id=interval["move_id"],category=move_metadata.get("category","status")),HitResult(targets_hit=1 if actual>0 else 0)) if attacker_item=="life-orb" else 0
        branches.append({"raw_damage":raw,"actual_damage":actual,"move_native_hp_delta":native if drain>0 else -native,"life_orb_recoil":life,"attacker_post_hit_hp":max(0,after_native-life),"sturdy_survival":({"outcome":"applied","target_final_hp":1,"provenance":"exact_detached_opponent_switch_in_sturdy_survival_v1"} if activated else {"outcome":"not_triggered"} if sturdy is True else {"outcome":"not_applicable"}),"focus_sash_survival":(deepcopy(focus_row["survival"]) if isinstance(focus_row,Mapping) else {"outcome":"not_applicable"})})
    hp_values=tuple(sorted({row["attacker_post_hit_hp"] for row in branches})); faints=[value==0 for value in hp_values]
    return {"status":"resolved","schema_version":"deterministic-predictive-normal-formula-post-hit-v1","session_id":interval["session_id"],"source_branch_fingerprint":interval["source_branch_fingerprint"],"decision_owner":deepcopy(dict(interval["decision_owner"])),"move_id":interval["move_id"],"ordering":["direct_damage","move_native_hp_effect","life_orb_post_hit"],"branches":tuple(branches),"attacker_post_hit_hp_values":hp_values,"attacker_post_hit_hp_range":{"minimum":min(hp_values),"maximum":max(hp_values)},"guaranteed_attacker_faint":all(faints),"possible_attacker_faint":any(faints) and not all(faints),"guaranteed_attacker_survival":not any(faints),"provenance":"existing_drain_recoil_then_life_orb_v1"}
def _target_hp(interval):
 value=interval.get("target_hp_before")
 return value if isinstance(value,int) and not isinstance(value,bool) and value>=0 else None
def _sturdy(value,interval,move,target_hp):
 if value is None:return False
 if not isinstance(value,Mapping):return "sturdy_authority_invalid"
 status=value.get("status")
 if status=="not_applicable":return False
 required={"schema_version","session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","defender","attacker","status","post_entry_hp","maximum_hp","provenance"}
 if status!="ready" or set(value)!=required or value.get("schema_version")!="detached-switch-in-sturdy-survival-authority-v1":return "sturdy_authority_invalid"
 # The interval is rebuilt from the private post-switch predictive view, so
 # its branch fingerprint intentionally differs from the frozen source D0.
 # Session and decision-owner binding were already verified while materializing
 # that detached switch-in authority.
 if any(value.get(key)!=interval.get(key) for key in ("session_id","decision_owner")):return "sturdy_authority_binding_mismatch"
 if value.get("post_entry_hp")!=target_hp or value.get("maximum_hp")!=target_hp or not isinstance(target_hp,int) or target_hp<=1:return "sturdy_post_entry_hp_invalid"
 minimum,maximum=move.get("min_hits"),move.get("max_hits")
 if not ((minimum is None and maximum is None) or (minimum==maximum==1)):return "sturdy_multi_hit_unsupported"
 return True
def _focus(value,interval,move,target_hp):
 if value is None:return False
 if not isinstance(value,Mapping):return "focus_sash_survival_authority_invalid"
 status=value.get("status")
 if status=="resolved" and value.get("outcome")=="known_no_effect":return False
 if status in {"incomplete","unsupported","rejected"}:return "focus_sash_survival_authority_unavailable"
 required={"schema_version","session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","holder","attacker","action_id","move_id","provenance","status","current_hp","maximum_hp","current_item_authority","outcome","focus_sash_available","eligible","item_before"}
 if status!="ready" or not required.issubset(set(value)) or value.get("schema_version")!="runtime-d0-focus-sash-survival-authority-v1":return "focus_sash_survival_authority_invalid"
 if any(value.get(key)!=interval.get(key) for key in ("session_id","source_branch_fingerprint","decision_owner","move_id")):return "focus_sash_survival_authority_binding_mismatch"
 if value.get("current_hp")!=target_hp or value.get("maximum_hp")!=target_hp or not isinstance(target_hp,int) or target_hp<1:return "focus_sash_hp_invalid"
 minimum,maximum=move.get("min_hits"),move.get("max_hits")
 if not ((minimum is None and maximum is None) or (minimum==maximum==1)):return "focus_sash_multi_hit_unsupported"
 return True
def _hp(value): return isinstance(value,Mapping) and all(isinstance(value.get(k),int) and not isinstance(value.get(k),bool) for k in ("current_hp","max_hp")) and 0<=value["current_hp"]<=value["max_hp"] and value["max_hp"]>0
def _r(status,reason): return {"status":status,"reason":reason}
