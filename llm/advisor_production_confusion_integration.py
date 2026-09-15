"""Atomic explicit production admission for current Champions confusion state."""
from copy import deepcopy

from llm.advisor_lifecycle_confirmation import CONFUSION_SOURCE, USER_TRUST, LifecycleConfirmationBoundary


def admit_current_confusion_state(*, runtime_session_manager, captured_session_id, side, state, turn_number, newly_established=False):
    """Write observed state and, only for a newly observed episode, progression."""
    if side not in {"self", "opponent"} or state not in {"confused", "none"} or not isinstance(newly_established, bool):
        return _result("rejected", "invalid_confusion_confirmation")
    if state != "confused" and newly_established:
        return _result("rejected", "cleared_confusion_cannot_establish_progression")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected", "runtime_snapshot_unavailable")
    current = snapshot["state"].get(f"{side}_side", {})
    slot = current.get("active_slot_index")
    pokemon = current.get("pokemon", {}).get(slot)
    if not isinstance(slot, int) or not isinstance(pokemon, dict) or not isinstance(pokemon.get("pokemon_id"), str) or pokemon.get("fainted") is True:
        return _result("rejected", "invalid_current_confusion_owner")
    owners = {}
    for owner_side in ("self", "opponent"):
        owner_state = snapshot["state"].get(f"{owner_side}_side", {})
        owner_slot = owner_state.get("active_slot_index")
        owner_pokemon = owner_state.get("pokemon", {}).get(owner_slot)
        if not isinstance(owner_slot, int) or not isinstance(owner_pokemon, dict):
            return _result("rejected", "invalid_runtime_active_owners")
        owners[owner_side] = {"session_id": captured_session_id, "side": owner_side, "slot_index": owner_slot, "pokemon_id": owner_pokemon.get("pokemon_id")}
    boundary = LifecycleConfirmationBoundary(captured_session_id, owners)
    sequence = runtime_session_manager.allocate_observation_sequence()["observation_sequence"]
    current_id = f"{captured_session_id}:confusion-state:{sequence}"
    confirmed = boundary.confirm(
        event_kind="current_confusion_state_observed", payload={"state": state},
        session_id=captured_session_id, source=CONFUSION_SOURCE, trust=USER_TRUST,
        confirmed=True, side=side, slot_index=slot, pokemon_id=pokemon["pokemon_id"],
        observation_id=current_id, turn_number=turn_number,
    )
    if confirmed.get("status") != "confirmed":
        return _result("rejected", "confusion_confirmation_rejected")
    confirmed["observation"]["observation_sequence"] = sequence
    confirmations = [confirmed]
    if newly_established:
        sequence = runtime_session_manager.allocate_observation_sequence()["observation_sequence"]
        progression = boundary.confirm(
            event_kind="champions_confusion_progression_observed",
            payload={"state": "confused", "origin_id": f"{current_id}:episode", "established_turn": turn_number, "prior_opportunities": 0, "duration": None},
            session_id=captured_session_id, source=CONFUSION_SOURCE, trust=USER_TRUST,
            confirmed=True, side=side, slot_index=slot, pokemon_id=pokemon["pokemon_id"],
            observation_id=f"{captured_session_id}:confusion-progression:{sequence}",
            related_observation_id=current_id, turn_number=turn_number,
        )
        if progression.get("status") != "confirmed":
            return _result("rejected", "confusion_progression_confirmation_rejected")
        progression["observation"]["observation_sequence"] = sequence
        confirmations.append(progression)
    collection = runtime_session_manager.read_collection_snapshot()
    rows = [*collection.get("ordered_observations", []), *(row["observation"] for row in confirmations)]
    rows.sort(key=lambda row: (row["observation_sequence"], row["observation_id"]))
    if runtime_session_manager.preview(captured_session_id, {**collection, "ordered_observations": rows}).get("status") != "preview_ready":
        return _result("rejected", "atomic_confusion_preview_rejected")
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "atomic_confusion_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "atomic_confusion_application_rejected")
    return {"status": "resolved", "observation_transaction": [deepcopy(row["observation"]) for row in confirmations], "newly_established": newly_established}


def _result(status, reason):
    return {"status": status, "reason": reason, "observation_transaction": []}
