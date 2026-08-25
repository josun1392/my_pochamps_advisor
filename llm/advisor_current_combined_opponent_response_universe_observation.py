"""Atomic production admission for one current combined opponent response view."""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence

from llm.advisor_current_opponent_response_set_observation import _normalize_explicit_response_set
from llm.advisor_current_opponent_switch_response_set_observation import _normalize_explicit_switch_response_set
from llm.advisor_lifecycle_confirmation import (
    LifecycleConfirmationBoundary,
    OPPONENT_RESPONSE_SET_SOURCE,
    OPPONENT_SWITCH_RESPONSE_SET_SOURCE,
    OPPONENT_SWITCH_TARGET_COMBAT_SOURCE,
    USER_TRUST,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def admit_current_combined_opponent_response_universe_observation(
    *, runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str, move_ids: list[str],
    move_usability: Mapping[str, Mapping[str, object]], permission: str,
    targets: Sequence[Mapping[str, object]], turn_number: int | None,
    target_combat_facts: Sequence[Mapping[str, object]] = (),
    switch_hazard_context: Mapping[str, object] | None = None,
) -> dict:
    """Validate, admit, and apply both explicit response facts as one batch."""
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("rejected", "invalid_session")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    state = snapshot.get("state")
    own, opponent = _active_owner(state, "self"), _active_owner(state, "opponent")
    if own is None or opponent is None:
        return _result("incomplete", "active_owner_unavailable")
    moves = _normalize_explicit_response_set(move_ids, move_usability)
    switches = _normalize_explicit_switch_response_set(state, permission, targets)
    if moves.get("status") != "resolved":
        return _result("incomplete", moves["reason"])
    if switches.get("status") != "resolved":
        return _result(switches.get("status", "incomplete"), switches["reason"])
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("incomplete", "trusted_turn_number_unavailable")
    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    combat_by_identity = {(row.get("slot_index"), row.get("pokemon_id")): row for row in target_combat_facts if isinstance(row, Mapping)}
    target_owners = [{"session_id": captured_session_id, "side": "opponent", "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"]} for row in switches["targets"] if row.get("availability") == "alive" and (row["slot_index"], row["pokemon_id"]) in combat_by_identity]
    boundary = LifecycleConfirmationBoundary(captured_session_id, {"self": own, "opponent": opponent, "opponent_targets": target_owners})
    move_confirmation = boundary.confirm(
        event_kind="current_opponent_response_set_observed",
        payload={"move_ids": moves["move_ids"], "move_usability": moves["move_usability"]},
        session_id=captured_session_id, source=OPPONENT_RESPONSE_SET_SOURCE,
        trust=USER_TRUST, confirmed=True, side="opponent",
        slot_index=opponent["slot_index"], pokemon_id=opponent["pokemon_id"],
        observation_id=f"{captured_session_id}:combined-opponent-moves-{sequence}", turn_number=turn_number,
    )
    switch_confirmation = boundary.confirm(
        event_kind="current_opponent_switch_response_set_observed",
        payload={"permission": switches["permission"], "targets": switches["targets"]},
        session_id=captured_session_id, source=OPPONENT_SWITCH_RESPONSE_SET_SOURCE,
        trust=USER_TRUST, confirmed=True, side="opponent",
        slot_index=opponent["slot_index"], pokemon_id=opponent["pokemon_id"],
        observation_id=f"{captured_session_id}:combined-opponent-switches-{sequence}", turn_number=turn_number,
    )
    if move_confirmation.get("status") != "confirmed" or switch_confirmation.get("status") != "confirmed":
        return _result("rejected", "combined_lifecycle_confirmation_rejected")
    confirmations = [move_confirmation, switch_confirmation]
    for target in target_owners:
        facts = combat_by_identity[(target["slot_index"], target["pokemon_id"])]
        payload = {key: facts.get(key) for key in ("current_hp", "max_hp", "fainted", "types", "final_stats", "stages", "condition", "item", "ability")}
        confirmation = boundary.confirm(event_kind="current_opponent_switch_target_combat_observed", payload=payload, session_id=captured_session_id, source=OPPONENT_SWITCH_TARGET_COMBAT_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=target["slot_index"], pokemon_id=target["pokemon_id"], observation_id=f"{captured_session_id}:combined-opponent-switch-target-{target['slot_index']}-{sequence}", turn_number=turn_number)
        if confirmation.get("status") != "confirmed":
            return _result("incomplete", "switch_target_combat_confirmation_invalid")
        confirmations.append(confirmation)
    if switch_hazard_context is not None:
        hazard = boundary.confirm(event_kind="switch_hazards_observed", payload=dict(switch_hazard_context), session_id=captured_session_id, source="ui_switch_hazard_state_confirmation", trust=USER_TRUST, confirmed=True, side="opponent", observation_id=f"{captured_session_id}:combined-opponent-switch-hazards-{sequence}", turn_number=turn_number)
        if hazard.get("status") != "confirmed":
            return _result("incomplete", "switch_hazard_confirmation_invalid")
        confirmations.append(hazard)
    for confirmation in confirmations:
        confirmation["observation"]["observation_sequence"] = sequence
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "combined_observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "combined_reducer_application_rejected")
    return {
        "status": "resolved", "reason": None, "shared_observation_sequence": sequence,
        "runtime_fingerprint": snapshot.get("state_fingerprint"), "active_opponent": deepcopy(opponent),
        "move_observation": deepcopy(move_confirmation["observation"]),
        "switch_observation": deepcopy(switch_confirmation["observation"]),
        "target_combat_observations": tuple(deepcopy(row["observation"]) for row in confirmations[2:]),
    }


def _active_owner(state: object, side: str) -> dict | None:
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon = roster.get(slot) if isinstance(roster, Mapping) else None
    session_id = state.get("session_id") if isinstance(state, Mapping) else None
    pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id or not isinstance(session_id, str) or not session_id:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}


def _result(status: str, reason: str) -> dict:
    return {"status": status, "reason": reason, "shared_observation_sequence": None,
            "runtime_fingerprint": None, "active_opponent": None,
            "move_observation": None, "switch_observation": None}
