"""Production admission for one explicit user-confirmed Pokemon switch."""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, SWITCH_SOURCE, USER_TRUST
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def admit_pokemon_switch_observation(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    side: str,
    switch_in_slot_index: int,
    switch_in_pokemon_id: str,
    turn_number: int | None,
) -> dict:
    """Preview and apply one exact, explicitly confirmed active switch.

    The runtime snapshot is the sole owner of the outgoing identity and roster
    membership.  UI selection is deliberately not an input to this boundary.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("rejected", "invalid_session")
    if side not in {"self", "opponent"}:
        return _result("rejected", "invalid_side")
    if not isinstance(switch_in_slot_index, int) or isinstance(switch_in_slot_index, bool) or switch_in_slot_index < 0:
        return _result("rejected", "invalid_switch_in_slot")
    if not isinstance(switch_in_pokemon_id, str) or not switch_in_pokemon_id:
        return _result("rejected", "invalid_switch_in_identity")

    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    state = snapshot.get("state")
    outgoing, other = _active_owner(state, side), _active_owner(state, "opponent" if side == "self" else "self")
    if outgoing is None or other is None:
        return _result("incomplete", "active_owner_unavailable")
    incoming = _incoming_owner(state, side, switch_in_slot_index, switch_in_pokemon_id)
    if incoming is None:
        return _result("rejected", "switch_in_identity_mismatch")
    if incoming["slot_index"] == outgoing["slot_index"] and incoming["pokemon_id"] == outgoing["pokemon_id"]:
        return _result("rejected", "switch_in_matches_active_owner")
    if incoming["fainted"] is True:
        return _result("rejected", "switch_in_fainted")

    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    owners = {side: outgoing, ("opponent" if side == "self" else "self"): other}
    confirmation = LifecycleConfirmationBoundary(captured_session_id, owners).confirm(
        event_kind="pokemon_switch_observed",
        payload={
            "switch_out_slot_index": outgoing["slot_index"],
            "switch_out_pokemon_id": outgoing["pokemon_id"],
            "switch_in_slot_index": incoming["slot_index"],
            "switch_in_pokemon_id": incoming["pokemon_id"],
        },
        session_id=captured_session_id,
        source=SWITCH_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=side,
        slot_index=outgoing["slot_index"],
        pokemon_id=outgoing["pokemon_id"],
        observation_id=f"{captured_session_id}:pokemon-switch-{sequence}",
        turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "lifecycle_confirmation_rejected"))
    observation = confirmation["observation"]
    observation["observation_sequence"] = sequence
    preview_snapshot = _preview_snapshot(runtime_session_manager.read_collection_snapshot(), observation)
    if preview_snapshot is None:
        return _result("rejected", "invalid_collection_snapshot")
    preview = runtime_session_manager.preview(captured_session_id, preview_snapshot)
    if preview.get("status") != "preview_ready":
        return _result("rejected", "reducer_preview_rejected")
    admitted = runtime_session_manager.admit_confirmation(captured_session_id, confirmation)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "reducer_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    committed_owner = _active_owner(committed.get("state"), side) if committed.get("status") == "runtime_snapshot_ready" else None
    if committed_owner is None or (committed_owner["slot_index"], committed_owner["pokemon_id"]) != (incoming["slot_index"], incoming["pokemon_id"]):
        return _result("rejected", "committed_active_identity_mismatch")
    return {
        "status": "resolved",
        "reason": None,
        "observation": deepcopy(observation),
        "runtime_fingerprint": snapshot.get("state_fingerprint"),
        "outgoing_owner": deepcopy(outgoing),
        "incoming_owner": {key: value for key, value in incoming.items() if key != "fainted"},
        "preview": {"status": preview.get("status"), "applied_step_ids": deepcopy(preview.get("applied_observation_ids", []))},
    }


def _active_owner(state: object, side: str) -> dict | None:
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon = _roster_record(roster, slot)
    session_id = state.get("session_id") if isinstance(state, Mapping) else None
    pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id or not isinstance(session_id, str) or not session_id:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}


def _incoming_owner(state: object, side: str, slot: int, pokemon_id: str) -> dict | None:
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    pokemon = _roster_record(roster, slot)
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != pokemon_id:
        return None
    owner = _active_owner(state, side)
    if owner is None:
        return None
    return {"session_id": owner["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon_id, "fainted": pokemon.get("fainted")}


def _roster_record(roster: object, slot: object) -> Mapping | None:
    if not isinstance(roster, Mapping) or not isinstance(slot, int) or isinstance(slot, bool):
        return None
    value = roster.get(slot, roster.get(str(slot)))
    return value if isinstance(value, Mapping) else None


def _preview_snapshot(snapshot: object, observation: Mapping) -> dict | None:
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready" or not isinstance(snapshot.get("session_id"), str) or not isinstance(snapshot.get("ordered_observations"), list):
        return None
    rows = deepcopy(snapshot["ordered_observations"])
    rows.append(deepcopy(dict(observation)))
    rows.sort(key=lambda row: (row.get("observation_sequence"), row.get("observation_id")))
    return {**deepcopy(dict(snapshot)), "ordered_observations": rows}


def _result(status: str, reason: str) -> dict:
    return {"status": status, "reason": reason, "observation": None, "runtime_fingerprint": None, "outgoing_owner": None, "incoming_owner": None, "preview": None}
