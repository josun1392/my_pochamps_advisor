"""One exact observed Bind residual family; this is not a volatile scheduler."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _owners, _sync_hp
from llm.advisor_substitute import substitute_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state

_SCHEMA = "detached-bind-residual-state-v1"
_OBSERVED = "observed-bind-result-v1"
_PROVENANCE = "trusted_observed_bind_result_v1"
_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
CANONICAL_BIND_AUTHORITY = {
    "source": "pokemon-showdown",
    "move_source": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts#bind",
    "condition_source": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/conditions.ts#partiallytrapped",
    "move": "bind", "volatile": "partiallytrapped", "duration_turns": (5, 6),
    "residual_order": 13, "residual_divisor": 8,
    "source_leaves_or_faints": "clear_without_residual",
    "forced_switch": "not_blocked; outgoing_state_clears",
}


def materialize_observed_bind(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, observed_result: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize only exact applied Bind evidence into current branch state."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint or not _valid_observation(observed_result, source_branch_fingerprint):
        return _result("rejected", "stale_or_invalid_observed_bind_result")
    source, target = observed_result["source_owner"], observed_result["target_owner"]
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or not _current(active, source) or not _current(active, target) or active[target["side"]].get("fainted"):
        return _result("rejected", "invalid_bind_owner_authority")
    sub = substitute_state(branch_state, target)
    if sub["state"] == "unknown": return _result("incomplete", "substitute_state_unknown")
    if sub["state"] == "known_active": return _result("rejected", "bind_blocked_by_substitute")
    existing = bind_state(branch_state, target)
    if existing["state"] == "unknown": return _result("incomplete", "bind_state_unknown")
    if existing["state"] == "known_active": return _result("rejected", "bind_already_active")
    state = deepcopy(dict(branch_state))
    _set_bind(state, target, "known_active", source, observed_result["duration_turns"], source_branch_fingerprint)
    fp = fingerprint_transition_preview_state(state)
    if fp is None: return _result("rejected", "unserializable_bind_application")
    return {"status":"resolved", "source_branch_fingerprint":source_branch_fingerprint, "resulting_branch_fingerprint":fp,
            "next_state":state, "bind_application":{"source_owner":deepcopy(dict(source)), "target_owner":deepcopy(dict(target)), "remaining_turns":observed_result["duration_turns"]},
            "observed_bind_result":deepcopy(dict(observed_result)), "materialization":"pure_idempotent"}


def bind_state(branch_state: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact owner row. An absent context is compatibility-untracked."""
    context = branch_state.get("bind_residual_state_context") if isinstance(branch_state, Mapping) else None
    if context is None: return {"state":"legacy_untracked"}
    if not isinstance(context, Mapping) or context.get("schema_version") != _SCHEMA or context.get("session_id") != owner.get("session_id") or context.get("provenance") != _PROVENANCE or not isinstance(context.get("states"), list): return {"state":"unknown"}
    rows = [row for row in context["states"] if isinstance(row, Mapping) and row.get("target_owner") == dict(owner)]
    if len(rows) != 1: return {"state":"unknown"}
    row = rows[0]
    if row.get("state") == "known_active" and _owner(row.get("source_owner")) and isinstance(row.get("remaining_turns"), int) and not isinstance(row["remaining_turns"], bool) and row["remaining_turns"] in {1,2,3,4,5,6}:
        return {"state":"known_active", "source_owner":deepcopy(dict(row["source_owner"])), "remaining_turns":row["remaining_turns"]}
    if row.get("state") in {"known_inactive", "unknown"} and row.get("source_owner") is None and row.get("remaining_turns") is None: return {"state":row["state"]}
    return {"state":"unknown"}


