"""Pure Gen 9 regular-accuracy assessment from already-bound authority.

This module owns neither reducer/runtime state nor capability classification.
It composes the strict stage adapter and the detached capability-resolution
projection using the Gen V+ Q12 accuracy contract.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "strict-deterministic-hit-probability-v1"
Q12_ONE = 4096
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def chain_accuracy_modifier_q12(current_q12: int, factor_q12: int) -> int:
    """Chain a Q12 accuracy factor with nearest rounding and ties upward."""
    if not _positive_int(current_q12) or not _positive_int(factor_q12):
        raise ValueError("accuracy Q12 factors must be positive integers")
    return (current_q12 * factor_q12 + 2048) >> 12


def apply_accuracy_modifier_q12(base_accuracy: int, modifier_q12: int) -> int:
    """Apply a Q12 accuracy modifier with half-down rounding."""
    if not _accuracy(base_accuracy) or not _positive_int(modifier_q12):
        raise ValueError("base accuracy and modifier must be valid")
    return (base_accuracy * modifier_q12 + 2047) >> 12


def apply_accuracy_evasion_stages(modified_base_accuracy: int, net_stage: int) -> int:
    """Apply the clamped Gen V+ combined Accuracy/Evasion stage ratio."""
    if not _nonnegative_int(modified_base_accuracy) or not _stage(net_stage):
        raise ValueError("modified base accuracy and stage must be valid")
    if net_stage >= 0:
        return modified_base_accuracy * (3 + net_stage) // 3
    return modified_base_accuracy * 3 // (3 - net_stage)


def assess_strict_deterministic_hit_probability(
    *, move: Mapping[str, Any], strict_stage_authority: Mapping[str, Any] | None,
    modifier_authority: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return an exact regular-accuracy result or fail closed.

    ``move`` supplies only canonical move metadata.  The remaining inputs must
    already be detached authority objects; this function never reads runtime
    state and never turns omitted data into a neutral modifier or stage.
    """
    normalized_move = _move(move)
    if normalized_move is None:
        return _result("rejected", "invalid_hit_probability_move")
    if normalized_move["always_hit"]:
        return {
            "status": "resolved", "schema_version": SCHEMA_VERSION,
            "result": "always_hit", "move_id": normalized_move["move_id"],
            "accuracy_check": "bypassed_by_move_metadata",
            "reason": "move_always_hits",
        }
    modifier = _modifier_authority(modifier_authority)
    if modifier is None:
        return _result("rejected", "invalid_strict_hit_probability_authority")
    stage = _stage_authority(strict_stage_authority)
    bindings = _bindings(modifier)
    if modifier["status"] == "incomplete":
        return {**bindings, "status": "incomplete", "schema_version": SCHEMA_VERSION,
                "move_id": normalized_move["move_id"], "reason": _authority_reason(modifier),
                "missing_authority": _missing_authority(modifier)}
    if modifier["status"] == "unsupported":
        return {**bindings, "status": "unsupported", "schema_version": SCHEMA_VERSION,
                "move_id": normalized_move["move_id"], "reason": _authority_reason(modifier)}
    if stage is None:
        return {**bindings, "status": "incomplete", "schema_version": SCHEMA_VERSION,
                "move_id": normalized_move["move_id"], "reason": _authority_reason(strict_stage_authority or {}),
                "missing_authority": _missing_authority(strict_stage_authority or {})}
    if not _same_binding(stage, modifier) or stage["attacker"] != modifier["attacker"] or stage["target"] != modifier["target"]:
        return _result("rejected", "strict_hit_probability_authority_binding_mismatch")
    if modifier["move"] != {"move_id": normalized_move["move_id"], "category": normalized_move["category"]}:
        return _result("rejected", "strict_hit_probability_move_authority_mismatch")
    if modifier["status"] != "resolved":
        return _result("rejected", "invalid_hit_modifier_authority_status")
    if stage["status"] != "resolved":
        return {**bindings, "status": "incomplete", "schema_version": SCHEMA_VERSION,
                "move_id": normalized_move["move_id"], "reason": _authority_reason(stage),
                "missing_authority": _missing_authority(stage)}

    factor_result = _factors(modifier["capability_resolution"])
    if factor_result.get("status") != "resolved":
        return {**bindings, "schema_version": SCHEMA_VERSION, "move_id": normalized_move["move_id"], **factor_result}
    modifier_q12 = Q12_ONE
    for factor in factor_result["factors"]:
        modifier_q12 = chain_accuracy_modifier_q12(modifier_q12, factor)
    attacker_stage, target_stage = _stage_values(stage)
    net_stage = max(-6, min(6, attacker_stage - target_stage))
    modified_base = apply_accuracy_modifier_q12(normalized_move["accuracy"], modifier_q12)
    threshold = apply_accuracy_evasion_stages(modified_base, net_stage)
    return {
        **bindings, "status": "resolved", "schema_version": SCHEMA_VERSION,
        "result": "exact_regular_accuracy", "move_id": normalized_move["move_id"],
        "move_category": normalized_move["category"], "base_accuracy": normalized_move["accuracy"],
        "modifier_chain_q12": modifier_q12, "applicable_modifier_factors_q12": tuple(factor_result["factors"]),
        "modified_base_accuracy": modified_base, "attacker_accuracy_stage": attacker_stage,
        "target_evasion_stage": target_stage, "net_stage": net_stage,
        "raw_accuracy_threshold": threshold, "probability_percent": max(0, min(100, threshold)),
        "accuracy_check_only": True,
        "stage_authority": deepcopy(dict(strict_stage_authority)),
        "modifier_authority": deepcopy(dict(modifier_authority)),
    }


