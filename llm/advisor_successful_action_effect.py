"""Narrow detached successful-action authority for approved persistent effects."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state


_OWNERSHIP_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_REQUIRED_ACTION_EFFECT_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user",
    "move_id", "target", "applied_effect", "execution_status", "provenance",
})
_EFFECTS = {
    "aqua_ring": {
        "move_id": "aqua-ring",
        "applied_effect": "aqua_ring_persistent_self_volatile",
        "action_provenance": "trusted_deterministic_aqua_ring_application",
        "context_key": "aqua_ring_persistent_effect_context",
        "context_schema": "detached-aqua-ring-persistent-effect-v1",
        "context_provenance": "trusted_aqua_ring_persistent_effect_state",
        "target_mode": "self",
    },
    "ingrain": {
        "move_id": "ingrain",
        "applied_effect": "ingrain_persistent_self_volatile",
        "action_provenance": "trusted_deterministic_ingrain_application",
        "context_key": "ingrain_persistent_effect_context",
        "context_schema": "detached-ingrain-persistent-effect-v1",
        "context_provenance": "trusted_ingrain_persistent_effect_state",
        "target_mode": "self",
    },
    "leech_seed": {
        "move_id": "leech-seed",
        "applied_effect": "leech_seed_seeded_volatile",
        "action_provenance": "trusted_deterministic_leech_seed_application",
        "context_key": "leech_seed_persistent_effect_context",
        "context_schema": "detached-leech-seed-persistent-effect-v1",
        "context_provenance": "trusted_leech_seed_persistent_effect_state",
        "target_mode": "opponent",
    },
}


def apply_successful_aqua_ring(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, action_effect: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one already-resolved Aqua Ring self-volatile action record.

    Move eligibility, selection, and move metadata are deliberately not inputs
    to this seam. The supplied record must already prove the self effect was
    applied on this exact detached generation.
    """
    return _apply_successful_persistent_effect(
        family="aqua_ring",
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        action_effect=action_effect,
    )


def apply_successful_ingrain(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, action_effect: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one already-resolved Ingrain self-volatile action record."""
    return _apply_successful_persistent_effect(
        family="ingrain",
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        action_effect=action_effect,
    )


def apply_successful_leech_seed(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, action_effect: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one already-resolved Leech Seed target-volatile action record."""
    return _apply_successful_persistent_effect(
        family="leech_seed",
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        action_effect=action_effect,
    )


def _apply_successful_persistent_effect(*, family: str, branch_state: Mapping[str, Any], source_branch_fingerprint: str, action_effect: Mapping[str, Any]) -> dict[str, Any]:
    effect = _EFFECTS[family]
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_action_branch")
    if not _is_successful_persistent_effect(action_effect, effect):
        return _result("incomplete", f"{family}_application_unproven")

    user = action_effect["user"]
    side = user["side"]
    target = _target_owner(active, user, action_effect, effect)
    if (
        side not in {"self", "opponent"}
        or not isinstance(active.get(side), Mapping)
        or dict(user) != _owner(active[side])
        or action_effect["session_id"] != user["session_id"]
        or action_effect["source_branch_fingerprint"] != source_branch_fingerprint
        or active[side].get("fainted")
        or target is None
        or active[target["side"]].get("fainted")
    ):
        return _result("rejected", f"stale_or_foreign_{family}_application")

    bundle = branch_state.get("branch_persistent_effect_authority")
    if not isinstance(bundle, Mapping) or not isinstance(bundle.get("states"), list):
        return _result("incomplete", "persistent_effect_authority_unknown")

    state = deepcopy(dict(branch_state))
    rows = state["branch_persistent_effect_authority"]["states"]
    matches = [row for row in rows if isinstance(row, dict) and row.get("family") == family and row.get("owner") == target]
    if len(matches) != 1:
        return _result("rejected", f"invalid_{family}_bundle_owner")

    # This is the sole approved promotion path. A repeat application replaces
    # the same row, so no additional persistent instance can be created.
    prior_source_slot = matches[0].get("source_slot") if matches[0].get("state") == "known_active" else None
    if family == "leech_seed" and matches[0].get("state") == "known_active" and not _source_slot_is_valid(prior_source_slot, user):
        return _result("rejected", "invalid_active_leech_seed_source_slot")
    source_slot = prior_source_slot if family == "leech_seed" and prior_source_slot is not None else _source_slot(user) if family == "leech_seed" else None
    matches[0]["state"] = "known_active"
    matches[0]["provenance"] = f"successful_action_effect_{family}_v1"
    if source_slot is not None:
        matches[0]["source_slot"] = source_slot
    state[effect["context_key"]] = _persistent_effect_context(
        state=state,
        family=family,
        target=target,
        source_slot=source_slot,
        source_branch_fingerprint=source_branch_fingerprint,
    )

    resulting_fingerprint = fingerprint_transition_preview_state(state)
    if resulting_fingerprint is None:
        return _result("rejected", f"unserializable_{family}_application")
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": resulting_fingerprint,
        "next_state": state,
        "action_effect": deepcopy(dict(action_effect)),
        "trace": {
            "effect": f"{family}_application",
            "owner": deepcopy(target),
            "source": deepcopy(dict(user)) if target != dict(user) else None,
            "execution_status": "applied",
            "provenance": f"successful_action_effect_{family}_v1",
        },
    }


