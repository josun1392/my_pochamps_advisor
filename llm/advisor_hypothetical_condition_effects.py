"""Detached move-poison applicability and condition overlays for Turn Engine branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_battle_state_context import (
    normalize_current_type_authority,
    normalize_user_confirmed_current_ability,
    normalize_user_confirmed_current_condition,
)

_POISON_AILMENTS = frozenset({"poison", "toxic"})


def project_move_poison_condition(*, branch_state: Mapping[str, Any], action: Mapping[str, Any], expected_owner: Mapping[str, Any], target_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one immediate poison-family condition without creating an observation.

    Only PokeAPI's no-accuracy-roll representation (``accuracy is None``) is
    deterministic here.  Numeric accuracy, including 100, remains unresolved.
    """
    if not isinstance(branch_state, Mapping) or branch_state.get("schema_version") != "deterministic-transition-preview-v1":
        return _result("rejected", "invalid_branch_state")
    if not _same_owner(action.get("owner"), expected_owner) or not _same_owner(_active(branch_state, expected_owner.get("side")), expected_owner):
        return _result("rejected", "stale_or_mismatched_poison_action_owner")
    if not _same_owner(_active(branch_state, target_owner.get("side")), target_owner) or expected_owner.get("side") == target_owner.get("side"):
        return _result("rejected", "stale_or_mismatched_poison_target_owner")
    move = action.get("move")
    if not isinstance(move, Mapping) or move.get("category") != "status" or move.get("target") != "selected-pokemon":
        return _result("unsupported", "move_poison_target_or_category")
    if move.get("accuracy") is not None:
        return _result("incomplete", "move_poison_success_uncertain")
    ailment = move.get("ailment")
    if ailment not in _POISON_AILMENTS or move.get("effect_category") != "ailment":
        return _result("unsupported", "move_poison_ailment_metadata")
    current = branch_state.get("current_state")
    if not isinstance(current, Mapping):
        return _result("rejected", "branch_current_state")
    condition = _condition(current, target_owner["side"])
    if condition is None:
        return _result("incomplete", f"{target_owner['side']}.condition")
    if condition != "none":
        return _result("unsupported", "target_existing_nonvolatile_condition")
    target_types = _types(current, target_owner["side"])
    if target_types is None:
        return _result("incomplete", f"{target_owner['side']}.current_type")
    target_ability = _ability(current, target_owner["side"])
    if target_ability is None or target_ability == "unknown":
        return _result("incomplete", f"{target_owner['side']}.ability")
    if target_ability == "immunity":
        return _result("resolved", "blocked_by_immunity", applicable=False, ailment=ailment, owner=deepcopy(dict(target_owner)))
    type_immune = bool({"poison", "steel"} & set(target_types))
    attacker_ability = _ability(current, expected_owner["side"])
    if type_immune and (attacker_ability is None or attacker_ability == "unknown"):
        return _result("incomplete", f"{expected_owner['side']}.ability")
    if type_immune and attacker_ability != "corrosion":
        return _result("resolved", "blocked_by_poison_type_immunity", applicable=False, ailment=ailment, owner=deepcopy(dict(target_owner)))
    return _result("resolved", "applicable", applicable=True, ailment=ailment, owner=deepcopy(dict(target_owner)))


