"""Explicit user-observation capture for current-active switch permission."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from llm.advisor_reducer_state_model import execute_atomic_transition


_VALUES = frozenset({"permitted", "blocked", "unknown"})


def capture_switch_permission(*, store: Any, session_id: str, active_slot_index: int, active_pokemon_id: str, permission: str, observation_id: str, observation_sequence: int) -> dict[str, Any]:
    """Commit one manual fact through CAS; no rebinding or provider authority."""
    if permission not in _VALUES or not isinstance(session_id, str) or not session_id or not isinstance(active_slot_index, int) or isinstance(active_slot_index, bool) or not isinstance(active_pokemon_id, str) or not active_pokemon_id or not isinstance(observation_id, str) or not observation_id or not isinstance(observation_sequence, int) or isinstance(observation_sequence, bool) or observation_sequence < 1:
        return {"status": "invalid_capture", "state_snapshot": None}
    read = store.read_snapshot(session_id)
    if read.get("status") != "ready": return {"status": "stale_or_unavailable", "state_snapshot": None}
    state = read["state"]; side = state.get("self_side", {}); roster = side.get("pokemon", {}) if isinstance(side, dict) else {}
    active = roster.get(active_slot_index) if isinstance(roster, dict) else None
    if side.get("active_slot_index") != active_slot_index or not isinstance(active, dict) or active.get("pokemon_id") != active_pokemon_id:
        return {"status": "active_identity_mismatch", "state_snapshot": None}
    event = {"observation_id": observation_id, "observation_sequence": observation_sequence, "planned_effect": "clear_switch_permission" if permission == "unknown" else "set_switch_permission", "side": "self", "slot_index": active_slot_index, "pokemon_id": active_pokemon_id, "source": "user_confirmed_current_switch_permission", "trust": "user_confirmed_current"}
    if permission != "unknown": event["permission_status"] = permission
    plan = {"session_id": session_id, "status": "planned", "conflicts": [], "accepted_events": [event], "ordered_steps": [event]}
    execution = execute_atomic_transition(state, plan, expected_session_id=session_id, expected_base_fingerprint=read["state_fingerprint"])
    if execution.get("status") != "committed": return {"status": "capture_rejected", "state_snapshot": None}
    replaced = store.compare_and_replace(execution["committed_state"], expected_session_id=session_id, expected_base_fingerprint=read["state_fingerprint"])
    return {"status": "captured" if replaced.get("status") == "replaced" else replaced.get("status", "capture_rejected"), "state_snapshot": deepcopy(replaced.get("state_snapshot"))}
