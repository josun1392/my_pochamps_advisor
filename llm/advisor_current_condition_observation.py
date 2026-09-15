"""Authoritative admission for one explicit current major-condition fact."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_lifecycle_confirmation import (
    CURRENT_CONDITION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


_CONDITIONS = {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"}


def admit_current_condition_observation(*, runtime_session_manager, captured_session_id, side, condition, turn_number):
    """Preview, commit, and verify one user-confirmed active-owner condition.

    The runtime snapshot supplies both owner identities.  UI selection is never
    accepted as an owner authority, and local UI state is deliberately outside
    this function so callers cannot mirror a failed admission as success.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("rejected", "invalid_session")
    if side not in {"self", "opponent"} or condition not in _CONDITIONS:
        return _result("rejected", "invalid_current_condition")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("rejected", "invalid_turn_number")

    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected", "runtime_snapshot_unavailable")
    owners = _active_owners(snapshot.get("state"), captured_session_id)
    target = owners.get(side) if owners is not None else None
    if target is None:
        return _result("rejected", "invalid_current_condition_owner")

    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, owners).confirm(
        event_kind="current_condition_observed",
        payload={"condition": condition},
        session_id=captured_session_id,
        source=CURRENT_CONDITION_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=side,
        slot_index=target["slot_index"],
        pokemon_id=target["pokemon_id"],
        observation_id=f"{captured_session_id}:current-condition:{sequence}",
        turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "condition_confirmation_rejected"))
    observation = confirmation["observation"]
    observation["observation_sequence"] = sequence
    collection = runtime_session_manager.read_collection_snapshot()
    preview_rows = [*collection.get("ordered_observations", []), deepcopy(observation)]
    preview_rows.sort(key=lambda row: (row["observation_sequence"], row["observation_id"]))
    preview = runtime_session_manager.preview(captured_session_id, {**collection, "ordered_observations": preview_rows})
    if preview.get("status") != "preview_ready":
        return _result("rejected", "reducer_preview_rejected")
    admitted = runtime_session_manager.admit_confirmation(captured_session_id, confirmation)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "reducer_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    raw = _owner_record(committed.get("state"), target)
    if committed.get("status") != "runtime_snapshot_ready" or not isinstance(raw, Mapping):
        return _result("rejected", "committed_current_condition_owner_missing")
    committed_condition = raw.get("condition")
    provenance = raw.get("condition_provenance")
    expected = None if condition == "none" else condition
    if committed_condition != expected or not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_condition_observed" or provenance.get("condition") != condition:
        return _result("rejected", "committed_current_condition_mismatch")
    return {
        "status": "resolved",
        "reason": None,
        "owner": deepcopy(target),
        "condition": condition,
        "observation": deepcopy(observation),
        "runtime_fingerprint": snapshot.get("state_fingerprint"),
    }


def _active_owners(state, session_id):
    if not isinstance(state, Mapping) or state.get("session_id") != session_id:
        return None
    owners = {}
    for side in ("self", "opponent"):
        side_state = state.get(f"{side}_side")
        roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
        slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
        pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) and not isinstance(slot, bool) else None
        pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id or pokemon.get("fainted") is True:
            return None
        owners[side] = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}
    return owners


def _owner_record(state, owner):
    side_state = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    raw = roster.get(owner["slot_index"], roster.get(str(owner["slot_index"]))) if isinstance(roster, Mapping) else None
    return raw if isinstance(raw, Mapping) and raw.get("pokemon_id") == owner["pokemon_id"] else None


def _result(status, reason):
    return {"status": status, "reason": reason, "observation": None}
