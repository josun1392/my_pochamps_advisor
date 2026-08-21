"""Pure end-of-turn to next-turn-start lifecycle handoff for Turn Engine branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state


# These records justify an already-completed turn; they must never become
# executable authority for the following turn.
_TURN_SCOPED_CURRENT_STATE_KEYS = frozenset({
    "action_order",
    "action_order_evidence",
    "candidate_evidence",
    "move_success_evidence",
    "same_turn_event_context",
    "selected_action",
    "selected_actions",
})
_OWNERSHIP_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def handoff_end_of_turn_to_next_turn_start(*, end_of_turn_branch: Mapping[str, Any]) -> dict[str, Any]:
    """Create a detached state-only next-turn boundary from one resolved EOT branch.

    This deliberately performs no mechanics.  It carries persistent battle
    authority forward while excluding action/evidence records bound to the
    completed turn.
    """
    if not isinstance(end_of_turn_branch, Mapping):
        return _result("rejected", "invalid_end_of_turn_branch")
    if end_of_turn_branch.get("status") != "resolved" or end_of_turn_branch.get("boundary", {}).get("phase") != "end_of_turn":
        return _result("rejected", "resolved_end_of_turn_boundary_required")
    source = end_of_turn_branch.get("next_state")
    source_fp = end_of_turn_branch.get("resulting_branch_fingerprint")
    if not isinstance(source, Mapping) or not isinstance(source_fp, str) or fingerprint_transition_preview_state(source) != source_fp:
        return _result("rejected", "stale_or_invalid_end_of_turn_fingerprint")

    state = deepcopy(dict(source))
    owners = _owners(state)
    if owners is None:
        return _result("rejected", "invalid_end_of_turn_ownership")
    lifecycle_error = _validate_predicted_lifecycle(state, owners)
    if lifecycle_error is not None:
        return _result("rejected", lifecycle_error)

    excluded = _exclude_turn_scoped_authority(state)
    aqua_ring = state.get("aqua_ring_persistent_effect_context")
    if isinstance(aqua_ring, dict) and aqua_ring.get("schema_version") == "detached-aqua-ring-persistent-effect-v1":
        # The typed persistent effect remains with the same active owner, but
        # its authority now originates at the completed EOT branch.
        aqua_ring["source_branch_fingerprint"] = source_fp
    ingrain = state.get("ingrain_persistent_effect_context")
    if isinstance(ingrain, dict) and ingrain.get("schema_version") == "detached-ingrain-persistent-effect-v1":
        ingrain["source_branch_fingerprint"] = source_fp
    # This metadata is branch provenance, not battle authority.  Its presence
    # intentionally creates a new fingerprint for the lifecycle boundary.
    state["turn_engine_lifecycle"] = {
        "schema_version": "deterministic-next-turn-start-v1",
        "source_end_of_turn_fingerprint": source_fp,
        "provenance": "turn_engine_end_of_turn_handoff",
    }
    resulting_fp = fingerprint_transition_preview_state(state)
    if resulting_fp is None:
        return _result("rejected", "unserializable_next_turn_start_state")
    requires_replacement = [side for side, active in state["active"].items() if active["fainted"]]
    return {
        "status": "resolved",
        "source_end_of_turn_fingerprint": source_fp,
        "resulting_branch_fingerprint": resulting_fp,
        "next_state": state,
        "lifecycle_trace": [{
            "sequence": 1,
            "event": "end_of_turn_to_next_turn_start",
            "execution_status": "carried_forward",
            "persistent_state": "carried_forward_without_mechanics",
            "excluded_turn_scoped_current_state_keys": excluded,
            "requires_replacement_before_action": requires_replacement,
        }],
        "boundary": {"phase": "next_turn_start"},
        "limitations": [
            "state_handoff_only",
            "no_action_selection_or_execution",
            "no_end_of_turn_or_next_turn_mechanics",
            "no_reducer_or_runtime_writeback",
        ],
    }


def _owners(state: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    active = state.get("active")
    if not isinstance(active, Mapping):
        return None
    owners: dict[str, dict[str, Any]] = {}
    session_id: Any = None
    for side in ("self", "opponent"):
        row = active.get(side)
        if not isinstance(row, Mapping) or row.get("side") != side:
            return None
        if any(key not in row for key in _OWNERSHIP_KEYS):
            return None
        if not isinstance(row.get("slot_index"), int) or isinstance(row.get("slot_index"), bool):
            return None
        if not isinstance(row.get("current_hp"), int) or isinstance(row.get("current_hp"), bool) or not isinstance(row.get("max_hp"), int) or isinstance(row.get("max_hp"), bool):
            return None
        if row["max_hp"] <= 0 or not 0 <= row["current_hp"] <= row["max_hp"] or row.get("fainted") is not (row["current_hp"] == 0):
            return None
        if session_id is None:
            session_id = row["session_id"]
        elif row["session_id"] != session_id:
            return None
        owners[side] = {key: row[key] for key in _OWNERSHIP_KEYS}
    return owners


def _validate_predicted_lifecycle(state: Mapping[str, Any], owners: Mapping[str, Mapping[str, Any]]) -> str | None:
    condition = state.get("predicted_condition_context")
    lifecycle = state.get("predicted_toxic_lifecycle")
    if condition is not None:
        if not isinstance(condition, Mapping) or condition.get("condition_type") not in {"poison", "toxic"}:
            return "invalid_predicted_condition_overlay"
        owner = condition.get("owner")
        if not isinstance(owner, Mapping) or owner not in owners.values() or not isinstance(condition.get("branch_state_fingerprint"), str):
            return "stale_predicted_condition_overlay"
    if lifecycle is None:
        return None
    if not isinstance(condition, Mapping) or condition.get("condition_type") != "toxic" or not isinstance(lifecycle, Mapping):
        return "stale_or_mismatched_predicted_toxic_lifecycle"
    stage = lifecycle.get("current_stage")
    if lifecycle.get("owner") != condition.get("owner") or lifecycle.get("provenance") != "turn_engine_predicted_toxic_application" or isinstance(stage, bool) or not isinstance(stage, int) or not 1 <= stage <= 15:
        return "stale_or_mismatched_predicted_toxic_lifecycle"
    return None


def _exclude_turn_scoped_authority(state: dict[str, Any]) -> list[str]:
    excluded: list[str] = []
    current = state.get("current_state")
    if isinstance(current, dict):
        for key in sorted(_TURN_SCOPED_CURRENT_STATE_KEYS):
            if key in current:
                current.pop(key)
                excluded.append(key)
    # Prior executable action/evidence never crosses the lifecycle boundary,
    # even if a caller placed it at the branch top level.
    for key in ("action_order", "consequence_trace", "selected_actions", "direct_mechanics_evidence", "predicted_protection_context"):
        if key in state:
            state.pop(key)
            excluded.append(key)
    return excluded


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
