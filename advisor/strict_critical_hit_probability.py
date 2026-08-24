"""Pure strict critical-hit probability from detached runtime authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.crit import CRIT_GUARANTEED_STAGE, crit_probability


SCHEMA_VERSION = "strict-critical-hit-probability-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def assess_strict_critical_hit_probability(*, critical_hit_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Convert resolved canonical crit capability into an exact rational result."""
    authority = _authority(critical_hit_authority)
    if authority is None:
        return _result("rejected", "invalid_runtime_critical_hit_authority")
    bindings = _bindings(authority)
    if authority["status"] in {"incomplete", "unsupported"}:
        return {**bindings, "status": authority["status"], "schema_version": SCHEMA_VERSION,
                "move_id": authority["move"]["move_id"], "reason": _reason(authority),
                **({"missing_authority": [_reason(authority)]} if authority["status"] == "incomplete" else {})}
    capability = authority["capability_resolution"]
    if capability.get("status") != "resolved" or not _same_binding(authority, capability):
        return _result("rejected", "resolved_critical_hit_authority_binding_mismatch")
    stage = capability.get("crit_stage")
    blocker = capability.get("crit_blocker")
    if not isinstance(stage, int) or isinstance(stage, bool) or stage < 0 or not isinstance(blocker, Mapping) or blocker.get("status") not in {"known_present", "known_absent"}:
        return _result("rejected", "invalid_resolved_critical_hit_capability")
    blocked = blocker["status"] == "known_present"
    probability = (0, 1) if blocked else _fraction(stage)
    if probability is None:
        return _result("rejected", "invalid_canonical_critical_hit_stage")
    effective_stage = min(stage, CRIT_GUARANTEED_STAGE)
    always_crit = capability.get("move_rule") == "always-crit"
    return {
        **bindings, "status": "resolved", "schema_version": SCHEMA_VERSION,
        "result": "crit_blocked" if blocked else "exact_critical_hit_probability",
        "move_id": authority["move"]["move_id"], "move_rule": capability.get("move_rule"),
        "crit_stage": stage, "effective_crit_stage": effective_stage,
        "always_crit": always_crit, "crit_blocker": deepcopy(dict(blocker)),
        "critical_probability": {"numerator": probability[0], "denominator": probability[1]},
        "critical_hit_authority": deepcopy(dict(critical_hit_authority)),
        "provenance": "canonical_gen9_critical_hit_engine_to_strict_probability_v1",
    }


def _authority(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != "runtime-d0-critical-hit-authority-v1" or value.get("status") not in {"resolved", "incomplete", "unsupported"} or not _binding(value):
        return None
    if not _owner(value.get("decision_owner")) or not _owner(value.get("attacker")) or not _owner(value.get("target")) or value["attacker"] != value["decision_owner"] or value["attacker"].get("side") == value["target"].get("side"):
        return None
    move = value.get("move")
    if not isinstance(move, Mapping) or set(move) != {"move_id"} or not isinstance(move.get("move_id"), str) or not move["move_id"] or not isinstance(value.get("capability_resolution"), Mapping):
        return None
    return value


def _binding(value: Mapping[str, Any]) -> bool:
    return isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("source_runtime_fingerprint"), str) and bool(value["source_runtime_fingerprint"]) and isinstance(value.get("source_branch_fingerprint"), str) and bool(value["source_branch_fingerprint"])


def _same_binding(authority: Mapping[str, Any], capability: Mapping[str, Any]) -> bool:
    return all(authority.get(key) == capability.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "attacker", "target")) and authority["move"]["move_id"] == capability.get("move_id")


def _bindings(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": authority["session_id"], "source_runtime_fingerprint": authority["source_runtime_fingerprint"],
        "source_branch_fingerprint": authority["source_branch_fingerprint"],
        "decision_owner": deepcopy(dict(authority["decision_owner"])), "attacker": deepcopy(dict(authority["attacker"])),
        "target": deepcopy(dict(authority["target"])),
    }


def _fraction(stage: int) -> tuple[int, int] | None:
    try:
        value = crit_probability(stage)
    except (TypeError, ValueError):
        return None
    return value.numerator, value.denominator


def _reason(authority: Mapping[str, Any]) -> str:
    reason = authority.get("reason")
    if isinstance(reason, str) and reason:
        return reason
    capability = authority.get("capability_resolution")
    if isinstance(capability, Mapping) and isinstance(capability.get("reason"), str) and capability["reason"]:
        return capability["reason"]
    return "critical_hit_authority_unavailable"


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
