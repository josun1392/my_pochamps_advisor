"""Strict, detached normalization of one predictive action into exact leaves.

This module deliberately owns no mechanics and never supplies a neutral
probability for an omitted component.  It only flattens already-authoritative
predictive branch structures after an explicit component manifest proves the
tree is complete.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping


SCHEMA_VERSION = "exact-predictive-outcome-ledger-v1"
HORIZON = "immediate_action_consequence"
_COMPONENTS = ("accuracy", "critical", "damage_roll", "secondary")
_STAT_SECONDARY = "deterministic-predictive-probabilistic-target-stage-effect-uncertainty-v1"
_STATUS_SECONDARY = "deterministic-predictive-thunderbolt-paralysis-uncertainty-v1"
_SELF_SECONDARY = "deterministic-predictive-probabilistic-self-stage-effect-uncertainty-v1"
_FLINCH_SECONDARY = "deterministic-predictive-iron-head-flinch-uncertainty-v1"
_CONDITION_REMOVAL_SECONDARY = "deterministic-predictive-sparkling-aria-burn-clearing-uncertainty-v1"


def normalize_exact_predictive_outcome_ledger(
    *, candidate: Mapping[str, Any], predictive_consequence: Mapping[str, Any] | None,
    component_manifest: Mapping[str, Any], bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Return exact terminal leaves or fail closed without mutating inputs.

    ``predictive_consequence`` is the existing hit/miss uncertainty for an
    attack.  Deterministic actions use ``None`` and an explicitly complete
    ``deterministic_outcome`` manifest entry.  The caller must never omit a
    material component from the manifest.
    """
    bound = _bindings(candidate, bindings)
    if bound is None:
        return _result("rejected", "candidate_or_binding_mismatch")
    manifest = _manifest(component_manifest, candidate["action_type"])
    if manifest.get("status") != "resolved":
        return _result(manifest["status"], manifest["reason"], bound)
    if candidate["action_type"] == "manual_switch":
        return _deterministic_switch(candidate, predictive_consequence, manifest, bound)
    if candidate["action_type"] != "attack":
        return _result("unsupported", "action_family_not_supported", bound)
    try:
        return _attack(candidate, predictive_consequence, manifest, bound)
    except _NormalizationError as error:
        return _result("rejected", str(error), bound)


def _attack(candidate: Mapping[str, Any], root: Any, manifest: Mapping[str, Any], bound: Mapping[str, Any]) -> dict[str, Any]:
    if manifest["accuracy"] != "resolved" or manifest["critical"] not in {"resolved", "not_applicable"} or manifest["damage_roll"] != "resolved":
        return _result("incomplete", "required_attack_probability_component_not_resolved", bound)
    if not isinstance(root, Mapping) or root.get("status") != "resolved" or root.get("schema_version") != "deterministic-predictive-hit-miss-uncertainty-v1":
        return _result("rejected", "invalid_hit_miss_predictive_consequence", bound)
    if not _same(root, bound, move_required=True):
        return _result("rejected", "hit_miss_binding_mismatch", bound)
    leaves: list[dict[str, Any]] = []
    branches = root.get("branches")
    if not isinstance(branches, (tuple, list)) or not branches:
        return _result("rejected", "hit_miss_branches_missing", bound)
    parsed = []
    for branch in branches:
        if not isinstance(branch, Mapping) or branch.get("branch") not in {"hit", "miss"}:
            return _result("rejected", "invalid_hit_miss_branch", bound)
        factor = _percent(branch.get("probability_percent"))
        if factor is None or not isinstance(branch.get("consequences"), Mapping):
            return _result("rejected", "invalid_hit_miss_probability", bound)
        parsed.append((branch, factor))
    if not _partition(parsed):
        return _result("rejected", "hit_miss_probability_mass_invalid", bound)
    names = {branch["branch"] for branch, _ in parsed}
    if "miss" in names and "hit" in names and len(parsed) != 2 or len(names) != len(parsed):
        return _result("rejected", "duplicate_or_invalid_hit_miss_branches", bound)
    for branch, factor in parsed:
        path = ((branch["branch"], _fraction_dict(factor)),)
        if branch["branch"] == "miss":
            leaves.append(_leaf(candidate, bound, path, branch["consequences"], None, None, None))
            continue
        result = _hit_descendants(candidate, bound, branch["consequences"], path, manifest)
        if isinstance(result, dict):
            return result
        leaves.extend(result)
    return _complete(candidate, bound, leaves, manifest)


