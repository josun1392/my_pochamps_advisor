"""Branch-aware detached stage materialization for normal-formula attacks."""
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_observed_damage_application import apply_canonical_stage_delta
from llm.advisor_predictive_post_hit_target_outcomes import resolve_predictive_post_hit_target_outcomes


def compose_predictive_self_stage_effect(*, interval: Mapping[str, Any], effect: Mapping[str, Any], current_stage: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize one detached self-stage overlay for a successful hit leaf.

    This narrow helper shares the canonical stage-cap arithmetic with the
    deterministic stage composer while leaving authority and probability
    branching to its dedicated callers.
    """
    if not isinstance(interval, Mapping) or interval.get("completeness") != "exact_complete":
        return _r("incomplete", "normal_formula_interval_incomplete")
    if interval.get("target_routing") not in {"target", "substitute"}:
        return _r("incomplete", "successful_damaging_hit_unavailable")
    rolls = interval.get("exact_damage_rolls")
    if not isinstance(rolls, tuple) or len(rolls) != 16 or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in rolls):
        return _r("incomplete", "successful_damaging_hit_unavailable")
    stat, delta = effect.get("stat") if isinstance(effect, Mapping) else None, effect.get("delta") if isinstance(effect, Mapping) else None
    before = current_stage.get("value") if isinstance(current_stage, Mapping) and current_stage.get("status") == "known" else None
    if effect.get("owner") != "self" or not isinstance(stat, str) or not isinstance(delta, int) or isinstance(delta, bool) or not 1 <= delta <= 6:
        return _r("rejected", "invalid_probabilistic_self_stage_effect")
    if not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _r("incomplete", "self_stage_unknown")
    return {
        "status": "resolved", "schema_version": "predictive-self-stage-effect-composition-v1",
        "effect": {"owner": "self", "stat": stat, "previous_stage": before, "delta": delta, "resulting_stage": apply_canonical_stage_delta(before, delta)},
        "provenance": "canonical_predictive_stage_composition_v1",
    }


def compose_predictive_target_stage_effect(*, interval: Mapping[str, Any], effect: Mapping[str, Any], current_stage: Mapping[str, Any], roll_damage: int) -> dict[str, Any]:
    """Materialize one surviving direct-hit target-stage overlay.

    Target-owned secondaries must be evaluated per exact damage roll: a KO
    roll has no target-stage effect.  This helper owns only the forward stage
    cap arithmetic, not probability, Substitute, or suppression semantics.
    """
    if not isinstance(interval, Mapping) or interval.get("completeness") != "exact_complete":
        return _r("incomplete", "normal_formula_interval_incomplete")
    if interval.get("target_routing") != "target":
        return _r("incomplete", "target_stage_direct_hit_unavailable")
    target_hp = interval.get("target_hp_before")
    if not isinstance(target_hp, int) or isinstance(target_hp, bool) or target_hp < 1:
        return _r("incomplete", "target_hp_unknown")
    if not isinstance(roll_damage, int) or isinstance(roll_damage, bool) or roll_damage < 1:
        return _r("incomplete", "successful_damaging_hit_unavailable")
    if roll_damage >= target_hp:
        return _r("incomplete", "target_did_not_survive_damage_roll")
    stat, delta = effect.get("stat") if isinstance(effect, Mapping) else None, effect.get("delta") if isinstance(effect, Mapping) else None
    before = current_stage.get("value") if isinstance(current_stage, Mapping) and current_stage.get("status") == "known" else None
    if effect.get("owner") != "target" or not isinstance(stat, str) or not isinstance(delta, int) or isinstance(delta, bool) or not -6 <= delta <= -1:
        return _r("rejected", "invalid_probabilistic_target_stage_effect")
    if not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _r("incomplete", "target_stage_unknown")
    return {
        "status": "resolved", "schema_version": "predictive-target-stage-effect-composition-v1",
        "effect": {"owner": "target", "stat": stat, "previous_stage": before, "delta": delta, "resulting_stage": apply_canonical_stage_delta(before, delta)},
        "provenance": "canonical_predictive_stage_composition_v1",
    }

def compose_predictive_deterministic_stage_effects(*, interval: Mapping[str, Any], stage_effect_authority: Mapping[str, Any], stat_provenance: Mapping[str, Any], post_hit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(interval, Mapping) or interval.get("completeness") != "exact_complete": return _r("incomplete", "normal_formula_interval_incomplete")
    if not isinstance(stage_effect_authority, Mapping) or stage_effect_authority.get("move_id") != interval.get("move_id"): return _r("rejected", "stage_effect_move_binding_mismatch")
    if stage_effect_authority.get("status") != "deterministic": return _r(stage_effect_authority.get("status", "unknown"), stage_effect_authority.get("reason", "stage_effect_not_deterministic"))
    effects, conditions, rolls = stage_effect_authority.get("effects"), stage_effect_authority.get("conditions"), interval.get("exact_damage_rolls")
    if not isinstance(effects, list) or not isinstance(conditions, Mapping) or not isinstance(rolls, tuple): return _r("incomplete", "stage_effect_authority_incomplete")
    values = {"self": _stages(stat_provenance.get("attacker")), "target": _stages(stat_provenance.get("defender"))}
    applicable = [e for e in effects if e.get("owner") == "self" or _may_target_apply(interval, conditions, rolls)]
    for effect in applicable:
        if not isinstance(values.get(effect.get("owner")), Mapping) or not isinstance(values[effect["owner"]].get(effect.get("stat")), int): return _r("incomplete", f"{effect.get('owner')}.{effect.get('stat')}_stage_unknown")
    if interval.get("target_routing") == "substitute":
        outcomes = {"status": "resolved", "outcomes": tuple({"raw_damage": raw, "actual_damage": raw, "target_post_hit_hp": None, "target_survived": False} for raw in rolls)}
    else:
        outcomes = resolve_predictive_post_hit_target_outcomes(interval=interval, post_hit=post_hit)
        if outcomes.get("status") != "resolved": return outcomes
    branches=[]
    for outcome in outcomes["outcomes"]:
        raw, actual, target_survived = outcome["raw_damage"], outcome["actual_damage"], outcome["target_survived"]
        row=[]; hit=raw > 0
        for effect in effects:
            owner=effect["owner"]; applies=hit
            if owner == "target": applies = applies and interval.get("target_routing") != "substitute" and (not conditions.get("target_must_survive") or target_survived)
            if applies:
                before=values[owner][effect["stat"]]; row.append({"owner":owner,"stat":effect["stat"],"previous_stage":before,"delta":effect["delta"],"resulting_stage":apply_canonical_stage_delta(before,effect["delta"])})
        branches.append({"raw_damage":raw,"actual_damage":actual,"target_post_hit_hp":outcome["target_post_hit_hp"],"effects":tuple(row)})
    common = tuple(branches[0]["effects"]) if branches and all(x["effects"] == branches[0]["effects"] for x in branches) else ()
    return {"status":"resolved","schema_version":"deterministic-predictive-stage-effects-v1","session_id":interval["session_id"],"source_branch_fingerprint":interval["source_branch_fingerprint"],"move_id":interval["move_id"],"ordering":["direct_damage","move_native_hp_effect","deterministic_stage_effect","life_orb_post_hit"],"branches":tuple(branches),"guaranteed_effects":common,"conditional":not bool(common),"provenance":deepcopy(stage_effect_authority.get("provenance"))}
def _stages(side):
    block=side.get("stat_stages") if isinstance(side,Mapping) else None; value=block.get("value") if isinstance(block,Mapping) and block.get("available") is True else None
    return value if isinstance(value,Mapping) else None
def _may_target_apply(interval, conditions, rolls): return interval.get("target_routing") != "substitute" and any(x>0 for x in rolls)
def _r(status,reason): return {"status":status,"reason":reason}
