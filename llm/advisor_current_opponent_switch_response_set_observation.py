"""Production admission for an explicit current opponent switch-response set."""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence

from llm.advisor_lifecycle_confirmation import (
    LifecycleConfirmationBoundary,
    OPPONENT_SWITCH_RESPONSE_SET_SOURCE,
    USER_TRUST,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def admit_current_opponent_switch_response_set_observation(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    permission: str,
    targets: Sequence[Mapping[str, object]],
    turn_number: int | None,
) -> dict:
    """Apply one user-confirmed present-tense opponent switch snapshot.

    The reducer owns the resulting authority.  This admission seam only
    validates explicit confirmation against the already-known opponent roster;
    it never turns a panel entry, preview, or historic switch into a target.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("rejected", "invalid_session")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    state = snapshot.get("state")
    opponent, own = _active_owner(state, "opponent"), _active_owner(state, "self")
    if opponent is None or own is None:
        return _result("incomplete", "active_owner_unavailable")
    normalized = _normalize_explicit_switch_response_set(state, permission, targets)
    if normalized.get("status") != "resolved":
        return _result(normalized["status"], normalized["reason"])
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("incomplete", "trusted_turn_number_unavailable")
    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, {"self": own, "opponent": opponent}).confirm(
        event_kind="current_opponent_switch_response_set_observed",
        payload={"permission": normalized["permission"], "targets": normalized["targets"]},
        session_id=captured_session_id,
        source=OPPONENT_SWITCH_RESPONSE_SET_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side="opponent",
        slot_index=opponent["slot_index"],
        pokemon_id=opponent["pokemon_id"],
        observation_id=f"{captured_session_id}:opponent-switch-response-set-{sequence}",
        turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "lifecycle_confirmation_rejected"))
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
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot_index = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon = roster.get(slot_index) if isinstance(roster, Mapping) else None
    pokemon_id, session_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None, state.get("session_id")
    if not isinstance(slot_index, int) or isinstance(slot_index, bool) or slot_index < 0 or not isinstance(pokemon_id, str) or not pokemon_id or not isinstance(session_id, str) or not session_id:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot_index, "pokemon_id": pokemon_id}


def _normalize_explicit_switch_response_set(state: object, permission: object, targets: object) -> dict:
    if permission not in {"permitted", "blocked", "unknown"}:
        return {"status": "incomplete", "reason": "explicit_switch_permission_required"}
    side = state.get("opponent_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    active = side.get("active_slot_index") if isinstance(side, Mapping) else None
    if not isinstance(roster, Mapping) or not isinstance(active, int) or isinstance(active, bool):
        return {"status": "incomplete", "reason": "opponent_roster_unavailable"}
    expected = {(slot, pokemon.get("pokemon_id")) for slot, pokemon in roster.items() if isinstance(slot, int) and not isinstance(slot, bool) and slot != active and isinstance(pokemon, Mapping) and isinstance(pokemon.get("pokemon_id"), str) and pokemon.get("pokemon_id")}
    if not isinstance(targets, Sequence) or isinstance(targets, (str, bytes)):
        return {"status": "incomplete", "reason": "explicit_complete_target_set_required"}
    normalized, seen = [], set()
    for row in targets:
        slot = row.get("slot_index") if isinstance(row, Mapping) else None
        pokemon_id = row.get("pokemon_id") if isinstance(row, Mapping) else None
        availability = row.get("availability") if isinstance(row, Mapping) else None
        identity = (slot, pokemon_id)
        if identity not in expected or identity in seen or availability not in {"alive", "fainted", "unknown"}:
            return {"status": "rejected", "reason": "opponent_switch_target_identity_mismatch"}
        seen.add(identity)
        normalized.append({"slot_index": slot, "pokemon_id": pokemon_id, "availability": availability})
    if seen != expected:
        return {"status": "incomplete", "reason": "explicit_complete_target_set_required"}
    return {"status": "resolved", "permission": permission, "targets": normalized}


def _result(status: str, reason: str) -> dict:
    return {"status": status, "reason": reason, "observation": None, "runtime_fingerprint": None, "active_opponent": None}