def _hit_descendants(candidate: Mapping[str, Any], bound: Mapping[str, Any], consequence: Mapping[str, Any], path: tuple, manifest: Mapping[str, Any]) -> list[dict[str, Any]] | dict[str, Any]:
    critical = consequence.get("critical_hit_uncertainty")
    if manifest["critical"] == "resolved":
        if not isinstance(critical, Mapping) or critical.get("status") != "resolved" or critical.get("schema_version") != "deterministic-predictive-critical-hit-uncertainty-v1" or not _same(critical, bound, move_required=True):
            return _result("rejected", "critical_component_missing_or_mismatched", bound)
        parsed = []
        for branch in critical.get("branches", ()):
            probability = branch.get("conditional_critical_probability") if isinstance(branch, Mapping) else None
            factor = _fraction(probability)
            if not isinstance(branch, Mapping) or branch.get("branch") not in {"critical", "non_critical"} or factor is None or not isinstance(branch.get("consequences"), Mapping):
                return _result("rejected", "invalid_critical_branch", bound)
            parsed.append((branch, factor))
        if not _partition(parsed) or not parsed:
            return _result("rejected", "critical_probability_mass_invalid", bound)
        output: list[dict[str, Any]] = []
        for branch, factor in parsed:
            output.extend(_roll_descendants(candidate, bound, branch["consequences"], path + ((branch["branch"], _fraction_dict(factor)),), manifest, branch["branch"]))
        return output
    if critical is not None:
        return _result("rejected", "critical_manifest_not_applicable_but_present", bound)
    return _roll_descendants(candidate, bound, consequence, path, manifest, "not_applicable")


def _roll_descendants(candidate: Mapping[str, Any], bound: Mapping[str, Any], consequence: Mapping[str, Any], path: tuple, manifest: Mapping[str, Any], critical_state: str) -> list[dict[str, Any]]:
    rolls = consequence.get("damage_roll_uncertainty")
    if not isinstance(rolls, Mapping) or rolls.get("status") != "resolved" or rolls.get("schema_version") != "deterministic-predictive-damage-roll-uncertainty-v1" or not _same(rolls, bound, move_required=True, inherited_identity=True):
        raise _NormalizationError("damage_roll_component_missing_or_mismatched")
    outcomes = rolls.get("outcomes")
    if not isinstance(outcomes, (tuple, list)) or len(outcomes) != 16:
        raise _NormalizationError("canonical_sixteen_rolls_missing")
    parsed: list[tuple[Mapping[str, Any], Fraction]] = []
    for index, roll in enumerate(outcomes):
        factor = _fraction(roll.get("probability") if isinstance(roll, Mapping) else None)
        if not isinstance(roll, Mapping) or roll.get("roll_index") != index or roll.get("random_factor_percent") != 85 + index or not isinstance(roll.get("damage"), int) or isinstance(roll.get("damage"), bool) or factor != Fraction(1, 16):
            raise _NormalizationError("invalid_canonical_damage_roll")
        parsed.append((roll, factor))
    if not _partition(parsed):
        raise _NormalizationError("damage_roll_probability_mass_invalid")
    output: list[dict[str, Any]] = []
    for roll, factor in parsed:
        roll_path = path + ((f"damage_roll:{roll['roll_index']}", _fraction_dict(factor)),)
        output.extend(_secondary_descendants(candidate, bound, consequence, roll, roll_path, manifest, critical_state))
    return output


