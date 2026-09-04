"""Strict detached Leech Seed application authority.

This module decides whether a selected Leech Seed creates a seeded volatile;
the successful-action reducer remains the only lifecycle promotion writer.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "detached-leech-seed-application-v1"
_BINDING = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
_CANONICAL = {"move_id": "leech-seed", "category": "status", "type": "grass", "accuracy": 90, "priority": 0}


def materialize_detached_leech_seed_application(*, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], accuracy_authority: Mapping[str, Any], target_type_authority: Mapping[str, Any], current_seed_authority: Mapping[str, Any], protection_authority: Mapping[str, Any], reflection_authority: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None:
        return _result("rejected", "leech_seed_application_binding_invalid", {})
    for authority, label in ((accuracy_authority, "accuracy"), (target_type_authority, "target_type"), (current_seed_authority, "current_seed"), (protection_authority, "protection"), (reflection_authority, "reflection")):
        error = _bound(authority, base, label)
        if error is not None:
            return _result(*error, base)
    if protection_authority.get("outcome") == "blocked":
        return _outcome(base, "blocked", "leech_seed_blocked_by_protection", protection_authority)
    if protection_authority.get("outcome") != "not_applicable":
        return _result("rejected", "leech_seed_protection_outcome_invalid", base)
    if reflection_authority.get("outcome") == "reflected":
        return _result("incomplete", "leech_seed_reflection_execution_unsupported", base)
    if reflection_authority.get("outcome") != "not_applicable":
        return _result("rejected", "leech_seed_reflection_outcome_invalid", base)
    types = target_type_authority.get("types")
    if not isinstance(types, (list, tuple)) or not all(isinstance(value, str) and value for value in types):
        return _result("incomplete", "leech_seed_target_type_authority_missing", base)
    if current_seed_authority.get("owner") != dict(target) or current_seed_authority.get("state") not in {"active", "not_active"}:
        return _result("rejected", "leech_seed_current_state_invalid", base)
    if "grass" in types:
        return _outcome(base, "canonical_failure", "leech_seed_target_grass_immune", target_type_authority)
    if current_seed_authority["state"] == "active":
        return _outcome(base, "canonical_failure", "leech_seed_target_already_seeded", current_seed_authority)
    if accuracy_authority.get("outcome") == "missed":
        return _outcome(base, "missed", "leech_seed_missed", accuracy_authority)
    if accuracy_authority.get("outcome") != "hit":
        return _result("rejected", "leech_seed_accuracy_outcome_invalid", base)
    return _outcome(base, "applicable", "leech_seed_applicable", accuracy_authority)


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    meta = action.get("metadata_authority", action.get("move_metadata_authority")) if isinstance(action, Mapping) else None
    metadata = meta.get("metadata") if isinstance(meta, Mapping) else None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(actor, Mapping) or not isinstance(target, Mapping) or d0.get("active_owners", {}).get(actor.get("side")) != dict(actor) or d0.get("active_owners", {}).get(target.get("side")) != dict(target) or not isinstance(metadata, Mapping) or any(metadata.get(key) != value for key, value in _CANONICAL.items()):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action.get("action_id"), "move_id": "leech-seed"}


def _bound(value: Any, base: Mapping[str, Any], label: str) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return "incomplete", f"leech_seed_{label}_authority_missing"
    if value.get("status") != "resolved":
        return value.get("status") if value.get("status") in {"incomplete", "rejected"} else "rejected", value.get("reason", f"leech_seed_{label}_authority_unavailable")
    if any(value.get(key) != base[key] for key in _BINDING) or any(value.get(key) != base[key] for key in ("actor", "target", "action_id", "move_id")):
        return "rejected", f"leech_seed_{label}_authority_binding_mismatch"
    return None


def _outcome(base: Mapping[str, Any], outcome: str, reason: str, authority: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome, "reason": reason, "authority": deepcopy(dict(authority)), "provenance": "strict_detached_leech_seed_application_v1"}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
