"""Versioned user observations of a decision boundary; no native truth owner."""
from copy import deepcopy

SCHEMA = "battle-decision-phase-v1"
KIND = "battle_decision_phase_observed"
SOURCE = "user_confirmed_battle_decision_phase"
KEY = "battle_decision_phase_context"


def valid_payload(payload):
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "phase", "requesting_sides", "participants"}:
        return False
    sides, participants = payload.get("requesting_sides"), payload.get("participants")
    return (payload.get("schema_version") == SCHEMA and isinstance(payload.get("phase"), str) and payload.get("phase") in
        {"move_selection", "faint_replacement", "pivot_replacement"} and
        isinstance(sides, list) and 1 <= len(sides) <= 2 and all(isinstance(s, str) and s in {"self", "opponent"} for s in sides) and
        len(set(sides)) == len(sides) and (payload["phase"] != "move_selection" or set(sides) == {"self", "opponent"}) and
        isinstance(participants, dict) and set(participants) == {"self", "opponent"} and all(
            isinstance(p, dict) and set(p) == {"slot_index", "pokemon_id"} and type(p.get("slot_index")) is int and
            p["slot_index"] >= 0 and isinstance(p.get("pokemon_id"), str) and p["pokemon_id"] for p in participants.values()))


def valid_context(state, value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "phase", "requesting_sides", "participants", "session_id", "turn_number", "provenance"}:
        return False
    payload = {k: value[k] for k in ("schema_version", "phase", "requesting_sides", "participants")}
    provenance = value.get("provenance")
    if not valid_payload(payload) or value.get("session_id") != state.get("session_id") or type(value.get("turn_number")) is not int or value["turn_number"] < 1:
        return False
    if not isinstance(provenance, dict) or set(provenance) != {"event_kind", "source", "trust", "source_observation_id", "source_sequence"}:
        return False
    if (provenance.get("event_kind") != KIND or provenance.get("source") != SOURCE or
            provenance.get("trust") != "user_confirmed_observation" or
            not isinstance(provenance.get("source_observation_id"), str) or not provenance["source_observation_id"] or
            type(provenance.get("source_sequence")) is not int or provenance["source_sequence"] < 1):
        return False
    # Historical participants remain valid after a switch. Freshness is checked
    # separately at the native boundary, so stale records cannot break replay.
    for side, participant in value["participants"].items():
        roster = state.get(f"{side}_side", {}).get("pokemon", {})
        pokemon = roster.get(participant["slot_index"], roster.get(str(participant["slot_index"])))
        if not isinstance(pokemon, dict) or pokemon.get("pokemon_id") != participant["pokemon_id"]: return False
    return True


def project_phase(state, event):
    payload = event.get("payload", {})
    candidate = {**deepcopy(payload), "session_id": state["session_id"], "turn_number": event.get("turn_number"),
        "provenance": {"event_kind": event.get("event_kind"), "source": event.get("source"), "trust": event.get("trust"),
            "source_observation_id": event.get("observation_id"), "source_sequence": event.get("observation_sequence")}}
    if not valid_context(state, candidate): return "invalid_battle_decision_phase"
    prior = state.get(KEY)
    if prior and candidate["turn_number"] < prior["turn_number"]: return "stale_battle_decision_phase_turn"
    for side, participant in candidate["participants"].items():
        if state[f"{side}_side"]["active_slot_index"] != participant["slot_index"]: return "battle_decision_phase_active_owner_mismatch"
    state[KEY] = candidate
    return None


def admit_battle_decision_phase_observation(*, runtime_session_manager, captured_session_id, phase, requesting_sides, turn_number):
    """Commit an explicitly confirmed human phase through the existing replay owner.

    This API must never be called with a predicted phase or from simulation.
    It creates no status counter or pending action queue.
    """
    from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, USER_TRUST
    from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return {"status": "rejected", "reason": "invalid_runtime_manager"}
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready": return {"status": "rejected", "reason": "stale_or_unavailable_session"}
    state = snapshot["state"]
    participants = {}
    for side in ("self", "opponent"):
        container = state[f"{side}_side"]
        slot = container["active_slot_index"]
        pokemon = container["pokemon"].get(slot, container["pokemon"].get(str(slot)))
        if type(slot) is not int or not isinstance(pokemon, dict): return {"status": "rejected", "reason": "phase_active_owner_unavailable"}
        participants[side] = {"slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}
    payload = {"schema_version": SCHEMA, "phase": phase, "requesting_sides": deepcopy(requesting_sides), "participants": participants}
    if not valid_payload(payload) or type(turn_number) is not int or turn_number < 1:
        return {"status": "rejected", "reason": "invalid_phase_observation"}
    prior = state.get(KEY)
    if prior and prior["provenance"]["source_sequence"] == state.get("last_applied_observation_sequence") and all(prior[k] == v for k, v in payload.items()) and prior["turn_number"] == turn_number:
        return {"status": "resolved", "idempotent": True, "runtime_snapshot": snapshot}
    collection = runtime_session_manager.read_collection_snapshot()
    turns = [e.get("turn_number") for e in collection.get("ordered_observations", [])]
    turns.extend(e.get("turn_number") for e in runtime_session_manager.read_applied_ledger().values())
    if turn_number < max((t for t in turns if type(t) is int), default=1): return {"status": "rejected", "reason": "stale_phase_observation_turn"}
    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return {"status": "rejected", "reason": "phase_sequence_binding_mismatch"}
    sequence = allocated["observation_sequence"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, {}).confirm(event_kind=KIND, payload=payload,
        session_id=captured_session_id, source=SOURCE, trust=USER_TRUST, confirmed=True,
        observation_id=f"{captured_session_id}:decision-phase:{sequence}", turn_number=turn_number)
    if confirmation.get("status") != "confirmed": return {"status": "rejected", "reason": "phase_confirmation_rejected"}
    confirmation["observation"]["observation_sequence"] = sequence
    preview = deepcopy(collection)
    preview["ordered_observations"].append(deepcopy(confirmation["observation"]))
    if runtime_session_manager.preview(captured_session_id, preview).get("status") != "preview_ready":
        return {"status": "rejected", "reason": "phase_preview_rejected"}
    admitted = runtime_session_manager.admit_confirmation(captured_session_id, confirmation)
    if admitted.get("status") not in {"added", "duplicate"}: return {"status": "rejected", "reason": "phase_admission_rejected"}
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}: return {"status": "rejected", "reason": "phase_application_rejected"}
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if committed.get("state", {}).get(KEY, {}).get("provenance", {}).get("source_sequence") != sequence:
        return {"status": "rejected", "reason": "phase_commit_verification_failed"}
    return {"status": "resolved", "idempotent": False, "runtime_snapshot": committed, "observation": deepcopy(confirmation["observation"])}