def apply_predicted_condition(branch_state: Mapping[str, Any], effect: Mapping[str, Any], *, source_snapshot_fingerprint: str, branch_state_fingerprint: str) -> None:
    """Attach a branch-only overlay.  Reducer observations are never modified."""
    if not isinstance(branch_state, dict) or not isinstance(source_snapshot_fingerprint, str) or not isinstance(branch_state_fingerprint, str) or effect.get("status") != "resolved" or effect.get("applicable") is not True:
        raise ValueError("invalid_predicted_condition_effect")
    branch_state["predicted_condition_context"] = {
        "schema_version": "hypothetical-move-poison-condition-v1",
        "source_snapshot_fingerprint": source_snapshot_fingerprint,
        "branch_state_fingerprint": branch_state_fingerprint,
        "owner": deepcopy(dict(effect["owner"])),
        "condition_type": effect["ailment"],
        "provenance": "turn_engine_predicted_move_poison",
    }
    if effect["ailment"] == "toxic":
        branch_state["predicted_toxic_lifecycle"] = {
            "schema_version": "hypothetical-predictive-toxic-lifecycle-v1",
            "source_snapshot_fingerprint": source_snapshot_fingerprint,
            "branch_state_fingerprint": branch_state_fingerprint,
            "owner": deepcopy(dict(effect["owner"])),
            "current_stage": 1,
            "provenance": "turn_engine_predicted_toxic_application",
        }


def overlay_predicted_condition_for_direct_mechanics(current_state: Mapping[str, Any], predicted: Any) -> dict[str, Any] | None:
    """Create a private calculator view; it never writes an observed condition.

    The native direct evaluator accepts only its existing canonical condition
    shape.  This adapter is local to detached hypothetical evaluation; the
    branch overlay retains predictive provenance and is never returned as a
    reducer/user confirmation.
    """
    current = deepcopy(dict(current_state))
    if predicted is None:
        return current
    if not isinstance(predicted, Mapping) or predicted.get("schema_version") != "hypothetical-move-poison-condition-v1" or predicted.get("provenance") not in {"turn_engine_predicted_move_poison", "turn_engine_predicted_toxic_spikes"}:
        return None
    owner, ailment = predicted.get("owner"), predicted.get("condition_type")
    if not isinstance(owner, Mapping) or owner.get("side") not in {"self", "opponent"} or ailment not in _POISON_AILMENTS:
        return None
    context = current.get("condition_context")
    entries = context.get("current_conditions") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return None
    match = next((entry for entry in entries if isinstance(entry, dict) and entry.get("side") == owner["side"]), None)
    if match is None:
        return None
    # Private calculator normalization only; ``current_state`` remains observed authority.
    match.update(condition_type=ailment, status="user_confirmed", source="user_confirmed_current_condition", confidence="known")
    return current


def _condition(current: Mapping[str, Any], side: str) -> str | None:
    entries = _context_entry(current, "condition_context", "current_conditions", side)
    if entries is None:
        return None
    try:
        return normalize_user_confirmed_current_condition({key: value for key, value in entries.items() if key != "provenance"})["condition_type"]
    except ValueError:
        return None


def _types(current: Mapping[str, Any], side: str) -> list[str] | None:
    entry = _context_entry(current, "current_type_context", "current_types", side)
    if entry is None:
        return None
    try:
        normalized = normalize_current_type_authority({key: value for key, value in entry.items() if key != "provenance"})
    except ValueError:
        return None
    return normalized["types"] if normalized["state"] == "known" else None


def _ability(current: Mapping[str, Any], side: str) -> str | None:
    entry = _context_entry(current, "ability_context", "current_abilities", side)
    if entry is None:
        return None
    try:
        return normalize_user_confirmed_current_ability({key: value for key, value in entry.items() if key != "provenance"})["ability"]
    except ValueError:
        return None


def _context_entry(current: Mapping[str, Any], context_name: str, entries_name: str, side: str) -> Mapping[str, Any] | None:
    context = current.get(context_name)
    entries = context.get(entries_name) if isinstance(context, Mapping) else None
    matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == side] if isinstance(entries, list) else []
    return matches[0] if len(matches) == 1 else None


def _active(branch: Mapping[str, Any], side: Any) -> Any:
    active = branch.get("active")
    return active.get(side) if isinstance(active, Mapping) else None


def _same_owner(value: Any, expected: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(expected, Mapping) and all(value.get(key) == expected.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id"))


def _result(status: str, reason: str, **values: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, **values}
