"""Detached effect/no-effect branches for catalogued self stage secondaries."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_predictive_deterministic_stage_effects import compose_predictive_self_stage_effect


SCHEMA_VERSION = "deterministic-predictive-probabilistic-self-stage-effect-uncertainty-v1"
HORIZON = "immediate_action_consequence"


def compose_predictive_probabilistic_self_stage_effect_uncertainty(
    *, candidate: Mapping[str, Any], interval: Mapping[str, Any], runtime_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Branch a resolved secondary only inside an exact successful hit leaf."""
    authority = _authority(runtime_authority)
    if authority.get("status") != "resolved":
        return authority
    if not _candidate(candidate) or candidate.get("candidate_id") != f"attack:{authority['move_id']}" or any(candidate.get(key) != authority[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner")):
        return _result("rejected", "probabilistic_self_stage_candidate_binding_mismatch")
    if not _interval(interval, authority):
        return _result("rejected", "probabilistic_self_stage_hit_leaf_binding_mismatch")
    materialized = compose_predictive_self_stage_effect(
        interval=interval, effect=authority["effect"], current_stage=authority["current_attack_stage"],
    )
    if materialized.get("status") != "resolved":
        return materialized
    numerator, denominator = authority["probability"]["numerator"], authority["probability"]["denominator"]
    no_effect = _branch("no_effect", denominator - numerator, denominator, None)
    effect = _branch("effect", numerator, denominator, materialized["effect"])
    branches = (no_effect,) if numerator == 0 else (effect,) if numerator == denominator else (no_effect, effect)
    effects = tuple(branch["hypothetical_stage_effect"] for branch in branches if isinstance(branch.get("hypothetical_stage_effect"), Mapping))
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        "session_id": authority["session_id"], "source_runtime_fingerprint": authority["source_runtime_fingerprint"],
        "source_branch_fingerprint": authority["source_branch_fingerprint"], "decision_owner": deepcopy(dict(authority["decision_owner"])),
        "attacker": deepcopy(dict(authority["attacker"])), "target": deepcopy(dict(authority["target"])), "move_id": authority["move_id"],
        "runtime_authority": deepcopy(dict(runtime_authority)), "effect_probability": deepcopy(dict(authority["probability"])),
        "shared_successful_hit_consequence": "inherited_from_enclosing_hit_leaf", "branches": branches,
        "guaranteed_effects": effects if len(branches) == 1 and numerator == denominator else (),
        "possible_effects": effects if numerator > 0 else (),
        "provenance": "runtime_d0_self_stage_capability_to_detached_predictive_effect_branches_v1",
    }


def _authority(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_runtime_probabilistic_self_stage_authority")
    status = value.get("status")
    if status in {"incomplete", "unsupported", "rejected"}:
        return _result(status, _reason(value, "runtime_probabilistic_self_stage_authority_unavailable"))
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move", "capability_resolution", "current_stage_authority", "current_attack_stage")
    if status != "resolved" or value.get("schema_version") != "runtime-d0-probabilistic-self-stage-effect-authority-v1" or not all(key in value for key in required):
        return _result("rejected", "invalid_resolved_runtime_probabilistic_self_stage_authority")
    move, capability, stage = value["move"], value["capability_resolution"], value["current_attack_stage"]
    if not _owners(value) or not isinstance(move, Mapping) or not isinstance(capability, Mapping) or capability.get("status") != "resolved" or not isinstance(stage, Mapping):
        return _result("rejected", "invalid_resolved_runtime_probabilistic_self_stage_authority")
    move_id, probability, effect = move.get("move_id"), capability.get("probability"), capability.get("effect")
    if not isinstance(move_id, str) or not move_id or capability.get("move_id") != move_id or not _fraction(probability) or not _effect(effect) or capability.get("suppressed") is not (probability["numerator"] == 0):
        return _result("rejected", "invalid_probabilistic_self_stage_capability_resolution")
    if not _current_attack_stage(stage) or not _stage_binding(value["current_stage_authority"], value):
        return _result("rejected", "probabilistic_self_stage_authority_binding_mismatch")
    return {
        "status": "resolved", "session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"],
        "source_branch_fingerprint": value["source_branch_fingerprint"], "decision_owner": value["decision_owner"],
        "attacker": value["attacker"], "target": value["target"], "move_id": move_id,
        "probability": probability, "effect": effect, "current_attack_stage": stage,
    }


def _interval(value: Any, authority: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("completeness") == "exact_complete" and value.get("move_id") == authority["move_id"] and value.get("session_id") == authority["session_id"] and value.get("source_branch_fingerprint") == authority["source_branch_fingerprint"] and value.get("decision_owner") == authority["decision_owner"] and value.get("target_routing") in {"target", "substitute"} and isinstance(value.get("exact_damage_rolls"), tuple) and len(value["exact_damage_rolls"]) == 16 and all(isinstance(damage, int) and not isinstance(damage, bool) and damage > 0 for damage in value["exact_damage_rolls"])


def _candidate(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("action_type") == "attack" and isinstance(value.get("candidate_id"), str) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("source_branch_fingerprint"), str) and bool(value["source_branch_fingerprint"]) and _owner(value.get("decision_owner"))


def _owners(value: Mapping[str, Any]) -> bool:
    return all(isinstance(value.get(key), str) and value[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) and all(_owner(value.get(key)) for key in ("decision_owner", "attacker", "target")) and value["attacker"]["side"] != value["target"]["side"] and value["attacker"] == value["decision_owner"]


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("side") in {"self", "opponent"} and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _fraction(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("numerator"), int) and not isinstance(value.get("numerator"), bool) and isinstance(value.get("denominator"), int) and not isinstance(value.get("denominator"), bool) and value["denominator"] > 0 and 0 <= value["numerator"] <= value["denominator"]


def _effect(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("owner") == "self" and value.get("stat") == "attack" and value.get("delta") == 1


def _current_attack_stage(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("value"), int) and not isinstance(value.get("value"), bool) and -6 <= value["value"] <= 6


def _stage_binding(stage: Any, authority: Mapping[str, Any]) -> bool:
    return isinstance(stage, Mapping) and stage.get("status") == "resolved" and stage.get("schema_version") == "runtime-current-stage-authority-v1" and all(stage.get(key) == authority.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) and stage.get("owner") == authority.get("attacker") and isinstance(stage.get("stages"), Mapping) and stage["stages"].get("attack") == authority.get("current_attack_stage")


def _branch(name: str, numerator: int, denominator: int, effect: Mapping[str, Any] | None) -> dict[str, Any]:
    result = {"branch": name, "conditional_secondary_probability": {"numerator": numerator, "denominator": denominator}}
    if effect is not None:
        result["hypothetical_stage_effect"] = deepcopy(dict(effect))
    return result


def _reason(value: Mapping[str, Any], fallback: str) -> str:
    return value.get("reason") if isinstance(value.get("reason"), str) and value["reason"] else fallback


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
