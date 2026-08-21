"""Narrow, branch-owned authority for the Aqua Ring persistent effect."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _owners, _sync_hp
from llm.advisor_transition_preview import fingerprint_transition_preview_state

_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_PROVENANCE = "trusted_aqua_ring_persistent_effect_state"


def aqua_ring_state(state: Mapping[str, Any], side: str, owner: Mapping[str, Any]) -> str | None:
    """Read one exact owner's typed state; ``None`` is malformed/foreign."""
    context = state.get("aqua_ring_persistent_effect_context")
    if not isinstance(context, Mapping) or context.get("schema_version") != "detached-aqua-ring-persistent-effect-v1" or context.get("provenance") != _PROVENANCE or context.get("session_id") != owner.get("session_id") or not isinstance(context.get("source_branch_fingerprint"), str):
        return None
    rows = context.get("states")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("owner") == dict(owner)] if isinstance(rows, list) else []
    if len(matches) != 1 or matches[0].get("state") not in {"known_active", "known_inactive", "unknown"}:
        return None
    return matches[0]["state"]


def apply_owner_aqua_ring_end_of_turn(*, state: dict[str, Any], side: str, owner: Mapping[str, Any], source_branch_fingerprint: str) -> dict[str, Any]:
    owners = _owners(state)
    if owners is None or side not in owners or dict(owner) != owners[side] or fingerprint_transition_preview_state(state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_foreign_aqua_ring_owner")
    effect_state = aqua_ring_state(state, side, owner)
    if effect_state is None:
        return _result("rejected", "stale_or_invalid_aqua_ring_authority")
    if effect_state == "unknown":
        return _result("incomplete", "aqua_ring_persistent_effect_unknown")
    if effect_state == "known_inactive":
        return {"status": "resolved", "trace": None}
    active = state["active"][side]
    if active["fainted"]:
        return _result("rejected", "aqua_ring_fainted_owner")
    hp, maximum = active["current_hp"], active["max_hp"]
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1 or not 0 < hp <= maximum:
        return _result("incomplete", "aqua_ring_current_hp_authority")
    recovery, post = maximum // 16, min(maximum, hp + maximum // 16)
    active["current_hp"] = post
    _sync_hp(state, side, post, maximum)
    return {"status": "resolved", "trace": {"effect": "aqua_ring_recovery", "owner": deepcopy(dict(owner)), "persistent_effect": "aqua-ring", "persistent_effect_state": "known_active", "pre_hp": hp, "max_hp": maximum, "recovery": recovery, "post_hp": post, "execution_status": "executed" if post != hp else "prevented", "outcome": "recovered" if post != hp else "already_full_hp", "provenance": "detached_branch_aqua_ring_recovery_v1"}}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
