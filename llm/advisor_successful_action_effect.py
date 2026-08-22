"""Narrow detached successful-action authority for approved self-volatiles."""
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
    },
    "ingrain": {
        "move_id": "ingrain",
        "applied_effect": "ingrain_persistent_self_volatile",
        "action_provenance": "trusted_deterministic_ingrain_application",
        "context_key": "ingrain_persistent_effect_context",
        "context_schema": "detached-ingrain-persistent-effect-v1",
        "context_provenance": "trusted_ingrain_persistent_effect_state",
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


def _apply_successful_persistent_effect(*, family: str, branch_state: Mapping[str, Any], source_branch_fingerprint: str, action_effect: Mapping[str, Any]) -> dict[str, Any]:
    effect = _EFFECTS[family]
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_action_branch")
    if not _is_successful_persistent_effect(action_effect, effect):
        return _result("incomplete", f"{family}_application_unproven")

    user = action_effect["user"]
    side = user["side"]
    if (
        side not in {"self", "opponent"}
        or not isinstance(active.get(side), Mapping)
        or dict(user) != _owner(active[side])
        or action_effect["session_id"] != user["session_id"]
        or action_effect["source_branch_fingerprint"] != source_branch_fingerprint
        or active[side].get("fainted")
    ):
        return _result("rejected", f"stale_or_foreign_{family}_application")

    bundle = branch_state.get("branch_persistent_effect_authority")
    if not isinstance(bundle, Mapping) or not isinstance(bundle.get("states"), list):
        return _result("incomplete", "persistent_effect_authority_unknown")

    state = deepcopy(dict(branch_state))
    rows = state["branch_persistent_effect_authority"]["states"]
    matches = [row for row in rows if isinstance(row, dict) and row.get("family") == family and row.get("owner") == dict(user)]
    if len(matches) != 1:
        return _result("rejected", f"invalid_{family}_bundle_owner")

    # This is the sole approved promotion path. A repeat application replaces
    # the same row, so no additional persistent instance can be created.
    matches[0]["state"] = "known_active"
    matches[0]["provenance"] = f"successful_action_effect_{family}_v1"
    state[effect["context_key"]] = _persistent_effect_context(
        state=state,
        family=family,
        user=user,
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
            "owner": deepcopy(dict(user)),
            "execution_status": "applied",
            "provenance": f"successful_action_effect_{family}_v1",
        },
    }


def _is_successful_persistent_effect(action_effect: Mapping[str, Any], effect: Mapping[str, str]) -> bool:
    if not isinstance(action_effect, Mapping) or set(action_effect) != _REQUIRED_ACTION_EFFECT_KEYS:
        return False
    user = action_effect.get("user")
    return (
        action_effect.get("schema_version") == "successful-action-effect-v1"
        and isinstance(user, Mapping)
        and set(user) == set(_OWNERSHIP_KEYS)
        and action_effect.get("move_id") == effect["move_id"]
        and action_effect.get("target") == "self"
        and action_effect.get("applied_effect") == effect["applied_effect"]
        and action_effect.get("execution_status") == "applied"
        and action_effect.get("provenance") == effect["action_provenance"]
    )


def _owner(active: Mapping[str, Any]) -> dict[str, Any]:
    return {key: active.get(key) for key in _OWNERSHIP_KEYS}


def _persistent_effect_context(*, state: Mapping[str, Any], family: str, user: Mapping[str, Any], source_branch_fingerprint: str) -> dict[str, Any]:
    effect = _EFFECTS[family]
    rows = state["branch_persistent_effect_authority"]["states"]
    owners = [_owner(state["active"][side]) for side in ("self", "opponent")]
    return {
        "schema_version": effect["context_schema"],
        "session_id": user["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "provenance": effect["context_provenance"],
        "states": [
            {
                "owner": owner,
                "state": "known_active" if owner == dict(user) else next(
                    (row.get("state") for row in rows if row.get("family") == family and row.get("owner") == owner),
                    "unknown",
                ),
            }
            for owner in owners
        ],
    }


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
