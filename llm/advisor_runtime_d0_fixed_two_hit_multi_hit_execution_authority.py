"""Strict D0 authority for a future fixed-two-hit materializer.

This owner classifies only the deliberately small family whose hit count and
per-hit critical semantics are already canonical.  It is not a damage
calculator and deliberately does not expose the legacy aggregate multi-hit
damage result as a substitute for per-hit stateful execution.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_strict_critical_hit_probability_assessment,
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-fixed-two-hit-multi-hit-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
# These identifiers are an explicit canonical execution catalog, not a name
# heuristic.  Both are ordinary two-hit normal-formula attacks with no
# move-owned secondary, drain, recoil, or escalating-power behavior.
_SUPPORTED_FIXED_TWO_HIT_MOVES = frozenset({"double-hit", "double-kick"})


def freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one own selectable fixed-two-hit attack for later execution."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    active = strategy_d0.get("active_owners", {})
    own = strategy_d0.get("decision_owner")
    opponent = active.get("opponent" if isinstance(own, Mapping) and own.get("side") == "self" else "self")
    if not _owner(own) or not _owner(opponent) or own != active.get(own["side"]):
        return _result("rejected", "runtime_fixed_two_hit_active_identity_unavailable", base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {
        **base, "action_id": action.get("action_id"), "attacker": deepcopy(dict(own)),
        "target": deepcopy(dict(opponent)), "move_metadata_authority": deepcopy(metadata_authority),
        "provenance": "runtime_d0_canonical_fixed_two_hit_execution_authority_v1",
    }
    if metadata_authority.get("status") != "resolved":
        return _result(metadata_authority.get("status", "rejected"), metadata_authority.get("reason", "fixed_two_hit_move_metadata_unavailable"), common)
    metadata = metadata_authority.get("metadata")
    classification = _classification(metadata, action.get("identity"))
    if classification.get("status") != "resolved":
        return _result(classification["status"], classification["reason"], {**common, "classification": classification})
    critical = build_runtime_d0_strict_critical_hit_probability_assessment(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=own, target=opponent, move_metadata=metadata,
    )
    if critical.get("status") != "resolved":
        return _result(critical.get("status", "rejected"), critical.get("reason", "fixed_two_hit_critical_authority_unavailable"), {**common, "classification": classification, "critical_hit_authority": deepcopy(critical)})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "move_id": metadata["move_id"], "hit_count": 2,
        "accuracy_execution": {
            "status": "resolved", "semantics": "action_level_once_before_hit_sequence",
            "accuracy": "always_hit" if metadata.get("always_hit") is True else metadata["accuracy"],
        },
        "per_hit_critical_execution": {
            "status": "resolved", "semantics": "independent_canonical_critical_roll_per_hit",
            "hit_count": 2,
            "per_hit_critical_probability": deepcopy(critical["critical_probability"]),
            "critical_hit_authority": deepcopy(critical),
        },
        "execution_exclusions": {
            "aggregate_total_damage": "forbidden", "variable_hit_count": "unsupported",
            "multiaccuracy": "unsupported", "escalating_power": "unsupported",
            "per_hit_secondary": "unsupported", "drain_or_recoil": "unsupported",
            "contact_or_item_consumption": "requires_separate_exact_owner",
            "substitute_or_replacement": "requires_separate_exact_owner",
        },
    }


def _classification(metadata: Any, expected_move_id: Any) -> dict[str, Any]:
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != expected_move_id or not isinstance(expected_move_id, str) or not expected_move_id:
        return {"status": "rejected", "reason": "fixed_two_hit_metadata_action_identity_mismatch"}
    minimum, maximum = metadata.get("min_hits"), metadata.get("max_hits")
    if minimum is None or maximum is None:
        return {"status": "incomplete", "reason": "fixed_two_hit_count_metadata_missing"}
    if not _int(minimum) or not _int(maximum):
        return {"status": "incomplete", "reason": "fixed_two_hit_count_metadata_invalid"}
    if minimum != maximum:
        return {"status": "unsupported", "reason": "variable_multi_hit_move"}
    if minimum != 2:
        return {"status": "unsupported", "reason": "multi_hit_family_not_fixed_two_hit"}
    if metadata.get("move_id") not in _SUPPORTED_FIXED_TWO_HIT_MOVES:
        return {"status": "unsupported", "reason": "fixed_two_hit_move_not_in_supported_execution_catalog"}
    if metadata.get("category") not in {"physical", "special"} or not _int(metadata.get("power")) or not isinstance(metadata.get("type"), str) or not metadata["type"]:
        return {"status": "incomplete", "reason": "fixed_two_hit_normal_formula_metadata_missing"}
    if metadata.get("always_hit") is not True and (not _int(metadata.get("accuracy")) or not 1 <= metadata["accuracy"] <= 100):
        return {"status": "incomplete", "reason": "fixed_two_hit_action_accuracy_missing"}
    if metadata.get("drain") not in {None, 0} or metadata.get("recoil") not in {None, 0} or metadata.get("self_ko") not in {None, False}:
        return {"status": "unsupported", "reason": "fixed_two_hit_drain_recoil_or_self_faint_unsupported"}
    if not _neutral_secondary_metadata(metadata):
        return {"status": "unsupported", "reason": "fixed_two_hit_per_hit_secondary_unsupported"}
    return {"status": "resolved", "move_id": metadata["move_id"], "hit_count": 2, "damage_model": "ordinary_normal_formula_per_hit"}


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(value.get("decision_owner")):
        return None
    return {
        "session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"],
        "source_branch_fingerprint": value["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(value["decision_owner"])),
    }


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and _int(value.get("slot_index")) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _neutral_secondary_metadata(metadata: Mapping[str, Any]) -> bool:
    """Accept only normalized absence, never truth-test an arbitrary payload."""
    chance, changes, ailment = metadata.get("effect_chance"), metadata.get("stat_changes"), metadata.get("ailment")
    return (
        chance in (None, 0)
        and (changes is None or changes == () or changes == [] or changes == {})
        and (ailment is None or ailment == "none" or ailment == [])
    )


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
