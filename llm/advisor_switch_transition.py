"""Detached manual-switch transition evidence; no legality, damage, or ranking."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_SIDE_SHARED_KEYS = ("field_state_context", "runtime_advice_state")


def project_authorized_switch_transition(
    *, turn_snapshot: Any, switch_candidate: Mapping[str, Any], switch_authorized: bool,
    opponent_action: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one already-authorized manual switch from frozen evidence.

    ``switch_authorized`` is an explicit upstream legality handoff.  It never
    promotes the Conservative switch candidate itself and keeps this adapter
    useful for future legal-action evaluation without changing candidate gates.
    """
    validated = _validate_switch_candidate(turn_snapshot, switch_candidate)
    if validated is None:
        return _unavailable("invalid_or_stale_switch_candidate")
    if switch_authorized is not True:
        return _unavailable("switch_not_authorized")

    serialized, current, context, target = validated
    post_snapshot = {
        "session_id": context["session_id"],
        "self_active": {
            "slot_index": target["slot_index"],
            "pokemon_id": target["pokemon_id"],
            # This is the only roster-owned battle fact currently projected by
            # the Conservative switch-candidate context.  It remains exact.
            "fainted": deepcopy(target["fainted"]),
        },
        "target_pokemon_state": {
            key: deepcopy(target[key])
            for key in ("current_hp", "max_hp", "condition", "known_item")
            if key in target
        },
        "target_roster_mechanics": _target_roster_mechanics(current, session=context["session_id"], target=target),
        # Side-owned hazards are frozen with the target roster record.  The
        # evaluator never looks back into the live reducer after this point.
        "switch_hazard_context": deepcopy(current.get("switch_hazard_context")),
        # Bound source-B/opposing-active authority is frozen beside the entry
        # hazards, never recovered from mutable active-A state later.
        "switch_entry_intimidate_authority": deepcopy(current.get("switch_entry_intimidate_authority")),
        "switch_entry_download_authority": deepcopy(current.get("switch_entry_download_authority")),
        "switch_entry_trace_authority": deepcopy(current.get("switch_entry_trace_authority")),
        "switch_entry_sturdy_authority": deepcopy(current.get("switch_entry_sturdy_authority")),
        "self_roster": deepcopy(context["self_pokemon"]),
        "side_shared_authority": {
            key: deepcopy(current[key]) for key in _SIDE_SHARED_KEYS if key in current
        },
        "stat_stage_transition_supportability": "unsupported_mechanic",
        "volatile_transition_supportability": "unsupported_mechanic",
        "entry_effects_supportability": "unsupported_mechanic",
    }
    result: dict[str, Any] = {
        "supportability": "complete",
        "self_action": {
            "action_kind": "switch",
            "candidate_id": switch_candidate["candidate_id"],
            "session_id": context["session_id"],
            "source_active_slot_index": context["self_active_slot_index"],
            "target_slot_index": target["slot_index"],
            "target_pokemon_id": target["pokemon_id"],
        },
        "switch_execution_status": "executed",
        "transition_supportability": "complete",
        "post_switch_snapshot": post_snapshot,
        "order_supportability": "not_applicable",
        "order_result": None,
        "first_actor": None,
        "move_priority_supportability": "not_applicable",
        "speed_order_supportability": "not_applicable",
        "target_redirection_supportability": "not_applicable",
        "redirected_opponent_action": None,
    }
    if opponent_action is None:
        return deepcopy(result)
    if not isinstance(opponent_action, Mapping):
        return _unavailable("invalid_opponent_action")
    if opponent_action.get("action_kind") == "switch":
        result.update({
            "supportability": "unsupported_mechanic",
            "order_supportability": "unsupported_mechanic",
            "target_redirection_supportability": "unsupported_mechanic",
            "unsupported_reason": "switch_vs_switch",
        })
        return deepcopy(result)
    if not _is_supported_opponent_move(opponent_action):
        return _unavailable("invalid_opponent_move")

    # Manual-switch action-class precedence is intentionally independent of
    # move priority, effective priority, Speed, Tailwind, paralysis, and TR.
    result.update({
        "order_supportability": "complete",
        "order_result": "self_switch_first",
        "first_actor": "self",
        "opponent_execution_status": "queued",
    })
    metadata = opponent_action.get("move_metadata")
    if isinstance(metadata, Mapping) and metadata.get("target") == "selected-pokemon":
        redirected = deepcopy(dict(opponent_action))
        redirected["redirected_target"] = {
            "side": "self", "slot_index": target["slot_index"], "pokemon_id": target["pokemon_id"],
        }
        result["target_redirection_supportability"] = "complete"
        result["redirected_opponent_action"] = redirected
    else:
        result["target_redirection_supportability"] = "unsupported_mechanic"
        result["target_redirection_reason"] = "unsupported_opponent_target_shape"
    return deepcopy(result)


def _validate_switch_candidate(turn_snapshot: Any, candidate: Mapping[str, Any]) -> tuple[dict[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None:
    if not isinstance(candidate, Mapping):
        return None
    try:
        serialized = turn_snapshot.to_dict()
    except (AttributeError, TypeError, ValueError):
        return None
    current = serialized.get("current_state")
    if not isinstance(current, Mapping):
        return None
    context = current.get("switch_candidate_context")
    if not isinstance(context, Mapping):
        return None
    session, active, entries = context.get("session_id"), context.get("self_active_slot_index"), context.get("self_pokemon")
    if not isinstance(session, str) or not isinstance(active, int) or isinstance(active, bool) or not isinstance(entries, list):
        return None
    slot, pokemon_id = candidate.get("target_slot_index"), candidate.get("target_pokemon_id")
    if candidate.get("action_kind") != "switch" or candidate.get("session_id") != session:
        return None
    if not isinstance(slot, int) or isinstance(slot, bool) or slot == active or not isinstance(pokemon_id, str) or not pokemon_id:
        return None
    if candidate.get("candidate_id") != f"self-switch:{session}:{slot}:{pokemon_id}":
        return None
    target = next((entry for entry in entries if isinstance(entry, Mapping) and entry.get("slot_index") == slot and entry.get("pokemon_id") == pokemon_id), None)
    if not isinstance(target, Mapping) or not isinstance(target.get("fainted"), Mapping):
        return None
    return serialized, current, context, target


def _is_supported_opponent_move(action: Mapping[str, Any]) -> bool:
    return (
        action.get("role") == "opponent_action"
        and action.get("acting_side") == "opponent"
        and action.get("target_side") == "self"
        and isinstance(action.get("move_id"), str)
        and bool(action.get("move_id"))
    )


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "supportability": "insufficient_context",
        "reason": reason,
        "switch_execution_status": "not_executed",
        "transition_supportability": "insufficient_context",
        "order_supportability": "insufficient_context",
        "order_result": None,
        "first_actor": None,
        "target_redirection_supportability": "insufficient_context",
        "redirected_opponent_action": None,
    }


def _target_roster_mechanics(current: Mapping[str, Any], *, session: str, target: Mapping[str, Any]) -> dict[str, Any] | None:
    context = current.get("self_roster_mechanics_context")
    entries = context.get("entries") if isinstance(context, Mapping) else None
    if not isinstance(entries, list) or context.get("session_id") != session or context.get("side") != "self":
        return None
    row = next((entry for entry in entries if isinstance(entry, Mapping) and entry.get("slot_index") == target.get("slot_index") and entry.get("pokemon_id") == target.get("pokemon_id") and entry.get("session_id") == session), None)
    return deepcopy(dict(row)) if isinstance(row, Mapping) else None
