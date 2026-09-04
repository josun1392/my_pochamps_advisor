"""Canonical detached Encore application, forced execution, and selectability."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "detached-encore-action-restriction-v1"
_BINDINGS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
_INELIGIBLE = frozenset({"encore", "struggle", "transform", "mimic", "sketch", "mirror-move", "metronome", "sleep-talk", "nature-power", "copycat", "me-first", "assist", "dynamax-cannon", "burning-bulwark", "combat-torque", "blazing-torque", "magical-torque", "noxious-torque", "wicked-torque"})


def materialize_detached_encore_application(*, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], accuracy_authority: Mapping[str, Any], last_used_move_authority: Mapping[str, Any], last_used_move_metadata_authority: Mapping[str, Any], last_move_pp_authority: Mapping[str, Any], current_encore_authority: Mapping[str, Any], target_side_ability_authority: Mapping[str, Any], protection_authority: Mapping[str, Any], reflection_authority: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None: return _result("rejected", "encore_application_binding_invalid", {})
    for authority, label in ((accuracy_authority, "accuracy"), (target_side_ability_authority, "target_side_ability"), (protection_authority, "protection"), (reflection_authority, "reflection")):
        bad = _bound(authority, base, label, actor, target)
        if bad: return _result(*bad, base)
    if accuracy_authority.get("outcome") == "missed": return _outcome(base, "missed", "encore_missed", accuracy_authority)
    if accuracy_authority.get("outcome") != "hit": return _result("rejected", "encore_accuracy_outcome_invalid", base)
    if protection_authority.get("outcome") == "blocked": return _outcome(base, "blocked", "encore_blocked_by_protection", protection_authority)
    if protection_authority.get("outcome") != "not_applicable": return _result("rejected", "encore_protection_outcome_invalid", base)
    if reflection_authority.get("outcome") == "reflected": return _result("incomplete", "encore_reflection_execution_unsupported", base)
    if reflection_authority.get("outcome") != "not_applicable": return _result("rejected", "encore_reflection_outcome_invalid", base)
    if target_side_ability_authority.get("ability") == "aroma-veil": return _outcome(base, "failed", "encore_target_protected_by_aroma_veil", target_side_ability_authority)
    if not _current_encore(current_encore_authority, base, target): return _result("incomplete", "current_encore_authority_missing", base)
    if current_encore_authority.get("state") == "active": return _outcome(base, "failed", "encore_target_already_encored", current_encore_authority)
    if current_encore_authority.get("state") != "not_active": return _result("rejected", "current_encore_state_invalid", base)
    if not _bound_owner(last_used_move_authority, base, target): return _result("incomplete", "last_executed_move_authority_missing", base)
    move_id = last_used_move_authority.get("move_id")
    if not isinstance(move_id, str) or not move_id: return _result("rejected", "last_executed_move_identity_invalid", base)
    meta = last_used_move_metadata_authority.get("metadata") if isinstance(last_used_move_metadata_authority, Mapping) else None
    if not _bound_owner(last_used_move_metadata_authority, base, target) or not isinstance(meta, Mapping) or meta.get("move_id") != move_id or not isinstance(meta.get("priority"), int) or isinstance(meta.get("priority"), bool): return _result("incomplete", "last_executed_move_metadata_missing", base)
    if meta.get("encore_eligible") is False or move_id in _INELIGIBLE: return _outcome(base, "failed", "encore_locked_move_ineligible", last_used_move_metadata_authority, locked_move_id=move_id)
    if not _bound_owner(last_move_pp_authority, base, target) or last_move_pp_authority.get("move_id") != move_id: return _result("incomplete", "encore_locked_move_pp_authority_missing", base)
    if last_move_pp_authority.get("usable") is False: return _outcome(base, "failed", "encore_locked_move_no_pp", last_move_pp_authority, locked_move_id=move_id)
    if last_move_pp_authority.get("usable") is not True: return _result("rejected", "encore_locked_move_pp_invalid", base)
    return _outcome(base, "applicable", "encore_applicable", accuracy_authority, locked_move_id=move_id, locked_move_metadata=deepcopy(dict(meta)), last_used_execution_id=last_used_move_authority.get("execution_id"), remaining_target_turns=3)


def materialize_encore_forced_execution_action(*, selected_action: Mapping[str, Any], actor: Mapping[str, Any], encore_application: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(selected_action, Mapping) or not isinstance(actor, Mapping) or not isinstance(encore_application, Mapping): return _result("rejected", "encore_forced_execution_input_invalid", {})
    if encore_application.get("status") != "resolved" or encore_application.get("outcome") != "applicable" or encore_application.get("target") != dict(actor): return _result("rejected", "encore_forced_execution_binding_invalid", {})
    meta = encore_application.get("locked_move_metadata")
    if not isinstance(meta, Mapping) or meta.get("move_id") != encore_application.get("locked_move_id") or meta.get("category") not in {"physical", "special", "status"} or not isinstance(meta.get("priority"), int) or isinstance(meta.get("priority"), bool): return _result("incomplete", "encore_forced_move_metadata_missing", {})
    original = selected_action.get("action_id")
    if not isinstance(original, str) or not original: return _result("rejected", "encore_original_selected_action_missing", {})
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "actor": deepcopy(dict(actor)), "selected_action_id": original, "selected_move_id": selected_action.get("identity", selected_action.get("move_id")), "execution_action_id": f"encore_forced:{original}:{meta['move_id']}", "execution_move_id": meta["move_id"], "execution_move_metadata": deepcopy(dict(meta)), "execution_priority": meta["priority"], "replacement_reason": "encore", "encore_application": deepcopy(dict(encore_application)), "provenance": "selected_intent_preserved_encore_forced_execution_v1"}


def resolve_encore_move_selectability(*, encore_authority: Mapping[str, Any], owner: Mapping[str, Any], move_metadata_authority: Mapping[str, Any]) -> dict[str, Any]:
    meta = move_metadata_authority.get("metadata") if isinstance(move_metadata_authority, Mapping) else None
    if not isinstance(meta, Mapping) or not isinstance(meta.get("move_id"), str) or not meta["move_id"]: return _result("incomplete", "encore_move_metadata_missing", {})
    if not isinstance(encore_authority, Mapping) or encore_authority.get("status") != "resolved" or encore_authority.get("owner") != dict(owner): return _result("incomplete", "current_encore_authority_missing", {})
    if not all(isinstance(encore_authority.get(key), str) and encore_authority[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) or not isinstance(encore_authority.get("decision_owner"), Mapping): return _result("rejected", "current_encore_authority_binding_invalid", {})
    expected = {key: encore_authority[key] for key in _BINDINGS}; expected["active_attacker"] = dict(owner)
    if not isinstance(move_metadata_authority, Mapping) or move_metadata_authority.get("status") != "resolved" or any(move_metadata_authority.get(key) != value for key, value in expected.items()): return _result("rejected", "encore_move_metadata_binding_mismatch", {})
    if encore_authority.get("state") not in {"active", "not_active"}: return _result("rejected", "current_encore_state_invalid", {})
    if encore_authority["state"] == "not_active": return {"status": "resolved", "schema_version": SCHEMA_VERSION, "owner": deepcopy(dict(owner)), "move_id": meta["move_id"], "selectability": "selectable", "reason": "encore_not_active"}
    locked = encore_authority.get("locked_move_id")
    if not isinstance(locked, str) or not locked: return _result("rejected", "encore_locked_move_identity_invalid", {})
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "owner": deepcopy(dict(owner)), "move_id": meta["move_id"], "selectability": "selectable" if meta["move_id"] == locked else "not_selectable", "reason": "encore_locked_move_permitted" if meta["move_id"] == locked else "encore_forces_other_move", "encore_authority": deepcopy(dict(encore_authority))}


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or d0.get("active_owners", {}).get(actor.get("side") if isinstance(actor, Mapping) else None) != dict(actor) or d0.get("active_owners", {}).get(target.get("side") if isinstance(target, Mapping) else None) != dict(target): return None
    meta = action.get("metadata_authority", action.get("move_metadata_authority")); metadata = meta.get("metadata") if isinstance(meta, Mapping) else None
    if not isinstance(metadata, Mapping) or any(metadata.get(key) != value for key, value in {"move_id": "encore", "category": "status", "type": "normal", "accuracy": 100, "priority": 0}.items()): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action.get("action_id"), "move_id": "encore"}


def _bound(value: Any, base: Mapping[str, Any], label: str, actor: Mapping[str, Any], target: Mapping[str, Any]) -> tuple[str, str] | None:
    if not isinstance(value, Mapping): return ("incomplete", f"encore_{label}_authority_missing")
    if value.get("status") != "resolved": return (value.get("status") if value.get("status") in {"incomplete", "rejected"} else "rejected", value.get("reason", f"encore_{label}_authority_unavailable"))
    if any(value.get(key) != base.get(key) for key in _BINDINGS) or value.get("actor") != dict(actor) or value.get("target") != dict(target) or value.get("action_id") != base["action_id"] or value.get("move_id") != "encore": return ("rejected", f"encore_{label}_authority_binding_mismatch")
    return None


def _bound_owner(value: Any, base: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "resolved" and value.get("owner") == dict(owner) and all(value.get(key) == base.get(key) for key in _BINDINGS)


def _current_encore(value: Any, base: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    return _bound_owner(value, base, owner) and value.get("state") in {"active", "not_active"}


def _outcome(base: Mapping[str, Any], outcome: str, reason: str, authority: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome, "reason": reason, **deepcopy(extra), "authority": deepcopy(dict(authority)), "provenance": "strict_detached_encore_application_v1"}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