def _secondary_descendants(candidate: Mapping[str, Any], bound: Mapping[str, Any], consequence: Mapping[str, Any], roll: Mapping[str, Any], path: tuple, manifest: Mapping[str, Any], critical_state: str) -> list[dict[str, Any]]:
    secondary = _secondary(consequence)
    if manifest["secondary"] == "not_applicable":
        if secondary is not None:
            raise _NormalizationError("secondary_manifest_not_applicable_but_present")
        return [_leaf(candidate, bound, path, consequence, critical_state, roll, None)]
    if manifest["secondary"] != "resolved" or secondary is None or not _same(secondary, bound, move_required=True):
        raise _NormalizationError("secondary_component_missing_or_mismatched")
    if secondary["schema_version"] == _SELF_SECONDARY:
        branches = secondary.get("branches")
    else:
        source_leaves = secondary.get("damage_roll_leaves")
        if not isinstance(source_leaves, (tuple, list)) or len(source_leaves) != 16 or not isinstance(source_leaves[roll["roll_index"]], Mapping):
            raise _NormalizationError("secondary_damage_roll_identity_missing")
        source = source_leaves[roll["roll_index"]]
        if source.get("damage") != roll["damage"] or source.get("roll_index") != roll["roll_index"]:
            raise _NormalizationError("secondary_damage_roll_identity_mismatch")
        branches = source.get("secondary_branches")
        if branches == ():
            return [_leaf(candidate, bound, path, consequence, critical_state, roll, {"eligibility": source.get("secondary_eligibility"), "branch": "not_applicable"})]
    if not isinstance(branches, (tuple, list)) or not branches:
        raise _NormalizationError("secondary_branches_missing")
    parsed = []
    for branch in branches:
        factor = _fraction(branch.get("conditional_secondary_probability") if isinstance(branch, Mapping) else None)
        if not isinstance(branch, Mapping) or branch.get("branch") not in {"effect", "no_effect"} or factor is None:
            raise _NormalizationError("invalid_secondary_branch")
        parsed.append((branch, factor))
    if not _partition(parsed):
        raise _NormalizationError("secondary_probability_mass_invalid")
    result = []
    for branch, factor in parsed:
        effect = {"branch": branch["branch"]}
        if "hypothetical_stage_effect" in branch:
            effect["hypothetical_stage_effect"] = deepcopy(branch["hypothetical_stage_effect"])
        if "hypothetical_target_condition" in branch:
            effect["hypothetical_target_condition"] = deepcopy(branch["hypothetical_target_condition"])
        if "hypothetical_target_flinch" in branch:
            effect["hypothetical_target_flinch"] = deepcopy(branch["hypothetical_target_flinch"])
        if "hypothetical_target_condition_removal" in branch:
            effect["hypothetical_target_condition_removal"] = deepcopy(branch["hypothetical_target_condition_removal"])
        result.append(_leaf(candidate, bound, path + ((f"secondary:{branch['branch']}", _fraction_dict(factor)),), consequence, critical_state, roll, effect))
    return result


def _secondary(consequence: Mapping[str, Any]) -> Mapping[str, Any] | None:
    values = [consequence.get(key) for key in ("probabilistic_self_stage_effect_uncertainty", "probabilistic_target_stage_effect_uncertainty", "thunderbolt_paralysis_uncertainty", "iron_head_flinch_uncertainty", "sparkling_aria_burn_clearing_uncertainty") if consequence.get(key) is not None]
    if len(values) != 1 or not isinstance(values[0], Mapping) or values[0].get("status") != "resolved" or values[0].get("schema_version") not in {_SELF_SECONDARY, _STAT_SECONDARY, _STATUS_SECONDARY, _FLINCH_SECONDARY, _CONDITION_REMOVAL_SECONDARY}:
        return None
    return values[0]


