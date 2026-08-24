"""Bounded branch-owned Substitute state and exact observed creation/routing."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state

_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SCHEMA = "detached-substitute-state-v1"
_PROVENANCE = "trusted_observed_substitute_result_v1"


def materialize_observed_substitute(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, observed_result: Mapping[str, Any]) -> dict[str, Any]:
    """Create one exact Substitute from an already-successful observed action."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint or not _valid_creation(observed_result, source_branch_fingerprint): return _result("rejected", "stale_or_invalid_observed_substitute_result")
    owner = observed_result["owner"]; active = branch_state.get("active", {}).get(owner["side"]) if isinstance(branch_state.get("active"), Mapping) else None
    if not _same_owner(active, owner) or not _exact_hp(active): return _result("rejected", "invalid_substitute_owner_hp_authority")
    existing = substitute_state(branch_state, owner)
    if existing["state"] == "unknown": return _result("incomplete", "substitute_state_unknown")
    if existing["state"] == "known_active": return _result("rejected", "substitute_already_active")
    cost = active["max_hp"] // 4
    if active["current_hp"] <= cost or cost <= 0: return _result("rejected", "substitute_insufficient_hp")
    state = deepcopy(dict(branch_state)); current = state["active"][owner["side"]]; current["current_hp"] -= cost
    _sync_hp(state, owner["side"], current["current_hp"], current["max_hp"]); _set_substitute(state, owner, "known_active", cost, source_branch_fingerprint)
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None: return _result("rejected", "unserializable_substitute_creation")
    return {"status":"resolved","source_branch_fingerprint":source_branch_fingerprint,"resulting_branch_fingerprint":fingerprint,"next_state":state,"substitute_creation":{"owner":deepcopy(dict(owner)),"hp_cost":cost,"substitute_hp":cost},"observed_substitute_result":deepcopy(dict(observed_result)),"materialization":"pure_idempotent"}