def _move(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("move_id"), str) or not value["move_id"]:
        return None
    if value.get("always_hit") is True:
        return {"move_id": value["move_id"], "always_hit": True}
    if value.get("category") not in {"physical", "special", "status"} or not _accuracy(value.get("accuracy")):
        return None
    return {"move_id": value["move_id"], "category": value["category"], "accuracy": value["accuracy"], "always_hit": False}


def _stage_authority(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != "strict-hit-stage-authority-v1":
        return None
    if value.get("status") != "resolved" or not _binding(value):
        return None
    if not _owner(value.get("attacker")) or not _owner(value.get("target")):
        return None
    return value


def _modifier_authority(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != "runtime-d0-hit-modifier-authority-v1":
        return None
    if value.get("status") not in {"resolved", "incomplete", "unsupported"} or not _binding(value):
        return None
    if not _owner(value.get("attacker")) or not _owner(value.get("target")):
        return None
    move = value.get("move")
    if not isinstance(move, Mapping) or set(move) != {"move_id", "category"}:
        return None
    if not isinstance(move["move_id"], str) or not move["move_id"] or move["category"] not in {"physical", "special", "status"}:
        return None
    if not isinstance(value.get("capability_resolution"), Mapping):
        return None
    return value


def _binding(value: Mapping[str, Any]) -> bool:
    return (
        isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and isinstance(value.get("source_runtime_fingerprint"), str) and bool(value["source_runtime_fingerprint"])
        and isinstance(value.get("source_branch_fingerprint"), str) and bool(value["source_branch_fingerprint"])
    )


def _same_binding(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left[key] == right[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint"))


def _bindings(stage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": stage["session_id"], "source_runtime_fingerprint": stage["source_runtime_fingerprint"],
        "source_branch_fingerprint": stage["source_branch_fingerprint"],
        "attacker": deepcopy(dict(stage["attacker"])), "target": deepcopy(dict(stage["target"])),
    }


def _factors(capability: Mapping[str, Any]) -> dict[str, Any]:
    if capability.get("status") != "resolved" or not isinstance(capability.get("ledger"), tuple):
        return {"status": "rejected", "reason": "invalid_resolved_hit_modifier_capability"}
    factors: list[int] = []
    for row in capability["ledger"]:
        if not isinstance(row, Mapping) or row.get("state") != "applicable":
            continue
        effect = row.get("effect")
        if not isinstance(effect, Mapping) or effect.get("kind") != "accuracy_multiplier_q12":
            return {"status": "unsupported", "reason": "unsupported_resolved_hit_modifier_effect"}
        if effect.get("ordering") != "before_accuracy_evasion_stages" or effect.get("denominator") != Q12_ONE or not _positive_int(effect.get("numerator")):
            return {"status": "rejected", "reason": "invalid_accuracy_modifier_effect"}
        factors.append(effect["numerator"])
    return {"status": "resolved", "factors": factors}


def _stage_values(stage: Mapping[str, Any]) -> tuple[int, int]:
    context = stage.get("stat_stage_context")
    rows = context.get("current_stages") if isinstance(context, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError("strict stage authority lacks stage context")
    values = {(row.get("side"), row.get("stat")): row.get("stage") for row in rows if isinstance(row, Mapping)}
    attacker, target = values.get(("self", "accuracy")), values.get(("opponent", "evasion"))
    if not _stage(attacker) or not _stage(target):
        raise ValueError("strict stage authority has invalid stage values")
    return attacker, target


def _authority_reason(value: Mapping[str, Any]) -> str:
    reason = value.get("reason")
    if isinstance(reason, str) and reason:
        return reason
    capability = value.get("capability_resolution")
    if isinstance(capability, Mapping) and isinstance(capability.get("reason"), str):
        return capability["reason"]
    return "hit_probability_authority_incomplete"


def _missing_authority(value: Mapping[str, Any]) -> list[str]:
    missing = value.get("missing_authority")
    if isinstance(missing, list) and all(isinstance(item, str) for item in missing):
        return list(missing)
    stage = value.get("strict_stage_authority")
    if isinstance(stage, Mapping) and isinstance(stage.get("missing_authority"), list):
        return list(stage["missing_authority"])
    return [_authority_reason(value)]


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and all(
        isinstance(value.get(key), str) and bool(value[key]) for key in ("session_id", "side", "pokemon_id")
    ) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0


def _accuracy(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 100


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _stage(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and -6 <= value <= 6


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