def _leaf(candidate: Mapping[str, Any], bound: Mapping[str, Any], path: tuple, consequence: Mapping[str, Any], critical_state: str | None, roll: Mapping[str, Any] | None, secondary: Mapping[str, Any] | None) -> dict[str, Any]:
    probability = Fraction(1, 1)
    for _, factor in path:
        probability *= Fraction(factor["numerator"], factor["denominator"])
    interval = consequence.get("interval") if isinstance(consequence.get("interval"), Mapping) else {}
    post = roll.get("post_hit_consequence") if roll is not None else None
    damage = post.get("actual_damage") if isinstance(post, Mapping) and isinstance(post.get("actual_damage"), int) and not isinstance(post.get("actual_damage"), bool) else roll.get("damage") if roll is not None else consequence.get("target_damage")
    hp_before = interval.get("target_hp_before")
    target_hp = max(0, hp_before - damage) if isinstance(hp_before, int) and not isinstance(hp_before, bool) and isinstance(damage, int) and not isinstance(damage, bool) else consequence.get("target_hp_after")
    own_hp = post.get("attacker_post_hit_hp") if isinstance(post, Mapping) else consequence.get("attacker_hp_after")
    if own_hp is None and isinstance(post, Mapping):
        own_hp = post.get("attacker_hp_after")
    focus_sash_survival = _focus_sash_survival(post, bound, hp_before, damage, target_hp)
    leaf_id = "/".join(name for name, _ in path)
    rendered_secondary = deepcopy(dict(secondary)) if isinstance(secondary, Mapping) else None
    removal = rendered_secondary.get("hypothetical_target_condition_removal") if isinstance(rendered_secondary, Mapping) else None
    if isinstance(removal, Mapping):
        removal["source_leaf_id"] = leaf_id
    return {
        "leaf_id": leaf_id, "candidate_id": candidate["candidate_id"], "action_type": candidate["action_type"],
        "branch_path": tuple({"branch": name, "conditional_probability": factor} for name, factor in path),
        "conditional_factors": tuple(factor for _, factor in path), "probability": _fraction_dict(probability),
        "hit_state": next((name for name, _ in path if name in {"hit", "miss"}), None), "critical_state": critical_state,
        "damage_roll": None if roll is None else {"roll_index": roll["roll_index"], "random_factor_percent": roll["random_factor_percent"], "damage": roll["damage"]},
        "consequences": {"damage": damage, "target_final_hp": target_hp, "target_ko": target_hp == 0 if isinstance(target_hp, int) else None, "own_final_hp": own_hp, "self_fainted": own_hp == 0 if isinstance(own_hp, int) else None, "post_hit": deepcopy(dict(post)) if isinstance(post, Mapping) else None, "source_hit_context": {"source_action_id": candidate["candidate_id"], "source_move_id": bound.get("move_id"), "actual_damage": damage, "target_routing": interval.get("target_routing", "target"), "target_pre_hp": hp_before, "target_post_hp": target_hp, "critical_state": critical_state, "roll_index": roll.get("roll_index") if isinstance(roll, Mapping) else None}, "sturdy_survival": deepcopy(post.get("sturdy_survival")) if isinstance(post, Mapping) and isinstance(post.get("sturdy_survival"), Mapping) else None, "focus_sash_survival": focus_sash_survival, "deterministic_stage_effect": deepcopy(dict(consequence["stage_effects"])) if isinstance(consequence.get("stage_effects"), Mapping) else None, "secondary": rendered_secondary},
        "provenance": deepcopy(dict(bound)),
    }


def _focus_sash_survival(post: Any, bound: Mapping[str, Any], hp_before: Any, damage: Any, target_hp: Any) -> dict[str, Any] | None:
    if not isinstance(post, Mapping) or not isinstance(post.get("focus_sash_survival"), Mapping):
        return None
    focus = post["focus_sash_survival"]
    if focus.get("outcome") != "applied":
        return deepcopy(dict(focus))
    item_after = focus.get("item_after")
    source = focus.get("source_hit")
    if (
        focus.get("item_before") != "focus-sash"
        or not isinstance(item_after, Mapping)
        or item_after.get("status") != "known_absent"
        or focus.get("focus_sash_eligible") is not True
        or focus.get("holder") != bound.get("target")
        or focus.get("hp_before") != hp_before
        or focus.get("target_final_hp") != target_hp
        or focus.get("actual_damage") != damage
        or focus.get("pre_survival_lethal") is not True
        or not isinstance(focus.get("raw_damage"), int)
        or isinstance(focus.get("raw_damage"), bool)
        or focus.get("raw_damage") < hp_before
        or not isinstance(source, Mapping)
        or source.get("move_id") != bound.get("move_id")
        or focus.get("provenance") != "exact_detached_focus_sash_survival_consumption_v1"
    ):
        raise _NormalizationError("focus_sash_survival_record_invalid")
    return deepcopy(dict(focus))


def _deterministic_switch(candidate: Mapping[str, Any], root: Any, manifest: Mapping[str, Any], bound: Mapping[str, Any]) -> dict[str, Any]:
    if any(manifest[name] != "not_applicable" for name in _COMPONENTS):
        return _result("incomplete", "manual_switch_probability_manifest_not_complete", bound)
    if not isinstance(root, Mapping) or root.get("status") != "complete" or not isinstance(root.get("outcome"), Mapping):
        return _result("incomplete", "manual_switch_outcome_incomplete", bound)
    outcome = root["outcome"]
    if outcome.get("schema_version") != "deterministic-candidate-outcome-v1" or outcome.get("candidate_id") != candidate["candidate_id"] or outcome.get("action_type") != "manual_switch" or outcome.get("source_branch_fingerprint") != bound["source_branch_fingerprint"] or outcome.get("completeness") != "complete":
        return _result("rejected", "manual_switch_outcome_binding_mismatch", bound)
    leaf = _leaf(candidate, bound, (("deterministic_manual_switch", _fraction_dict(Fraction(1, 1))),), outcome, None, None, None)
    return _complete(candidate, bound, [leaf], manifest)


