"""Detached exact Iron Head flinch branches over already-computed hit rolls."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_predictive_post_hit_target_outcomes import resolve_predictive_post_hit_target_outcomes


SCHEMA_VERSION = "deterministic-predictive-iron-head-flinch-uncertainty-v1"
HORIZON = "immediate_action_consequence"


def compose_predictive_iron_head_flinch_uncertainty(*, candidate: Mapping[str, Any], interval: Mapping[str, Any], runtime_authority: Mapping[str, Any], post_hit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    authority = _authority(runtime_authority)
    if authority.get("status") != "resolved": return authority
    if not _candidate(candidate, authority) or not _interval(interval, authority):
        return _result("rejected", "iron_head_flinch_candidate_or_hit_leaf_binding_mismatch")
    outcomes = resolve_predictive_post_hit_target_outcomes(interval=interval, post_hit=post_hit)
    if outcomes.get("status") != "resolved": return outcomes
    numerator, denominator = authority["probability"]["numerator"], authority["probability"]["denominator"]
    blocked = authority["target_substitute"]["state"] == "known_active"
    leaves = []
    for index, outcome in enumerate(outcomes["outcomes"]):
        survived = outcome["target_survived"]
        leaf = {"roll_index": index, "random_factor_percent": 85 + index, "damage": outcome["raw_damage"], "roll_probability": {"numerator": 1, "denominator": 16}, "actual_damage": outcome["actual_damage"], "target_post_hit_hp": outcome["target_post_hit_hp"], "target_survived": survived}
        if not survived:
            leaf.update(secondary_eligibility="target_fainted", secondary_branches=())
        elif blocked:
            leaf.update(secondary_eligibility="blocked_by_substitute", secondary_branches=(_branch("no_effect", 1, 1),))
        else:
            no_effect, effect = _branch("no_effect", denominator - numerator, denominator), _branch("effect", numerator, denominator)
            leaf.update(secondary_eligibility="eligible", secondary_branches=(no_effect, effect))
        leaves.append(leaf)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, "session_id": authority["session_id"], "source_runtime_fingerprint": authority["source_runtime_fingerprint"], "source_branch_fingerprint": authority["source_branch_fingerprint"], "decision_owner": deepcopy(dict(authority["decision_owner"])), "attacker": deepcopy(dict(authority["attacker"])), "target": deepcopy(dict(authority["target"])), "move_id": "iron-head", "runtime_authority": deepcopy(dict(runtime_authority)), "effect_probability": deepcopy(dict(authority["probability"])), "target_substitute_authority": deepcopy(dict(authority["target_substitute"])), "damage_roll_leaves": tuple(leaves), "provenance": "runtime_d0_iron_head_flinch_capability_to_detached_predictive_per_roll_branches_v1"}


def _authority(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping): return _result("rejected", "invalid_runtime_iron_head_flinch_authority")
    if value.get("status") in {"incomplete", "unsupported", "rejected"}: return _result(value["status"], value.get("reason", "runtime_iron_head_flinch_authority_unavailable"))
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move", "capability_resolution", "target_substitute_authority")
    if value.get("status") != "resolved" or value.get("schema_version") != "runtime-d0-iron-head-flinch-authority-v1" or not all(key in value for key in required): return _result("rejected", "invalid_resolved_runtime_iron_head_flinch_authority")
    capability, substitute = value["capability_resolution"], value["target_substitute_authority"]
    if not isinstance(capability, Mapping) or capability.get("status") != "resolved" or capability.get("effect") != {"owner": "target", "state": "flinch"} or not _fraction(capability.get("probability")) or not _substitute(substitute): return _result("rejected", "invalid_iron_head_flinch_capability_resolution")
    return {"status": "resolved", **{key: value[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target")}, "probability": capability["probability"], "target_substitute": substitute}


def _candidate(value: Any, authority: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("candidate_id") == "attack:iron-head" and value.get("action_type") == "attack" and all(value.get(key) == authority[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner"))


def _interval(value: Any, authority: Mapping[str, Any]) -> bool:
    rolls = value.get("exact_damage_rolls") if isinstance(value, Mapping) else None
    return isinstance(value, Mapping) and value.get("completeness") == "exact_complete" and value.get("move_id") == "iron-head" and all(value.get(key) == authority[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner")) and value.get("target_routing") == "target" and isinstance(value.get("target_hp_before"), int) and not isinstance(value["target_hp_before"], bool) and value["target_hp_before"] > 0 and isinstance(rolls, tuple) and len(rolls) == 16 and all(isinstance(damage, int) and not isinstance(damage, bool) and damage > 0 for damage in rolls)


def _branch(name: str, numerator: int, denominator: int) -> dict[str, Any]:
    result = {"branch": name, "conditional_secondary_probability": {"numerator": numerator, "denominator": denominator}}
    if name == "effect": result["hypothetical_target_flinch"] = {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "provenance": "iron_head_successful_damage_roll_secondary_v1"}
    return result


def _fraction(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("numerator"), int) and isinstance(value.get("denominator"), int) and 0 < value["numerator"] <= value["denominator"]


def _substitute(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and value.get("state") in {"known_active", "known_inactive"}


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