def _is_successful_persistent_effect(action_effect: Mapping[str, Any], effect: Mapping[str, str]) -> bool:
    required = _REQUIRED_ACTION_EFFECT_KEYS | ({"target_owner"} if effect["target_mode"] == "opponent" else set())
    if not isinstance(action_effect, Mapping) or set(action_effect) != required:
        return False
    user = action_effect.get("user")
    return (
        action_effect.get("schema_version") == "successful-action-effect-v1"
        and isinstance(user, Mapping)
        and set(user) == set(_OWNERSHIP_KEYS)
        and action_effect.get("move_id") == effect["move_id"]
        and action_effect.get("target") == effect["target_mode"]
        and action_effect.get("applied_effect") == effect["applied_effect"]
        and action_effect.get("execution_status") == "applied"
        and action_effect.get("provenance") == effect["action_provenance"]
    )


def _owner(active: Mapping[str, Any]) -> dict[str, Any]:
    return {key: active.get(key) for key in _OWNERSHIP_KEYS}


def _target_owner(active: Mapping[str, Any], user: Mapping[str, Any], action_effect: Mapping[str, Any], effect: Mapping[str, str]) -> dict[str, Any] | None:
    if effect["target_mode"] == "self":
        return dict(user)
    target = action_effect.get("target_owner")
    target_side = target.get("side") if isinstance(target, Mapping) else None
    if target_side not in {"self", "opponent"} or target_side == user.get("side") or not isinstance(active.get(target_side), Mapping):
        return None
    return dict(target) if dict(target) == _owner(active[target_side]) else None


def _source_slot(user: Mapping[str, Any]) -> dict[str, Any]:
    return {key: user[key] for key in ("session_id", "side", "slot_index")}


def _source_slot_is_valid(source_slot: Any, user: Mapping[str, Any]) -> bool:
    return isinstance(source_slot, Mapping) and set(source_slot) == {"session_id", "side", "slot_index"} and source_slot.get("session_id") == user.get("session_id") and source_slot.get("side") in {"self", "opponent"} and isinstance(source_slot.get("slot_index"), int) and not isinstance(source_slot.get("slot_index"), bool)


def _persistent_effect_context(*, state: Mapping[str, Any], family: str, target: Mapping[str, Any], source_slot: Mapping[str, Any] | None, source_branch_fingerprint: str) -> dict[str, Any]:
    effect = _EFFECTS[family]
    rows = state["branch_persistent_effect_authority"]["states"]
    owners = [_owner(state["active"][side]) for side in ("self", "opponent")]
    return {
        "schema_version": effect["context_schema"],
        "session_id": target["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "provenance": effect["context_provenance"],
        "states": [
            {
                "owner": owner,
                "state": "known_active" if owner == dict(target) else next(
                    (row.get("state") for row in rows if row.get("family") == family and row.get("owner") == owner),
                    "unknown",
                ),
                **({"source_slot": deepcopy(dict(source_slot))} if family == "leech_seed" and owner == dict(target) and source_slot is not None else _stored_source_slot(rows, family, owner)),
            }
            for owner in owners
        ],
    }


def _stored_source_slot(rows: list[Mapping[str, Any]], family: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    row = next((row for row in rows if row.get("family") == family and row.get("owner") == owner), None)
    return {"source_slot": deepcopy(dict(row["source_slot"]))} if family == "leech_seed" and isinstance(row, Mapping) and isinstance(row.get("source_slot"), Mapping) else {}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