def _complete(candidate: Mapping[str, Any], bound: Mapping[str, Any], leaves: list[dict[str, Any]], manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not leaves:
        return _result("rejected", "terminal_leaves_missing", bound)
    mass = sum((Fraction(leaf["probability"]["numerator"], leaf["probability"]["denominator"]) for leaf in leaves), Fraction(0, 1))
    if mass != 1:
        return _result("rejected", "root_probability_mass_not_one", bound, probability_mass=_fraction_dict(mass))
    return {"status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, "candidate_id": candidate["candidate_id"], "action_type": candidate["action_type"], "bindings": deepcopy(dict(bound)), "component_manifest": deepcopy(dict(manifest)), "terminal_leaves": tuple(leaves), "terminal_probability_mass": _fraction_dict(mass), "aggregation": "none_preserve_roll_identity", "provenance": "strict_detached_predictive_outcome_normalization_v1"}


def _manifest(value: Any, action_type: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_COMPONENTS):
        return {"status": "incomplete", "reason": "probability_component_manifest_missing_or_incomplete"}
    parsed: dict[str, str] = {}
    for name in _COMPONENTS:
        row = value.get(name)
        status = row.get("status") if isinstance(row, Mapping) else None
        if status in {"incomplete", "unsupported", "rejected"}:
            return {"status": status, "reason": f"{name}_component_{status}"}
        if status not in {"resolved", "not_applicable"}:
            return {"status": "incomplete", "reason": f"{name}_component_not_explicit"}
        parsed[name] = status
    if action_type == "attack" and parsed["accuracy"] == "not_applicable":
        return {"status": "incomplete", "reason": "attack_accuracy_component_not_explicitly_resolved"}
    return {"status": "resolved", **parsed}


def _bindings(candidate: Any, value: Any) -> dict[str, Any] | None:
    if not isinstance(candidate, Mapping) or candidate.get("action_type") not in {"attack", "manual_switch"} or not isinstance(candidate.get("candidate_id"), str) or not isinstance(value, Mapping):
        return None
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
    if not all(isinstance(value.get(name), str) and value[name] for name in required[:3]) or not isinstance(value.get("decision_owner"), Mapping):
        return None
    if any(candidate.get(name) != value.get(name) for name in ("session_id", "source_branch_fingerprint", "decision_owner")):
        return None
    if candidate["action_type"] == "attack":
        if not all(isinstance(value.get(name), Mapping) for name in ("attacker", "target")) or not isinstance(value.get("move_id"), str) or candidate["candidate_id"] != f"attack:{value['move_id']}":
            return None
    return deepcopy(dict(value))


def _same(value: Mapping[str, Any], bound: Mapping[str, Any], *, move_required: bool, inherited_identity: bool = False) -> bool:
    keys = ("session_id", "source_branch_fingerprint", "decision_owner") if inherited_identity else ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target")
    if any(value.get(name) != bound.get(name) for name in keys):
        return False
    return not move_required or value.get("move_id") == bound.get("move_id")


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or isinstance(value.get("numerator"), bool) or not isinstance(value.get("denominator"), int) or isinstance(value.get("denominator"), bool) or value["denominator"] <= 0 or value["numerator"] < 0 or value["numerator"] > value["denominator"]:
        return None
    return Fraction(value["numerator"], value["denominator"])


def _percent(value: Any) -> Fraction | None:
    return Fraction(value, 100) if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100 else None


def _fraction_dict(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _partition(values: list[tuple[Mapping[str, Any], Fraction]]) -> bool:
    return bool(values) and all(factor > 0 for _, factor in values) and sum((factor for _, factor in values), Fraction(0, 1)) == 1


def _result(status: str, reason: str, bound: Mapping[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    result = {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
    if bound is not None:
        result["bindings"] = deepcopy(dict(bound))
    result.update(extra)
    return result


class _NormalizationError(Exception):
    pass
