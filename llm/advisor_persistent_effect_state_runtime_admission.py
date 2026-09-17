"""Production admission for one explicitly observed current persistent effect."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, PERSISTENT_EFFECT_SOURCE, USER_TRUST
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0

_EVENTS = {
    "aqua_ring": "current_aqua_ring_state_observed",
    "ingrain": "current_ingrain_state_observed",
    "leech_seed": "current_leech_seed_state_observed",
}


def admit_current_persistent_effect_state(*, runtime_session_manager: BattleObservationRuntimeSessionManager,
                                          captured_session_id: str, family: str, side: str, slot_index: int,
                                          pokemon_id: str, persistent_state: str, turn_number: int,
                                          source_side: str | None = None, source_slot_index: int | None = None) -> dict[str, Any]:
    """Commit an explicit current-state observation; predictions never enter here."""
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if family not in _EVENTS or persistent_state not in {"active", "inactive"}:
        return _result("rejected", "invalid_persistent_effect_family_or_state")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    state = snapshot.get("state") if snapshot.get("status") == "runtime_snapshot_ready" else None
    owner = _active_owner(state, side)
    if owner is None or owner["slot_index"] != slot_index or owner["pokemon_id"] != pokemon_id:
        return _result("rejected", "persistent_effect_owner_not_current_active")
    payload = {"persistent_state": persistent_state}
    if family == "leech_seed" and persistent_state == "active":
        payload.update(source_side=source_side, source_slot_index=source_slot_index)
    if family != "leech_seed" and (source_side is not None or source_slot_index is not None):
        return _result("rejected", "persistent_effect_source_not_applicable")
    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    seq = allocated["observation_sequence"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, {side: owner}).confirm(
        event_kind=_EVENTS[family], payload=payload, session_id=captured_session_id,
        source=PERSISTENT_EFFECT_SOURCE, trust=USER_TRUST, confirmed=True,
        side=side, slot_index=slot_index, pokemon_id=pokemon_id,
        observation_id=f"{captured_session_id}:persistent-effect:{family}:{seq}", turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "persistent_effect_confirmation_rejected"))
    confirmation["observation"]["observation_sequence"] = seq
    preview_snapshot = _preview_snapshot(runtime_session_manager.read_collection_snapshot(), [confirmation["observation"]])
    preview = runtime_session_manager.preview(captured_session_id, preview_snapshot) if preview_snapshot else {}
    if preview.get("status") != "preview_ready":
        return _result("rejected", "persistent_effect_preview_rejected")
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, [confirmation])
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "persistent_effect_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "persistent_effect_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=owner) if committed.get("status") == "runtime_snapshot_ready" else {}
    return {"status": "resolved", "reason": None, "observation": deepcopy(confirmation["observation"]),
            "runtime_snapshot": deepcopy(committed), "strategy_d0": d0 if d0.get("status") == "resolved" else None,
            "runtime_committed": True}


def _active_owner(state: Any, side: str) -> dict[str, Any] | None:
    row = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster, slot = (row.get("pokemon"), row.get("active_slot_index")) if isinstance(row, Mapping) else (None, None)
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) else None
    if side not in {"self", "opponent"} or not isinstance(pokemon, Mapping) or not isinstance(state.get("session_id"), str) or not isinstance(pokemon.get("pokemon_id"), str):
        return None
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}


def _preview_snapshot(snapshot: Any, observations: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready":
        return None
    rows = deepcopy(snapshot.get("ordered_observations", [])); rows.extend(deepcopy(dict(item)) for item in observations)
    rows.sort(key=lambda item: (item.get("observation_sequence"), item.get("observation_id")))
    return {**deepcopy(dict(snapshot)), "ordered_observations": rows}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason, "observation": None, "runtime_snapshot": None, "strategy_d0": None, "runtime_committed": False}
