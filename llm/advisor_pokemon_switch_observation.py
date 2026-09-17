"""Production admission for one explicit user-confirmed Pokemon switch."""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, SWITCH_SOURCE, USER_TRUST
from llm.advisor_manual_switch_entry_consequences import derive_live_manual_switch_entry_consequences
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


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
    consequences = derive_live_manual_switch_entry_consequences(
        state=state, switch_observation=observation, turn_number=turn_number,
        allocate_sequence=runtime_session_manager.allocate_observation_sequence,
    )
    if consequences.get("status") != "resolved":
        return _result("incomplete", consequences.get("reason", "switch_entry_authority_incomplete"))
    confirmations = [confirmation, *consequences["confirmations"]]
    observations = [item["observation"] for item in confirmations]
    preview_snapshot = _preview_snapshot(runtime_session_manager.read_collection_snapshot(), observations)
    if preview_snapshot is None:
        return _result("rejected", "invalid_collection_snapshot")
    preview = runtime_session_manager.preview(captured_session_id, preview_snapshot)
    if preview.get("status") != "preview_ready":
        return _result("rejected", "reducer_preview_rejected")
    preflight = _preflight_projected_switch(preview, incoming=incoming, side=side, entry_effects=consequences.get("entry_effects"))
    if preflight.get("status") != "ready":
        return _result("rejected", preflight.get("reason", "projected_switch_preflight_rejected"))
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "reducer_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    committed_owner = _active_owner(committed.get("state"), side) if committed.get("status") == "runtime_snapshot_ready" else None
    entry_hazard_ko = preflight["entry_hazard_ko"]
    post_commit_verified = committed_owner is not None and committed_owner == preflight["incoming_owner"]
    strategy_d0 = None
    post_commit_reason = None
    if not entry_hazard_ko and committed.get("status") == "runtime_snapshot_ready" and post_commit_verified:
        strategy_d0 = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=committed_owner)
        if strategy_d0.get("status") != "resolved":
            strategy_d0, post_commit_reason = None, "committed_runtime_d0_unavailable"
    elif not entry_hazard_ko:
        post_commit_reason = "committed_runtime_verification_unavailable"
    result = {
        "status": "resolved",
        "reason": None,
        "observation": deepcopy(observation),
        "runtime_fingerprint": snapshot.get("state_fingerprint"),
        "outgoing_owner": deepcopy(outgoing),
        "incoming_owner": {key: value for key, value in incoming.items() if key != "fainted"},
        "preview": {"status": preview.get("status"), "applied_step_ids": deepcopy(preview.get("applied_observation_ids", []))},
        "derived_observations": deepcopy(observations[1:]),
        "runtime_snapshot": deepcopy(committed if committed.get("status") == "runtime_snapshot_ready" else preflight["runtime_snapshot"]),
        "strategy_d0": strategy_d0,
        "runtime_committed": True,
        "post_commit_verified": post_commit_verified,
        "post_commit_verification_failure": post_commit_reason,
    }
    if entry_hazard_ko:
        result["boundary"] = "replacement_required_after_entry_hazard_ko"
    return result


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


def _preview_snapshot(snapshot: object, observations: list[Mapping]) -> dict | None:
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready" or not isinstance(snapshot.get("session_id"), str) or not isinstance(snapshot.get("ordered_observations"), list):
        return None
    rows = deepcopy(snapshot["ordered_observations"])
    rows.extend(deepcopy(dict(observation)) for observation in observations)
    rows.sort(key=lambda row: (row.get("observation_sequence"), row.get("observation_id")))
    return {**deepcopy(dict(snapshot)), "ordered_observations": rows}


def _preflight_projected_switch(preview: Mapping, *, incoming: Mapping, side: str, entry_effects: object) -> dict:
    """Validate all ordinary post-commit requirements against the dry-run state."""
    projected = preview.get("projected_state") if isinstance(preview, Mapping) else None
    session_id = projected.get("session_id") if isinstance(projected, Mapping) else None
    owner = _active_owner(projected, side)
    expected = {key: incoming.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")}
    if not isinstance(projected, Mapping) or not isinstance(session_id, str) or owner != expected:
        return {"status": "rejected", "reason": "projected_active_identity_mismatch"}
    runtime_snapshot = {"status": "runtime_snapshot_ready", "session_id": session_id, "state": deepcopy(projected), "state_fingerprint": state_fingerprint(projected)}
    entry_hazard_ko = isinstance(entry_effects, Mapping) and entry_effects.get("hazard_ko") is True
    if entry_hazard_ko:
        pokemon = _roster_record(projected.get(f"{side}_side", {}).get("pokemon") if isinstance(projected.get(f"{side}_side"), Mapping) else None, owner["slot_index"])
        if not isinstance(pokemon, Mapping) or pokemon.get("current_hp") != 0 or pokemon.get("fainted") is not True:
            return {"status": "rejected", "reason": "projected_entry_hazard_ko_mismatch"}
        return {"status": "ready", "runtime_snapshot": runtime_snapshot, "incoming_owner": owner, "entry_hazard_ko": True, "strategy_d0": None}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=runtime_snapshot, decision_owner=owner)
    if d0.get("status") != "resolved":
        return {"status": "rejected", "reason": "projected_fresh_runtime_d0_unavailable"}
    return {"status": "ready", "runtime_snapshot": runtime_snapshot, "incoming_owner": owner, "entry_hazard_ko": False, "strategy_d0": d0}


def _result(status: str, reason: str) -> dict:
    return {"status": status, "reason": reason, "observation": None, "runtime_fingerprint": None, "outgoing_owner": None, "incoming_owner": None, "preview": None, "derived_observations": [], "runtime_snapshot": None, "strategy_d0": None}
