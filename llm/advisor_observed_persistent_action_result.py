"""Materialize exact observed persistent-move results into action authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state


_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_PROVENANCE = "trusted_observed_persistent_action_result_v1"
_REQUIRED = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user",
    "target", "move_id", "applied_effect", "result", "provenance",
})
_SUPPORTED = {
    "aqua-ring": {
        "target": "self",
        "effect": "aqua_ring_persistent_self_volatile",
        "action_provenance": "trusted_deterministic_aqua_ring_application",
    },
    "ingrain": {
        "target": "self",
        "effect": "ingrain_persistent_self_volatile",
        "action_provenance": "trusted_deterministic_ingrain_application",
    },
    "leech-seed": {
        "target": "opponent",
        "effect": "leech_seed_seeded_volatile",
        "action_provenance": "trusted_deterministic_leech_seed_application",
    },
}


def materialize_observed_persistent_action_result(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, observed_result: Mapping[str, Any]) -> dict[str, Any]:
    """Convert one trusted, already-applied observation into action authority.

    This neither determines move success nor mutates battle state. It merely
    validates an externally resolved observation against this exact branch.
    """
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_action_branch")
    if not isinstance(observed_result, Mapping):
        return _result("incomplete", "persistent_action_result_unproven")

    move_id = observed_result.get("move_id")
    effect = _SUPPORTED.get(move_id)
    if effect is None:
        return _result("unsupported", "unsupported_persistent_action_move")
    required = _REQUIRED | ({"target_owner"} if effect["target"] == "opponent" else set())
    if set(observed_result) != required or observed_result.get("schema_version") != "observed-persistent-action-result-v1" or observed_result.get("result") != "applied" or observed_result.get("provenance") != _PROVENANCE:
        return _result("incomplete", "persistent_action_result_unproven")

    user = observed_result.get("user")
    if not isinstance(user, Mapping) or set(user) != set(_OWNER_KEYS):
        return _result("incomplete", "persistent_action_result_unproven")
    side = user.get("side")
    if (
        side not in {"self", "opponent"}
        or not isinstance(active.get(side), Mapping)
        or dict(user) != _owner(active[side])
        or observed_result.get("session_id") != user.get("session_id")
        or observed_result.get("source_branch_fingerprint") != source_branch_fingerprint
        or active[side].get("fainted")
    ):
        return _result("rejected", "stale_or_foreign_observed_action_user")
    if observed_result.get("target") != effect["target"] or observed_result.get("applied_effect") != effect["effect"]:
        return _result("rejected", "mismatched_observed_persistent_action_effect")

    action = {
        "schema_version": "successful-action-effect-v1",
        "session_id": user["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "user": deepcopy(dict(user)),
        "move_id": move_id,
        "target": effect["target"],
        "applied_effect": effect["effect"],
        "execution_status": "applied",
        "provenance": effect["action_provenance"],
    }
    if effect["target"] == "opponent":
        target = _exact_target(active, user, observed_result.get("target_owner"))
        if target is None or active[target["side"]].get("fainted"):
            return _result("rejected", "stale_or_foreign_observed_action_target")
        action["target_owner"] = target
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "successful_action_effect": action,
        "trace": {
            "event": "observed_persistent_action_materialized",
            "move_id": move_id,
            "execution_status": "applied",
            "provenance": _PROVENANCE,
        },
    }


def _owner(active: Mapping[str, Any]) -> dict[str, Any]:
    return {key: active.get(key) for key in _OWNER_KEYS}


def _exact_target(active: Mapping[str, Any], user: Mapping[str, Any], target: Any) -> dict[str, Any] | None:
    if not isinstance(target, Mapping) or set(target) != set(_OWNER_KEYS):
        return None
    side = target.get("side")
    if side not in {"self", "opponent"} or side == user.get("side") or not isinstance(active.get(side), Mapping):
        return None
    return dict(target) if dict(target) == _owner(active[side]) else None


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