def apply_owner_bind_end_of_turn(*, state: dict[str, Any], side: str, owner: Mapping[str, Any], source_branch_fingerprint: str) -> dict[str, Any]:
    """Apply one exact tier-13 Bind residual and decrement/expire its state."""
    owners = _owners(state)
    if owners is None or owners.get(side) != dict(owner) or fingerprint_transition_preview_state(state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_foreign_bind_owner")
    binding = bind_state(state, owner)
    if binding["state"] == "legacy_untracked" or binding["state"] == "known_inactive": return {"status":"resolved", "trace":None}
    if binding["state"] == "unknown": return _result("incomplete", "bind_state_unknown")
    source_side = binding["source_owner"]["side"]
    if owners.get(source_side) != binding["source_owner"] or state["active"][source_side].get("fainted"):
        _set_bind(state, owner, "known_inactive", None, None, source_branch_fingerprint)
        return {"status":"resolved", "trace":{"effect":"bind_residual", "owner":deepcopy(dict(owner)), "execution_status":"cleared", "reason":"bind_source_not_active"}}
    active = state["active"][side]
    if active.get("fainted"): return _result("rejected", "bind_fainted_target")
    hp, maximum = active.get("current_hp"), active.get("max_hp")
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or not 0 < hp <= maximum:
        return _result("incomplete", "bind_current_hp_authority")
    damage = max(1, maximum // 8); post = max(0, hp - damage)
    active["current_hp"], active["fainted"] = post, post == 0; _sync_hp(state, side, post, maximum)
    remaining = binding["remaining_turns"] - 1
    _set_bind(state, owner, "known_active" if remaining else "known_inactive", binding["source_owner"] if remaining else None, remaining if remaining else None, source_branch_fingerprint)
    return {"status":"resolved", "trace":{"effect":"bind_residual", "owner":deepcopy(dict(owner)), "source_owner":deepcopy(binding["source_owner"]), "pre_hp":hp, "post_hp":post, "damage":damage, "remaining_turns_before":binding["remaining_turns"], "remaining_turns_after":remaining, "expired":not bool(remaining), "target_fainted":post == 0, "execution_status":"executed", "provenance":_PROVENANCE}}


def rebind_bind_after_switch(*, source_branch: Mapping[str, Any], state: dict[str, Any], outgoing_owner: Mapping[str, Any], incoming_owner: Mapping[str, Any], source_branch_fingerprint: str) -> None:
    """A legal (including forced) switch clears the outgoing trap and source links."""
    context = source_branch.get("bind_residual_state_context")
    if context is None: return
    if not isinstance(context, Mapping): state["bind_residual_state_context"] = context; return
    state["bind_residual_state_context"] = deepcopy(dict(context))
    rows = state["bind_residual_state_context"].get("states")
    if not isinstance(rows, list): return
    for row in list(rows):
        if isinstance(row, Mapping) and (row.get("target_owner") == dict(outgoing_owner) or row.get("source_owner") == dict(outgoing_owner)):
            _set_bind(state, row.get("target_owner"), "known_inactive", None, None, source_branch_fingerprint)
    _set_bind(state, incoming_owner, "unknown", None, None, source_branch_fingerprint)


def _set_bind(state: dict[str, Any], target: Any, status: str, source: Mapping[str, Any] | None, remaining: int | None, fingerprint: str) -> None:
    if not _owner(target): return
    context = state.get("bind_residual_state_context")
    if not isinstance(context, dict) or context.get("schema_version") != _SCHEMA or not isinstance(context.get("states"), list):
        context = {"schema_version":_SCHEMA, "session_id":target["session_id"], "source_branch_fingerprint":fingerprint, "provenance":_PROVENANCE, "states":[]}; state["bind_residual_state_context"] = context
    rows = context["states"]; rows[:] = [row for row in rows if not (isinstance(row, Mapping) and row.get("target_owner") == dict(target))]
    rows.append({"target_owner":deepcopy(dict(target)), "state":status, "source_owner":deepcopy(dict(source)) if source else None, "remaining_turns":remaining})


def _valid_observation(value: Any, fp: str) -> bool:
    required = {"schema_version","session_id","source_branch_fingerprint","source_owner","target_owner","move_id","damaging_hit_result","bind_result","duration_turns","provenance"}
    return isinstance(value, Mapping) and set(value) == required and value.get("schema_version") == _OBSERVED and _owner(value.get("source_owner")) and _owner(value.get("target_owner")) and value["source_owner"]["side"] != value["target_owner"]["side"] and value.get("session_id") == value["source_owner"]["session_id"] == value["target_owner"]["session_id"] and value.get("source_branch_fingerprint") == fp and value.get("move_id") == "bind" and value.get("damaging_hit_result") == "applied" and value.get("bind_result") == "applied" and value.get("duration_turns") in {5, 6} and value.get("provenance") == _PROVENANCE


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self","opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _current(active: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    row = active.get(owner["side"]); return isinstance(row, Mapping) and dict(owner) == {key:row.get(key) for key in _KEYS}
def _result(status: str, reason: str) -> dict[str, Any]: return {"status":status,"reason":reason}
