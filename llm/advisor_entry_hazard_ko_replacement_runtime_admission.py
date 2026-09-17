"""Production continuation for a replacement required by switch-entry hazard KO.

The reducer has already committed the actual switch, hazard HP transition, and
faint before this boundary runs.  This owner does not choose a replacement and
does not invent a new switch lifecycle; it proves that the current active is
still the exact terminal result of that committed entry-hazard batch and then
reuses the ordinary explicit switch admission for the trainer-selected
replacement.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation


SOURCE = "runtime_entry_hazard_ko_replacement_v1"
_DERIVED_SOURCE = "runtime_switch_entry_mechanics_v1"
_DERIVED_TRUST = "mechanics_derived_runtime"


def admit_entry_hazard_ko_replacement(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    switch_in_slot_index: int,
    switch_in_pokemon_id: str,
    turn_number: int,
) -> dict[str, Any]:
    """Admit one explicit self-side replacement after an exact entry-hazard KO."""
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected", "runtime_snapshot_unavailable")
    boundary = freeze_entry_hazard_ko_replacement_boundary(
        runtime_snapshot=snapshot,
        collection_snapshot=runtime_session_manager.read_collection_snapshot(),
    )
    if boundary.get("status") != "resolved":
        return _result(boundary.get("status", "rejected"), boundary.get("reason", "replacement_boundary_unavailable"))

    replacement = admit_pokemon_switch_observation(
        runtime_session_manager=runtime_session_manager,
        captured_session_id=captured_session_id,
        side="self",
        switch_in_slot_index=switch_in_slot_index,
        switch_in_pokemon_id=switch_in_pokemon_id,
        turn_number=turn_number,
    )
    if replacement.get("status") != "resolved":
        return {
            **_result(replacement.get("status", "rejected"), replacement.get("reason", "replacement_switch_rejected")),
            "replacement_boundary": deepcopy(boundary),
        }
    return {
        **deepcopy(replacement),
        "replacement_boundary": deepcopy(boundary),
        "replacement_source_owner": deepcopy(boundary["fainted_owner"]),
        "replacement_provenance": SOURCE,
    }


def freeze_entry_hazard_ko_replacement_boundary(
    *, runtime_snapshot: Mapping[str, Any], collection_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the current active is the still-current result of one exact hazard-KO batch."""
    if not isinstance(runtime_snapshot, Mapping) or runtime_snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected", "runtime_snapshot_unavailable")
    state = runtime_snapshot.get("state")
    session = runtime_snapshot.get("session_id")
    if not isinstance(state, Mapping) or state.get("session_id") != session:
        return _result("rejected", "runtime_state_binding_mismatch")
    side = state.get("self_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    slot = side.get("active_slot_index") if isinstance(side, Mapping) else None
    pokemon = _roster_record(roster, slot)
    pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon_id, str) or not pokemon_id:
        return _result("incomplete", "active_owner_unavailable")
    owner = {"session_id": session, "side": "self", "slot_index": slot, "pokemon_id": pokemon_id}
    if pokemon.get("current_hp") != 0 or pokemon.get("fainted") is not True:
        return _result("rejected", "entry_hazard_ko_replacement_not_required")

    hp_provenance = pokemon.get("current_hp_provenance")
    faint_provenance = pokemon.get("fainted_provenance")
    if not _derived_provenance(hp_provenance) or not _derived_provenance(faint_provenance):
        return _result("rejected", "entry_hazard_ko_provenance_unavailable")
    last = state.get("last_applied_observation_sequence")
    if last != faint_provenance.get("source_sequence"):
        return _result("rejected", "stale_entry_hazard_ko_replacement_boundary")

    if not isinstance(collection_snapshot, Mapping) or collection_snapshot.get("status") != "ready" or collection_snapshot.get("session_id") != session:
        return _result("rejected", "collection_snapshot_unavailable")
    rows = collection_snapshot.get("ordered_observations")
    if not isinstance(rows, list):
        return _result("rejected", "collection_snapshot_unavailable")
    events = {
        row.get("observation_id"): row for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("observation_id"), str)
    }
    hp_event = events.get(hp_provenance.get("source_observation_id"))
    faint_event = events.get(faint_provenance.get("source_observation_id"))
    if not _derived_event(hp_event, "switch_entry_hp_transition_derived", owner):
        return _result("rejected", "entry_hazard_hp_source_invalid")
    if not _derived_event(faint_event, "switch_entry_faint_derived", owner):
        return _result("rejected", "entry_hazard_faint_source_invalid")
    hp_payload = hp_event.get("payload")
    faint_payload = faint_event.get("payload")
    if (
        hp_payload.get("mechanic") != "entry_hazards"
        or hp_payload.get("hp_after") != 0
        or faint_payload.get("mechanic") != "entry_hazards"
    ):
        return _result("rejected", "entry_hazard_ko_mechanic_mismatch")
    source_id = hp_payload.get("source_switch_observation_id")
    if not isinstance(source_id, str) or faint_payload.get("source_switch_observation_id") != source_id:
        return _result("rejected", "entry_hazard_ko_source_switch_mismatch")
    switch = events.get(source_id)
    if not _source_switch(switch, owner):
        return _result("rejected", "entry_hazard_ko_source_switch_invalid")
    source_seq = switch.get("observation_sequence")
    hp_seq = hp_event.get("observation_sequence")
    faint_seq = faint_event.get("observation_sequence")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (source_seq, hp_seq, faint_seq)) or not source_seq < hp_seq < faint_seq == last:
        return _result("rejected", "entry_hazard_ko_sequence_binding_invalid")
    return {
        "status": "resolved",
        "reason": None,
        "schema_version": "entry-hazard-ko-replacement-boundary-v1",
        "session_id": session,
        "source_runtime_fingerprint": runtime_snapshot.get("state_fingerprint"),
        "fainted_owner": owner,
        "source_switch_observation_id": source_id,
        "hp_transition_observation_id": hp_event["observation_id"],
        "faint_observation_id": faint_event["observation_id"],
        "terminal_sequence": faint_seq,
        "provenance": SOURCE,
    }


