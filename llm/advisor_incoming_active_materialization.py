"""Identity-bound incoming-active materialization for detached switch branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_substitute import rebind_substitute_after_switch
from llm.advisor_bind_residual import rebind_bind_after_switch
from llm.advisor_perish_song import rebind_perish_song_after_switch
from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority


_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_PERSISTENT_CONTEXTS = (
    ("aqua_ring", "aqua_ring_persistent_effect_context", "detached-aqua-ring-persistent-effect-v1", "trusted_aqua_ring_persistent_effect_state"),
    ("ingrain", "ingrain_persistent_effect_context", "detached-ingrain-persistent-effect-v1", "trusted_ingrain_persistent_effect_state"),
    ("leech_seed", "leech_seed_persistent_effect_context", "detached-leech-seed-persistent-effect-v1", "trusted_leech_seed_persistent_effect_state"),
)


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
    rebind_perish_song_after_switch(source_branch=source_branch, state=state, outgoing_owner=_owner_dict(outgoing), incoming_owner=owner, source_branch_fingerprint=source_branch_fingerprint)
    persistent_error = _rebind_persistent_effects_after_switch(
        source_branch=source_branch, state=state, outgoing_owner=_owner_dict(outgoing),
        incoming_owner=owner, retained_owner=_owner_dict(retained),
        source_branch_fingerprint=source_branch_fingerprint,
    )
    if persistent_error is not None:
        return _result("rejected", persistent_error)
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


def _rebind_persistent_effects_after_switch(
    *, source_branch: Mapping[str, Any], state: dict[str, Any], outgoing_owner: Mapping[str, Any],
    incoming_owner: Mapping[str, Any], retained_owner: Mapping[str, Any], source_branch_fingerprint: str,
) -> str | None:
    """Retire only the switching target's persistent rows.

    Aqua Ring and Ingrain are owned by their affected Pokemon.  Leech Seed is
    owned by its seeded target, while ``source_slot`` describes the opposite
    field position and therefore survives a source-side switch.
    """
    incoming_side = incoming_owner["side"]
    retained_side = retained_owner["side"]
    owners = {incoming_side: dict(incoming_owner), retained_side: dict(retained_owner)}
    bundle = source_branch.get("branch_persistent_effect_authority")
    if bundle is not None:
        rows = _persistent_rows(bundle=bundle, outgoing_owner=outgoing_owner, retained_owner=retained_owner)
        if rows is None:
            return "invalid_persistent_effect_authority_on_switch"
        states = {incoming_side: {}, retained_side: {}}
        for family, _, _, _ in _PERSISTENT_CONTEXTS:
            states[incoming_side][family] = {"state": "known_inactive"}
            states[retained_side][family] = _row_payload(rows[(family, "retained")], family=family)
        state["branch_persistent_effect_authority"] = materialize_persistent_effect_authority(
            owners=owners, source_branch_fingerprint=source_branch_fingerprint, states=states,
        )
    for family, key, schema, provenance in _PERSISTENT_CONTEXTS:
        context = source_branch.get(key)
        if context is None:
            continue
        retained_row = _context_row(
            context=context, schema=schema, provenance=provenance,
            owner=retained_owner, family=family,
        )
        outgoing_row = _context_row(
            context=context, schema=schema, provenance=provenance,
            owner=outgoing_owner, family=family,
        )
        if retained_row is None or outgoing_row is None:
            return f"invalid_{family}_persistent_effect_context_on_switch"
        rows = [
            {"owner": deepcopy(dict(incoming_owner)), "state": "known_inactive"},
            _context_payload(retained_row, owner=retained_owner, family=family),
        ]
        state[key] = {
            "schema_version": schema, "session_id": incoming_owner["session_id"],
            "source_branch_fingerprint": source_branch_fingerprint, "provenance": provenance,
            "states": rows,
        }
    return None


def _persistent_rows(*, bundle: Any, outgoing_owner: Mapping[str, Any], retained_owner: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]] | None:
    if not isinstance(bundle, Mapping) or bundle.get("schema_version") != "branch-persistent-effect-authority-v1" or bundle.get("session_id") != outgoing_owner.get("session_id") or bundle.get("provenance") != "trusted_branch_persistent_effect_materialization" or not isinstance(bundle.get("source_branch_fingerprint"), str):
        return None
    rows = bundle.get("states")
    if not isinstance(rows, list) or len(rows) != len(_PERSISTENT_CONTEXTS) * 2:
        return None
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for family, _, _, _ in _PERSISTENT_CONTEXTS:
        for label, owner in (("outgoing", outgoing_owner), ("retained", retained_owner)):
            matches = [row for row in rows if isinstance(row, Mapping) and row.get("family") == family and row.get("owner") == dict(owner)]
            if len(matches) != 1 or not _valid_persistent_row(matches[0], family=family):
                return None
            result[(family, label)] = matches[0]
    return result


def _context_row(*, context: Any, schema: str, provenance: str, owner: Mapping[str, Any], family: str) -> Mapping[str, Any] | None:
    if not isinstance(context, Mapping) or context.get("schema_version") != schema or context.get("session_id") != owner.get("session_id") or context.get("provenance") != provenance or not isinstance(context.get("source_branch_fingerprint"), str) or not isinstance(context.get("states"), list) or len(context["states"]) != 2:
        return None
    matches = [row for row in context["states"] if isinstance(row, Mapping) and row.get("owner") == dict(owner)]
    return matches[0] if len(matches) == 1 and _valid_persistent_row(matches[0], family=family) else None


def _valid_persistent_row(row: Mapping[str, Any], *, family: str) -> bool:
    if row.get("state") not in {"known_active", "known_inactive", "unknown"}:
        return False
    if family != "leech_seed" or row["state"] != "known_active":
        return "source_slot" not in row
    source, owner = row.get("source_slot"), row.get("owner")
    return isinstance(source, Mapping) and isinstance(owner, Mapping) and set(source) == {"session_id", "side", "slot_index"} and source.get("session_id") == owner.get("session_id") and source.get("side") in {"self", "opponent"} and source.get("side") != owner.get("side") and isinstance(source.get("slot_index"), int) and not isinstance(source.get("slot_index"), bool) and source["slot_index"] >= 0


def _row_payload(row: Mapping[str, Any], *, family: str) -> dict[str, Any]:
    payload = {"state": row["state"]}
    if "provenance" in row:
        payload["provenance"] = deepcopy(row["provenance"])
    if family == "leech_seed" and row["state"] == "known_active":
        payload["source_slot"] = deepcopy(dict(row["source_slot"]))
    return payload


def _context_payload(row: Mapping[str, Any], *, owner: Mapping[str, Any], family: str) -> dict[str, Any]:
    payload = {"owner": deepcopy(dict(owner)), "state": row["state"]}
    if family == "leech_seed" and row["state"] == "known_active":
        payload["source_slot"] = deepcopy(dict(row["source_slot"]))
    return payload


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
