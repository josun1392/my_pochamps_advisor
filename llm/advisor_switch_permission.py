"""Canonical frozen authority for whether the current self active may switch."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "switch-permission-context-v1"
_KNOWN = frozenset({"permitted", "blocked"})


def unknown_switch_permission_context(*, session_id: str, active_slot_index: int, active_pokemon_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "side": "self",
        "active_slot_index": active_slot_index,
        "active_pokemon_id": active_pokemon_id,
        "status": "unknown",
        "supportability": "insufficient_context",
    }


def normalize_switch_permission_context(
    value: Any, *, session_id: str, active_slot_index: int, active_pokemon_id: str,
) -> dict[str, Any]:
    """Reject stale, forged, malformed, or untrusted permission assertions."""
    unknown = unknown_switch_permission_context(
        session_id=session_id, active_slot_index=active_slot_index, active_pokemon_id=active_pokemon_id,
    )
    if not isinstance(value, Mapping):
        return unknown
    common = {
        "schema_version": SCHEMA_VERSION, "session_id": session_id, "side": "self",
        "active_slot_index": active_slot_index, "active_pokemon_id": active_pokemon_id,
    }
    if any(value.get(key) != expected for key, expected in common.items()):
        return unknown
    if value.get("status") == "unknown" and value.get("supportability") == "insufficient_context" and set(value) == {*common, "status", "supportability"}:
        return unknown
    if value.get("status") in _KNOWN and value.get("supportability") == "complete" and value.get("source") == "user_confirmed_current_switch_permission" and value.get("trust") == "user_confirmed_current":
        allowed = {*common, "status", "supportability", "source", "trust", "block_reason"}
        if set(value) <= allowed and (value.get("status") != "blocked" or value.get("block_reason") in (None, "trapped", "switch_lock", "other_confirmed_block")):
            return deepcopy(dict(value))
    return unknown


def project_switch_permission_context(runtime_state: Mapping[str, Any]) -> dict[str, Any]:
    """Detach the source-active permission from state; legacy/missing is unknown."""
    session, side = runtime_state.get("session_id"), runtime_state.get("self_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    slot = side.get("active_slot_index") if isinstance(side, Mapping) else None
    active = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) else None
    pokemon_id = active.get("pokemon_id", active.get("name_en")) if isinstance(active, Mapping) else None
    if not isinstance(session, str) or not session or not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon_id, str) or not pokemon_id:
        raise ValueError("invalid_switch_permission_context")
    return normalize_switch_permission_context(
        side.get("switch_permission_context") if isinstance(side, Mapping) else None,
        session_id=session, active_slot_index=slot, active_pokemon_id=pokemon_id,
    )
