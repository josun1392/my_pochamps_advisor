"""Detached per-roll Thunderbolt paralysis branches from strict D0 authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "deterministic-predictive-thunderbolt-paralysis-uncertainty-v1"
HORIZON = "immediate_action_consequence"


def compose_predictive_thunderbolt_paralysis_uncertainty(
    *, candidate: Mapping[str, Any], interval: Mapping[str, Any], runtime_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach status choices only to exact surviving direct-hit damage rolls."""
    authority = _authority(runtime_authority)
    if authority.get("status") != "resolved":
        return authority
    if not _candidate(candidate) or candidate.get("candidate_id") != "attack:thunderbolt" or any(candidate.get(key) != authority[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner")):
        return _result("rejected", "thunderbolt_paralysis_candidate_binding_mismatch")
    if not _interval(interval, authority):
        return _result("rejected", "thunderbolt_paralysis_hit_leaf_binding_mismatch")
    numerator, denominator = authority["probability"]["numerator"], authority["probability"]["denominator"]
    blocked = authority["target_substitute"]["state"] == "known_active"
    target_hp = interval["target_hp_before"]
    leaves, possible = [], []
    for index, damage in enumerate(interval["exact_damage_rolls"]):
        survived = damage < target_hp
        leaf = {
            "roll_index": index, "random_factor_percent": 85 + index, "damage": damage,
            "roll_probability": {"numerator": 1, "denominator": 16},
            "target_post_hit_hp": max(0, target_hp - damage), "target_survived": survived,
        }
        if not survived:
            leaf["secondary_eligibility"] = "target_fainted"
            leaf["secondary_branches"] = ()
        elif blocked:
            leaf["secondary_eligibility"] = "blocked_by_substitute"
            leaf["secondary_branches"] = (_branch("no_effect", 100, 100),)
        elif numerator == 0:
            leaf["secondary_eligibility"] = "ineligible_or_suppressed"
            leaf["secondary_branches"] = (_branch("no_effect", denominator, denominator),)
        else:
            hypothetical = _hypothetical_condition(authority)
            no_effect, effect = _branch("no_effect", denominator - numerator, denominator), _branch("effect", numerator, denominator, hypothetical)
            leaf["secondary_eligibility"] = "eligible"
            leaf["secondary_branches"] = (effect,) if numerator == denominator else (no_effect, effect)
            possible.append({"roll_index": index, "random_factor_percent": 85 + index, "hypothetical_target_condition": deepcopy(hypothetical)})
        leaves.append(leaf)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        "session_id": authority["session_id"], "source_runtime_fingerprint": authority["source_runtime_fingerprint"],
        "source_branch_fingerprint": authority["source_branch_fingerprint"], "decision_owner": deepcopy(dict(authority["decision_owner"])),
        "attacker": deepcopy(dict(authority["attacker"])), "target": deepcopy(dict(authority["target"])), "move_id": "thunderbolt",
        "runtime_authority": deepcopy(dict(runtime_authority)), "effect_probability": deepcopy(dict(authority["probability"])),
        "current_target_condition_authority": deepcopy(dict(authority["current_target_condition_authority"])),
        "target_substitute_authority": deepcopy(dict(authority["target_substitute"])),
        "damage_roll_leaves": tuple(leaves), "guaranteed_conditions": (), "possible_conditions": tuple(possible),
        "provenance": "runtime_d0_thunderbolt_status_capability_to_detached_predictive_per_roll_condition_branches_v1",
    }


def _authority(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_runtime_thunderbolt_paralysis_authority")
    status = value.get("status")
    if status in {"incomplete", "unsupported", "rejected"}:
        return _result(status, _reason(value, "runtime_thunderbolt_paralysis_authority_unavailable"))
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move", "capability_resolution", "current_target_condition_authority", "target_type_authority", "target_substitute_authority")
    if status != "resolved" or value.get("schema_version") != "runtime-d0-thunderbolt-paralysis-authority-v1" or not all(key in value for key in required):
        return _result("rejected", "invalid_resolved_runtime_thunderbolt_paralysis_authority")
    move, capability, condition, substitute = value["move"], value["capability_resolution"], value["current_target_condition_authority"], value["target_substitute_authority"]
    if not _owners(value) or not isinstance(move, Mapping) or move.get("move_id") != "thunderbolt" or not isinstance(capability, Mapping) or capability.get("status") != "resolved" or not _condition_binding(condition, value) or not _substitute(substitute):
        return _result("rejected", "invalid_resolved_runtime_thunderbolt_paralysis_authority")
    probability, effect = capability.get("probability"), capability.get("effect")
    if capability.get("move_id") != "thunderbolt" or not _fraction(probability) or effect != {"owner": "target", "condition": "paralysis"} or capability.get("suppressed") is not (probability["numerator"] == 0):
        return _result("rejected", "invalid_thunderbolt_paralysis_capability_resolution")
    condition_state = condition.get("condition")
    if not isinstance(condition_state, Mapping) or condition_state.get("status") not in {"known_none", "known_present"}:
        return _result("rejected", "thunderbolt_paralysis_condition_authority_not_exact")
    return {
        "status": "resolved", "session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"],
        "source_branch_fingerprint": value["source_branch_fingerprint"], "decision_owner": value["decision_owner"],
        "attacker": value["attacker"], "target": value["target"], "probability": probability,
        "current_target_condition_authority": condition, "target_substitute": substitute,
    }


def _hypothetical_condition(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "detached-hypothetical-current-condition-v1", "owner": deepcopy(dict(authority["target"])),
        "previous_condition": deepcopy(dict(authority["current_target_condition_authority"]["condition"])),
        "resulting_condition": "paralysis", "provenance": "thunderbolt_successful_damage_roll_secondary_v1",
    }


def _interval(value: Any, authority: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("completeness") == "exact_complete" and value.get("move_id") == "thunderbolt" and value.get("session_id") == authority["session_id"] and value.get("source_branch_fingerprint") == authority["source_branch_fingerprint"] and value.get("decision_owner") == authority["decision_owner"] and value.get("target_routing") == "target" and isinstance(value.get("target_hp_before"), int) and not isinstance(value.get("target_hp_before"), bool) and value["target_hp_before"] > 0 and isinstance(value.get("exact_damage_rolls"), tuple) and len(value["exact_damage_rolls"]) == 16 and all(isinstance(damage, int) and not isinstance(damage, bool) and damage > 0 for damage in value["exact_damage_rolls"])


def _condition_binding(condition: Any, authority: Mapping[str, Any]) -> bool:
    return isinstance(condition, Mapping) and condition.get("status") == "resolved" and condition.get("schema_version") == "runtime-current-condition-authority-v1" and all(condition.get(key) == authority.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) and condition.get("owner") == authority.get("target")


def _candidate(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("action_type") == "attack" and isinstance(value.get("candidate_id"), str) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("source_branch_fingerprint"), str) and bool(value["source_branch_fingerprint"]) and _owner(value.get("decision_owner"))


def _owners(value: Mapping[str, Any]) -> bool:
    return all(isinstance(value.get(key), str) and value[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) and all(_owner(value.get(key)) for key in ("decision_owner", "attacker", "target")) and value["attacker"]["side"] != value["target"]["side"] and value["attacker"] == value["decision_owner"]


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("side") in {"self", "opponent"} and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _fraction(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("numerator"), int) and not isinstance(value.get("numerator"), bool) and isinstance(value.get("denominator"), int) and not isinstance(value.get("denominator"), bool) and value["denominator"] > 0 and 0 <= value["numerator"] <= value["denominator"]


def _substitute(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "known" or value.get("state") not in {"known_active", "known_inactive"}:
        return False
    return (value["state"] == "known_inactive" and set(value) == {"status", "state"}) or (value["state"] == "known_active" and isinstance(value.get("substitute_hp"), int) and not isinstance(value.get("substitute_hp"), bool) and value["substitute_hp"] > 0 and set(value) == {"status", "state", "substitute_hp"})


def _branch(name: str, numerator: int, denominator: int, condition: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = {"branch": name, "conditional_secondary_probability": {"numerator": numerator, "denominator": denominator}}
    if condition is not None:
        result["hypothetical_target_condition"] = deepcopy(dict(condition))
    return result


def _reason(value: Mapping[str, Any], fallback: str) -> str:
    return value.get("reason") if isinstance(value.get("reason"), str) and value["reason"] else fallback


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
