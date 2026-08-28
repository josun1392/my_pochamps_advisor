"""Detached deterministic Sparkling Aria burn-clearing terminal effects."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_predictive_post_hit_target_outcomes import resolve_predictive_post_hit_target_outcomes


SCHEMA_VERSION = "deterministic-predictive-sparkling-aria-burn-clearing-uncertainty-v1"


def compose_predictive_sparkling_aria_burn_clearing_uncertainty(*, candidate: Mapping[str, Any], interval: Mapping[str, Any], runtime_authority: Mapping[str, Any], post_hit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    authority = _authority(runtime_authority)
    if authority.get("status") != "resolved":
        return authority
    if not _candidate(candidate, authority) or not _interval(interval, authority):
        return _result("rejected", "sparkling_aria_candidate_or_hit_leaf_binding_mismatch")
    outcomes = resolve_predictive_post_hit_target_outcomes(interval=interval, post_hit=post_hit)
    if outcomes.get("status") != "resolved":
        return outcomes
    leaves = []
    for index, outcome in enumerate(outcomes["outcomes"]):
        leaf = {
            "roll_index": index, "random_factor_percent": 85 + index,
            "damage": outcome["raw_damage"], "roll_probability": {"numerator": 1, "denominator": 16},
            "actual_damage": outcome["actual_damage"], "target_post_hit_hp": outcome["target_post_hit_hp"],
            "target_survived": outcome["target_survived"],
        }
        reason = _eligibility(authority, outcome)
        leaf["secondary_eligibility"] = reason
        leaf["secondary_branches"] = (_effect_branch() if reason == "eligible" else _no_effect_branch(reason),)
        leaves.append(leaf)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": "immediate_action_consequence",
        **{key: deepcopy(runtime_authority[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target")},
        "move_id": "sparkling-aria", "runtime_authority": deepcopy(dict(runtime_authority)),
        "damage_roll_leaves": tuple(leaves),
        "provenance": "runtime_d0_sparkling_aria_burn_clearing_capability_to_detached_predictive_per_roll_terminal_effect_v1",
    }


def _authority(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_runtime_sparkling_aria_burn_clearing_authority")
    if value.get("status") in {"incomplete", "unsupported", "rejected"}:
        return _result(value["status"], value.get("reason", "runtime_sparkling_aria_burn_clearing_authority_unavailable"))
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move", "capability_resolution", "target_substitute_authority")
    if value.get("status") != "resolved" or value.get("schema_version") != "runtime-d0-sparkling-aria-burn-clearing-authority-v1" or not all(key in value for key in required):
        return _result("rejected", "invalid_resolved_runtime_sparkling_aria_burn_clearing_authority")
    capability, substitute = value["capability_resolution"], value["target_substitute_authority"]
    if not isinstance(capability, Mapping) or capability.get("status") != "resolved" or capability.get("effect") != {"owner": "target", "condition_before": "burn", "condition_removed": "burn", "condition_after": "none"}:
        return _result("rejected", "invalid_sparkling_aria_burn_clearing_capability_resolution")
    if not isinstance(substitute, Mapping) or substitute.get("status") != "known" or substitute.get("state") not in {"known_active", "known_inactive"}:
        return _result("rejected", "invalid_sparkling_aria_target_substitute_authority")
    return {"status": "resolved", **{key: value[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target")}, "effect_applicable": capability.get("effect_applicable") is True, "target_substitute": substitute}


def _candidate(value: Any, authority: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("candidate_id") == "attack:sparkling-aria" and value.get("action_type") == "attack" and all(value.get(key) == authority[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner"))


def _interval(value: Any, authority: Mapping[str, Any]) -> bool:
    rolls = value.get("exact_damage_rolls") if isinstance(value, Mapping) else None
    return isinstance(value, Mapping) and value.get("completeness") == "exact_complete" and value.get("move_id") == "sparkling-aria" and all(value.get(key) == authority[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner")) and value.get("target_routing") == "target" and isinstance(value.get("target_hp_before"), int) and value["target_hp_before"] > 0 and isinstance(rolls, tuple) and len(rolls) == 16


def _eligibility(authority: Mapping[str, Any], outcome: Mapping[str, Any]) -> str:
    if not authority["effect_applicable"]:
        return "target_condition_not_burn"
    if authority["target_substitute"]["state"] == "known_active":
        return "blocked_by_substitute"
    if not outcome["target_survived"]:
        return "target_fainted"
    return "eligible"


def _effect_branch() -> dict[str, Any]:
    return {"branch": "effect", "conditional_secondary_probability": {"numerator": 1, "denominator": 1}, "hypothetical_target_condition_removal": {"schema_version": "detached-hypothetical-target-condition-removal-v1", "condition_before": "burn", "condition_removed": "burn", "condition_after": "none", "removal_trigger": "successful_damaging_hit_target_survives", "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1"}}


def _no_effect_branch(reason: str) -> dict[str, Any]:
    return {"branch": "no_effect", "conditional_secondary_probability": {"numerator": 1, "denominator": 1}, "reason": reason}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