def _derived_provenance(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("source_observation_id"), str)
        and bool(value["source_observation_id"])
        and isinstance(value.get("source_sequence"), int)
        and not isinstance(value.get("source_sequence"), bool)
        and value["source_sequence"] >= 1
        and value.get("trust") == _DERIVED_TRUST
    )


def _derived_event(value: Any, kind: str, owner: Mapping[str, Any]) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("event_kind") == kind
        and value.get("session_id") == owner.get("session_id")
        and value.get("side") == owner.get("side")
        and value.get("slot_index") == owner.get("slot_index")
        and value.get("pokemon_id") == owner.get("pokemon_id")
        and value.get("source") == _DERIVED_SOURCE
        and value.get("trust") == _DERIVED_TRUST
        and value.get("scope") == "switch_entry"
        and isinstance(value.get("payload"), Mapping)
    )


def _source_switch(value: Any, owner: Mapping[str, Any]) -> bool:
    payload = value.get("payload") if isinstance(value, Mapping) else None
    return (
        isinstance(value, Mapping)
        and value.get("event_kind") == "pokemon_switch_observed"
        and value.get("session_id") == owner.get("session_id")
        and value.get("side") == "self"
        and value.get("trust") == "user_confirmed_observation"
        and isinstance(payload, Mapping)
        and payload.get("switch_in_slot_index") == owner.get("slot_index")
        and payload.get("switch_in_pokemon_id") == owner.get("pokemon_id")
    )


def _roster_record(roster: Any, slot: Any) -> Mapping[str, Any] | None:
    if not isinstance(roster, Mapping) or not isinstance(slot, int) or isinstance(slot, bool):
        return None
    value = roster.get(slot, roster.get(str(slot)))
    return value if isinstance(value, Mapping) else None


def _result(status: str, reason: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "replacement_boundary": None,
        "replacement_source_owner": None,
        "replacement_provenance": None,
    }
