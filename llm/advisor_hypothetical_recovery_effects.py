"""Detached exact self-recovery projection for the Turn Engine."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_battle_state_context import build_direct_healing_assessment


def project_self_recovery(*, branch_state: Mapping[str, Any], action: Mapping[str, Any], expected_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one canonical direct self-heal without mutating observations."""
    if not isinstance(branch_state, Mapping) or branch_state.get("schema_version") != "deterministic-transition-preview-v1":
        return _result("rejected", "invalid_branch_state")
    if not _same_owner(action.get("owner"), expected_owner) or expected_owner.get("side") != "self":
        return _result("rejected", "stale_or_mismatched_recovery_owner")
    active = branch_state.get("active")
    actor = active.get("self") if isinstance(active, Mapping) else None
    if not isinstance(actor, Mapping) or actor.get("fainted") is not False:
        return _result("incomplete", "recovery_actor_execution_state")
    if not _same_owner(actor, expected_owner):
        return _result("rejected", "stale_or_mismatched_recovery_branch_owner")
    move = action.get("move")
    if not isinstance(move, Mapping) or move.get("category") != "status":
        return _result("unsupported", "self_recovery_action_not_status")
    if move.get("target") != "user":
        return _result("unsupported", "self_recovery_target_unsupported")
    if move.get("accuracy") is not None:
        return _result("incomplete", "self_recovery_move_success_uncertain")
    if move.get("effect_category") != "heal":
        return _result("unsupported", "self_recovery_effect_metadata")
    if move.get("stat_changes") not in (None, (), []):
        return _result("unsupported", "self_recovery_secondary_effect")
    if move.get("ailment") not in (None, "none"):
        return _result("unsupported", "self_recovery_secondary_effect")
    current = branch_state.get("current_state")
    hp_context = current.get("current_hp_context") if isinstance(current, Mapping) else None
    entry = next((row for row in hp_context.get("current_hp", []) if isinstance(row, Mapping) and row.get("side") == "self"), None) if isinstance(hp_context, Mapping) else None
    if not _trusted_hp(entry):
        return _result("incomplete", "self_exact_hp")
    assessment = build_direct_healing_assessment(move, hp_context)
    if assessment is None:
        return _result("incomplete", "self_recovery_effect_metadata")
    if assessment.get("status") == "unavailable":
        status = "unsupported" if assessment.get("reason") in {"invalid_healing_metadata", "unsupported_direct_healing_rule"} else "incomplete"
        return _result(status, str(assessment.get("reason") or "self_recovery"))
    if assessment.get("status") not in {"resolved", "no_effect"}:
        return _result("incomplete", str(assessment.get("reason") or "self_recovery"))
    if not all(isinstance(assessment.get(key), int) and not isinstance(assessment.get(key), bool) for key in ("actual_healing", "current_hp", "maximum_hp", "resulting_hp")):
        return _result("incomplete", "self_recovery_exact_amount")
    return {
        "status": "resolved",
        "owner": deepcopy(dict(expected_owner)),
        "recovery_percent": move["healing"],
        "recovery": assessment["actual_healing"],
        "hp_before": assessment["current_hp"],
        "max_hp": assessment["maximum_hp"],
        "hp_after": assessment["resulting_hp"],
    }


def _trusted_hp(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "user_confirmed" and value.get("source") == "user_confirmed_current_hp" and value.get("confidence") == "known" and all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) for key in ("current_hp", "maximum_hp")) and 1 <= value["current_hp"] <= value["maximum_hp"]


def _same_owner(value: Any, expected: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and all(value.get(key) == expected.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id"))


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
