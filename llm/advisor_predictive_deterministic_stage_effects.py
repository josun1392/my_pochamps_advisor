"""Branch-aware detached stage materialization for normal-formula attacks."""
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_observed_damage_application import apply_canonical_stage_delta

def compose_predictive_deterministic_stage_effects(*, interval: Mapping[str, Any], stage_effect_authority: Mapping[str, Any], stat_provenance: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(interval, Mapping) or interval.get("completeness") != "exact_complete": return _r("incomplete", "normal_formula_interval_incomplete")
    if not isinstance(stage_effect_authority, Mapping) or stage_effect_authority.get("move_id") != interval.get("move_id"): return _r("rejected", "stage_effect_move_binding_mismatch")
    if stage_effect_authority.get("status") != "deterministic": return _r(stage_effect_authority.get("status", "unknown"), stage_effect_authority.get("reason", "stage_effect_not_deterministic"))
    effects, conditions, rolls = stage_effect_authority.get("effects"), stage_effect_authority.get("conditions"), interval.get("exact_damage_rolls")
    if not isinstance(effects, list) or not isinstance(conditions, Mapping) or not isinstance(rolls, tuple): return _r("incomplete", "stage_effect_authority_incomplete")
    values = {"self": _stages(stat_provenance.get("attacker")), "target": _stages(stat_provenance.get("defender"))}
    applicable = [e for e in effects if e.get("owner") == "self" or _may_target_apply(interval, conditions, rolls)]
    for effect in applicable:
        if not isinstance(values.get(effect.get("owner")), Mapping) or not isinstance(values[effect["owner"]].get(effect.get("stat")), int): return _r("incomplete", f"{effect.get('owner')}.{effect.get('stat')}_stage_unknown")
    target_hp = interval.get("target_hp_before"); branches=[]
    for raw in rolls:
        row=[]; hit=raw > 0
        for effect in effects:
            owner=effect["owner"]; applies=hit
            if owner == "target": applies = applies and interval.get("target_routing") != "substitute" and (not conditions.get("target_must_survive") or isinstance(target_hp,int) and raw < target_hp)
            if applies:
                before=values[owner][effect["stat"]]; row.append({"owner":owner,"stat":effect["stat"],"previous_stage":before,"delta":effect["delta"],"resulting_stage":apply_canonical_stage_delta(before,effect["delta"])})
        branches.append({"raw_damage":raw,"effects":tuple(row)})
    common = tuple(branches[0]["effects"]) if branches and all(x["effects"] == branches[0]["effects"] for x in branches) else ()
    return {"status":"resolved","schema_version":"deterministic-predictive-stage-effects-v1","session_id":interval["session_id"],"source_branch_fingerprint":interval["source_branch_fingerprint"],"move_id":interval["move_id"],"ordering":["direct_damage","move_native_hp_effect","deterministic_stage_effect","life_orb_post_hit"],"branches":tuple(branches),"guaranteed_effects":common,"conditional":not bool(common),"provenance":deepcopy(stage_effect_authority.get("provenance"))}
def _stages(side):
    block=side.get("stat_stages") if isinstance(side,Mapping) else None; value=block.get("value") if isinstance(block,Mapping) and block.get("available") is True else None
    return value if isinstance(value,Mapping) else None
def _may_target_apply(interval, conditions, rolls): return interval.get("target_routing") != "substitute" and any(x>0 for x in rolls)
def _r(status,reason): return {"status":status,"reason":reason}
