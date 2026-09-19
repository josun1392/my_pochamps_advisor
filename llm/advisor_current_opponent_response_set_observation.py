"""Production admission for one explicit current opponent response-set observation."""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence

from llm.advisor_lifecycle_confirmation import (
    LifecycleConfirmationBoundary,
    OPPONENT_RESPONSE_SET_SOURCE,
    USER_TRUST,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def admit_current_opponent_response_set_observation(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    move_ids: list[str],
    move_usability: Mapping[str, Mapping[str, object]],
    turn_number: int | None,
    move_pp_slots: Sequence[Mapping[str, object]] | None = None,
) -> dict:
    """Apply only a user-confirmed complete, current response snapshot.

    This is an admission seam, not a second opponent-knowledge model: the
    lifecycle confirmation and reducer remain the respective authority owners.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("rejected", "invalid_session")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    state = snapshot.get("state")
    opponent = _active_owner(state, "opponent")
    own = _active_owner(state, "self")
    if opponent is None or own is None:
        return _result("incomplete", "active_owner_unavailable")
    normalized = _normalize_explicit_response_set(move_ids, move_usability, move_pp_slots)
    if normalized.get("status") != "resolved":
        return _result("incomplete", normalized["reason"])
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("incomplete", "trusted_turn_number_unavailable")
    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    payload = {"move_ids": normalized["move_ids"], "move_usability": normalized["move_usability"]}
    if normalized["move_pp_slots"] is not None:
        payload["move_pp_slots"] = normalized["move_pp_slots"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, {"self": own, "opponent": opponent}).confirm(
        event_kind="current_opponent_response_set_observed",
        payload=payload,
        session_id=captured_session_id,
        source=OPPONENT_RESPONSE_SET_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side="opponent",
        slot_index=opponent["slot_index"],
        pokemon_id=opponent["pokemon_id"],
        observation_id=f"{captured_session_id}:opponent-response-set-{sequence}",
        turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "lifecycle_confirmation_rejected"))
    # The runtime session is the sole cross-observation sequence owner.  The
    # short-lived lifecycle validator intentionally has no session allocator.
    confirmation["observation"]["observation_sequence"] = sequence
    admitted = runtime_session_manager.admit_confirmation(captured_session_id, confirmation)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "reducer_application_rejected")
    return {
        "status": "resolved",
        "reason": None,
        "observation": deepcopy(confirmation["observation"]),
        "runtime_fingerprint": snapshot.get("state_fingerprint"),
        "active_opponent": deepcopy(opponent),
    }


def _active_owner(state: object, side: str) -> dict | None:
    if not isinstance(state, Mapping):
        return None
    side_state = state.get(f"{side}_side")
    if not isinstance(side_state, Mapping):
        return None
    slot_index = side_state.get("active_slot_index")
    pokemon = side_state.get("pokemon", {}).get(slot_index) if isinstance(side_state.get("pokemon"), Mapping) else None
    pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    session_id = state.get("session_id")
    if not isinstance(slot_index, int) or isinstance(slot_index, bool) or slot_index < 0 or not isinstance(pokemon_id, str) or not pokemon_id or not isinstance(session_id, str) or not session_id:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot_index, "pokemon_id": pokemon_id}


def _normalize_explicit_response_set(
    move_ids: object,
    move_usability: object,
    move_pp_slots: object = None,
) -> dict:
    if not isinstance(move_ids, list) or len(move_ids) != 4:
        return {"status": "incomplete", "reason": "exactly_four_explicit_moves_required"}
    moves = [value.strip().lower() for value in move_ids if isinstance(value, str)]
    if len(moves) != 4 or len(set(moves)) != 4 or any(not value or " " in value or "_" in value for value in moves):
        return {"status": "incomplete", "reason": "invalid_or_duplicate_explicit_move_ids"}
    if not isinstance(move_usability, Mapping) or set(move_usability) != set(moves):
        return {"status": "incomplete", "reason": "explicit_usability_required_for_every_move"}
    normalized = {}
    for move_id in moves:
        value = move_usability.get(move_id)
        status = value.get("status") if isinstance(value, Mapping) else None
        if status == "unknown":
            return {"status": "incomplete", "reason": "unknown_move_usability"}
        if status == "usable":
            normalized[move_id] = {"status": "known_usable", "reason": None}
        elif status == "unusable":
            reason = value.get("reason", "observed_unclassified") if isinstance(value, Mapping) else "observed_unclassified"
            if reason not in {"no_pp", "disabled", "choice_lock", "encore_restriction", "other_supported_restriction", "observed_unclassified"}:
                return {"status": "incomplete", "reason": "invalid_explicit_usability_reason"}
            normalized[move_id] = {"status": "known_unusable", "reason": reason}
        else:
            return {"status": "incomplete", "reason": "invalid_explicit_usability"}
    pp = _normalize_move_pp_slots(moves, normalized, move_pp_slots)
    if isinstance(pp, str):
        return {"status": "incomplete", "reason": pp}
    return {"status": "resolved", "move_ids": moves, "move_usability": normalized, "move_pp_slots": pp}


def _normalize_move_pp_slots(moves: list[str], usability: Mapping[str, Mapping[str, object]], value: object) -> list[dict] | str | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != len(moves):
        return "complete_ordered_move_pp_snapshot_required"
    rows: list[dict] = []
    seen_slots: set[int] = set()
    seen_moves: set[str] = set()
    for expected_slot, expected_move in enumerate(moves):
        row = value[expected_slot]
        if not isinstance(row, Mapping) or set(row) != {"slot_index", "move_id", "current_pp", "max_pp"}:
            return "invalid_move_pp_slot_shape"
        slot, move_id, current_pp, max_pp = row.get("slot_index"), row.get("move_id"), row.get("current_pp"), row.get("max_pp")
        if (
            not isinstance(slot, int) or isinstance(slot, bool) or slot != expected_slot
            or not isinstance(move_id, str) or move_id != expected_move
            or slot in seen_slots or move_id in seen_moves
            or not isinstance(current_pp, int) or isinstance(current_pp, bool) or current_pp < 0
            or not isinstance(max_pp, int) or isinstance(max_pp, bool) or max_pp <= 0
            or current_pp > max_pp
        ):
            return "invalid_or_reordered_move_pp_slot"
        usability_row = usability.get(move_id, {})
        if usability_row.get("status") == "known_usable" and current_pp == 0:
            return "move_pp_usability_contradiction"
        if usability_row.get("status") == "known_unusable" and usability_row.get("reason") == "no_pp" and current_pp > 0:
            return "move_pp_usability_contradiction"
        seen_slots.add(slot); seen_moves.add(move_id)
        rows.append({"slot_index": slot, "move_id": move_id, "current_pp": current_pp, "max_pp": max_pp})
    return rows


def _result(status: str, reason: str) -> dict:
    return {"status": status, "reason": reason, "observation": None, "runtime_fingerprint": None, "active_opponent": None}
