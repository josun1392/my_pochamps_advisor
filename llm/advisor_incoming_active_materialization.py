"""Identity-bound incoming-active materialization for detached switch branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_substitute import rebind_substitute_after_switch
from llm.advisor_bind_residual import rebind_bind_after_switch


_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_incoming_active_branch(
    *, source_branch: Mapping[str, Any], source_branch_fingerprint: str, incoming_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Replace one exact active from a complete, identity-bound incoming authority.

    ``incoming_authority.current_state`` is intentionally the ordinary
    current-state shape consumed by hypothetical direct mechanics.  It is a
    frozen authority handoff, not a reducer observation or a switch-only
    damage format.
    """
    actual = fingerprint_transition_preview_state(source_branch)
    if actual is None or actual != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_source_branch_fingerprint")
    active = source_branch.get("active") if isinstance(source_branch, Mapping) else None
    outgoing_self = active.get("self") if isinstance(active, Mapping) else None
    outgoing_opponent = active.get("opponent") if isinstance(active, Mapping) else None
    if not _active(outgoing_self, "self") or not _active(outgoing_opponent, "opponent"):
        return _result("rejected", "invalid_source_branch_ownership")
    if not isinstance(incoming_authority, Mapping) or incoming_authority.get("provenance") != "identity_bound_incoming_current_state_v1":
        return _result("rejected", "invalid_incoming_authority_provenance")
    owner = incoming_authority.get("owner")
    hp = incoming_authority.get("hp_authority")
    fainted = incoming_authority.get("fainted_authority")
    current = incoming_authority.get("current_state")
    side = owner.get("side") if isinstance(owner, Mapping) else None
    outgoing = active.get(side) if side in {"self", "opponent"} and isinstance(active, Mapping) else None
    retained_side = "opponent" if side == "self" else "self"
    retained = active.get(retained_side) if isinstance(active, Mapping) else None
    if not _owner(owner, session=outgoing_self["session_id"], side=side) or not isinstance(outgoing, Mapping) or not isinstance(retained, Mapping) or owner == _owner_dict(outgoing):
        return _result("rejected", "stale_or_mismatched_incoming_owner")
    if not _known_hp(hp) or not isinstance(fainted, Mapping) or fainted.get("status") != "known" or not isinstance(fainted.get("value"), bool):
        return _result("incomplete", "incoming_exact_hp_or_fainted_authority")
    if fainted["value"] is not (hp["current_hp"] == 0):
        return _result("rejected", "incoming_fainted_hp_mismatch")
    if not isinstance(current, Mapping) or current.get("current_state_session_id") != owner["session_id"]:
        return _result("rejected", "invalid_incoming_current_state")

    # Never copy the source owner's current state. The caller supplies a
    # separately frozen incoming state; only the exact opposing active remains.
    state = {
        "schema_version": "deterministic-transition-preview-v1",
        "active": {side: {**deepcopy(dict(owner)), "current_hp": hp["current_hp"], "max_hp": hp["maximum_hp"], "fainted": fainted["value"]}, retained_side: deepcopy(dict(retained))},
        "current_state": deepcopy(dict(current)),
        "incoming_active_materialization": {
            "schema_version": "detached-incoming-active-v1",
            "source_branch_fingerprint": source_branch_fingerprint,
            "owner": deepcopy(dict(owner)),
            "provenance": "identity_bound_incoming_current_state_v1",
        },
    }
    rebind_substitute_after_switch(source_branch=source_branch, state=state, outgoing_owner=_owner_dict(outgoing), incoming_owner=owner, source_branch_fingerprint=source_branch_fingerprint)
    rebind_bind_after_switch(source_branch=source_branch, state=state, outgoing_owner=_owner_dict(outgoing), incoming_owner=owner, source_branch_fingerprint=source_branch_fingerprint)
    result_fp = fingerprint_transition_preview_state(state)
    if result_fp is None:
        return _result("rejected", "unserializable_materialized_branch")
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "incoming_owner": deepcopy(dict(owner)),
        "resulting_branch_fingerprint": result_fp,
        "next_state": state,
        "materialization_trace": [{
            "sequence": 1, "event": "incoming_active_materialized", "outgoing_owner": _owner_dict(outgoing),
            "incoming_owner": deepcopy(dict(owner)), "execution_status": "executed",
            "provenance": "identity_bound_incoming_current_state_v1",
            "identity_bound_authority_only": True,
        }],
        "boundary": {"phase": "post_switch_pre_entry"},
        "limitations": ["authority_conversion_only", "no_entry_effects_or_action_execution", "no_reducer_or_runtime_writeback"],
    }


def _active(value: Any, side: str) -> bool:
    return isinstance(value, Mapping) and _owner(value, session=value.get("session_id"), side=side) and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and isinstance(value.get("max_hp"), int) and not isinstance(value.get("max_hp"), bool) and value["max_hp"] > 0 and 0 <= value["current_hp"] <= value["max_hp"] and value.get("fainted") is (value["current_hp"] == 0)


def _owner(value: Any, *, session: Any, side: str) -> bool:
    return isinstance(value, Mapping) and value.get("session_id") == session and value.get("side") == side and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _owner_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in _OWNER_KEYS}


def _known_hp(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and isinstance(value.get("maximum_hp"), int) and not isinstance(value.get("maximum_hp"), bool) and value["maximum_hp"] > 0 and 0 <= value["current_hp"] <= value["maximum_hp"]


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