def substitute_state(branch_state: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    """Read exact, owner-bound Substitute state; absent state is legacy-untracked."""
    context = branch_state.get("substitute_state_context") if isinstance(branch_state, Mapping) else None
    if context is None: return {"state":"legacy_untracked"}
    if not isinstance(context, Mapping) or context.get("schema_version") != _SCHEMA or not isinstance(context.get("states"), list): return {"state":"unknown"}
    match = [row for row in context["states"] if isinstance(row, Mapping) and row.get("owner") == dict(owner)]
    if len(match) != 1: return {"state":"unknown"}
    row = match[0]; status, hp = row.get("state"), row.get("substitute_hp")
    if status == "known_active" and isinstance(hp, int) and not isinstance(hp, bool) and hp > 0: return {"state":status,"substitute_hp":hp}
    if status in {"known_inactive","unknown"} and hp is None: return {"state":status}
    return {"state":"unknown"}


def update_substitute_state_context(
    *, context: Mapping[str, Any] | None, session_id: str, owner: Mapping[str, Any],
    state: str, substitute_hp: int | None, provenance: str,
) -> dict[str, Any] | None:
    """Return one detached owner-bound Substitute context update.

    Runtime reducers and detached branches share this state representation; this
    helper only records already-known state and never calculates Substitute HP.
    """
    if not isinstance(session_id, str) or not session_id or not _exact_owner(owner):
        return None
    if state == "known_active":
        if not isinstance(substitute_hp, int) or isinstance(substitute_hp, bool) or substitute_hp <= 0:
            return None
    elif state in {"known_inactive", "unknown"}:
        if substitute_hp is not None:
            return None
    else:
        return None
    if isinstance(context, Mapping) and context.get("schema_version") == _SCHEMA and context.get("session_id") == session_id and isinstance(context.get("states"), list):
        result = deepcopy(dict(context))
    else:
        result = {"schema_version": _SCHEMA, "session_id": session_id, "provenance": provenance, "states": []}
    rows = result["states"]
    rows[:] = [row for row in rows if not (isinstance(row, Mapping) and row.get("owner") == dict(owner))]
    rows.append({"owner": deepcopy(dict(owner)), "state": state, "substitute_hp": substitute_hp})
    return result


def route_exact_damage_to_substitute(*, branch_state: Mapping[str, Any], target_owner: Mapping[str, Any], damage_amount: int, source_branch_fingerprint: str) -> dict[str, Any] | None:
    """Return an F0->F1 Substitute-only damage transition when state is tracked."""
    status = substitute_state(branch_state, target_owner)
    if status["state"] == "legacy_untracked" or status["state"] == "known_inactive": return None
    if status["state"] == "unknown": return _result("incomplete", "substitute_state_unknown")
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint: return _result("rejected", "stale_or_invalid_substitute_damage_branch")
    state = deepcopy(dict(branch_state)); before = status["substitute_hp"]; absorbed = min(before, damage_amount); remaining = before - absorbed
    _set_substitute(state, target_owner, "known_active" if remaining else "known_inactive", remaining or None, source_branch_fingerprint)
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None: return _result("rejected", "unserializable_substitute_damage")
    return {"status":"resolved","source_branch_fingerprint":source_branch_fingerprint,"resulting_branch_fingerprint":fingerprint,"next_state":state,"damage_application":{"target_owner":deepcopy(dict(target_owner)),"damage":damage_amount,"damage_to_substitute":absorbed,"substitute_hp_before":before,"substitute_hp_after":remaining,"substitute_broken":remaining==0,"target_fainted":False,"target_hit_substitute":True},"materialization":"pure_idempotent"}


def rebind_substitute_after_switch(*, source_branch: Mapping[str, Any], state: dict[str, Any], outgoing_owner: Mapping[str, Any], incoming_owner: Mapping[str, Any], source_branch_fingerprint: str) -> None:
    """Clear switch-out Substitute and make unsupported incoming state explicit unknown."""
    source_context = source_branch.get("substitute_state_context")
    if source_context is None: return
    if not isinstance(source_context, Mapping):
        state["substitute_state_context"] = source_context
        return
    context = update_substitute_state_context(context=source_context, session_id=outgoing_owner["session_id"], owner=outgoing_owner, state="known_inactive", substitute_hp=None, provenance=_PROVENANCE)
    context = update_substitute_state_context(context=context, session_id=incoming_owner["session_id"], owner=incoming_owner, state="unknown", substitute_hp=None, provenance=_PROVENANCE)
    if context is not None:
        context["source_branch_fingerprint"] = source_branch_fingerprint
        state["substitute_state_context"] = context


def _set_substitute(state: dict[str, Any], owner: Mapping[str, Any], status: str, hp: int | None, source_fingerprint: str) -> None:
    context = state.get("substitute_state_context")
    if not isinstance(context, dict) or context.get("schema_version") != _SCHEMA or not isinstance(context.get("states"), list):
        context = {"schema_version":_SCHEMA,"session_id":owner["session_id"],"source_branch_fingerprint":source_fingerprint,"provenance":_PROVENANCE,"states":[]}; state["substitute_state_context"] = context
    rows = context["states"]; rows[:] = [row for row in rows if not (isinstance(row, Mapping) and row.get("owner") == dict(owner))]
    rows.append({"owner":deepcopy(dict(owner)),"state":status,"substitute_hp":hp})


def _valid_creation(value: Any, fingerprint: str) -> bool:
    return isinstance(value, Mapping) and set(value) == {"schema_version","session_id","source_branch_fingerprint","owner","move_id","result","provenance"} and value.get("schema_version") == "observed-substitute-result-v1" and _exact_owner(value.get("owner")) and value.get("move_id") == "substitute" and value.get("result") == "applied" and value.get("provenance") == _PROVENANCE and value.get("source_branch_fingerprint") == fingerprint and value.get("session_id") == value["owner"]["session_id"]


def _exact_owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self","opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _same_owner(active: Any, owner: Mapping[str, Any]) -> bool: return isinstance(active, Mapping) and dict(owner) == {key:active.get(key) for key in _OWNER_KEYS}
def _exact_hp(active: Any) -> bool: return isinstance(active, Mapping) and isinstance(active.get("current_hp"), int) and not isinstance(active.get("current_hp"), bool) and isinstance(active.get("max_hp"), int) and not isinstance(active.get("max_hp"), bool) and 0 < active["current_hp"] <= active["max_hp"]
def _sync_hp(state: Mapping[str, Any], side: str, hp: int, maximum: int) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None; rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current, Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == side: row["current_hp"], row["maximum_hp"] = hp, maximum
def _result(status: str, reason: str) -> dict[str, Any]: return {"status":status,"reason":reason}
