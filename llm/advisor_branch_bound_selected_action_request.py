"""Strict branch-local normalization for a selected attack action.

This adapter bridges the own selected-action shape and the opponent response
shape without granting mechanics.  It only rebinds immutable move metadata to
the exact current branch D0/actor/target.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "branch-bound-selected-attack-request-v1"


def normalize_branch_bound_selected_attack_request(
    *,
    strategy_d0: Mapping[str, Any],
    source_action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    metadata_authority: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(strategy_d0, Mapping)
        or strategy_d0.get("status") != "resolved"
        or strategy_d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1"
        or not isinstance(source_action, Mapping)
        or not isinstance(actor, Mapping)
        or not isinstance(target, Mapping)
        or not isinstance(metadata_authority, Mapping)
    ):
        return _result("rejected", "branch_selected_action_request_invalid")

    active = strategy_d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or strategy_d0.get("decision_owner") != dict(actor)
        or active.get(actor.get("side")) != dict(actor)
        or actor.get("side") == target.get("side")
        or active.get(target.get("side")) != dict(target)
    ):
        return _result("rejected", "branch_selected_action_actor_target_binding_mismatch")

    for key in ("opponent_actor", "actor"):
        if key in source_action:
            explicit_actor = source_action[key]
            if (
                not isinstance(explicit_actor, Mapping)
                or explicit_actor != dict(actor)
            ):
                return _result(
                    "rejected",
                    "branch_selected_action_source_actor_binding_mismatch",
                )

    for key in ("target_owner", "target"):
        if key in source_action:
            explicit_target = source_action[key]
            if (
                not isinstance(explicit_target, Mapping)
                or explicit_target != dict(target)
            ):
                return _result(
                    "rejected",
                    "branch_selected_action_target_binding_mismatch",
                )

    action_id = source_action.get("action_id")
    identity = source_action.get("identity")
    response_move = source_action.get("move_id")
    if (
        source_action.get("action_type") != "attack"
        or not isinstance(action_id, str)
        or not action_id
    ):
        return _result("rejected", "branch_selected_action_identity_missing")
    move_ids = [value for value in (identity, response_move) if isinstance(value, str) and value]
    if not move_ids or len(set(move_ids)) != 1:
        return _result("rejected", "branch_selected_action_move_identity_conflict")
    move_id = move_ids[0]

    metadata = metadata_authority.get("metadata")
    if (
        metadata_authority.get("status") != "resolved"
        or not isinstance(metadata, Mapping)
        or metadata.get("move_id") != move_id
    ):
        return _result("rejected", "branch_selected_action_metadata_mismatch")
    metadata_binding_error = _metadata_claim_binding_error(
        metadata_authority,
        actor=actor,
        action_id=action_id,
    )
    if metadata_binding_error is not None:
        return _result("rejected", metadata_binding_error)

    embedded = source_action.get("move_metadata_authority")
    opponent_embedded = source_action.get("metadata_authority")
    for value in (embedded, opponent_embedded):
        if value is None:
            continue
        if (
            not isinstance(value, Mapping)
            or value.get("status") != "resolved"
            or value.get("metadata") != metadata
            or value.get("move_id", move_id) != move_id
        ):
            return _result("rejected", "branch_selected_action_embedded_metadata_mismatch")
        embedded_binding_error = _metadata_claim_binding_error(
            value,
            actor=actor,
            action_id=action_id,
        )
        if embedded_binding_error is not None:
            return _result("rejected", embedded_binding_error)

    rebound = deepcopy(dict(metadata_authority))
    rebound.update({
        "status": "resolved",
        "candidate_id": action_id,
        "move_id": move_id,
        "session_id": strategy_d0.get("session_id"),
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(strategy_d0.get("decision_owner")),
        "active_attacker": deepcopy(dict(actor)),
        "metadata": deepcopy(dict(metadata)),
        "branch_rebound_selected_action": True,
    })
    normalized = {
        "action_id": action_id,
        "action_type": "attack",
        "identity": move_id,
        "move_id": move_id,
        "move_metadata_authority": deepcopy(rebound),
        "target_owner": deepcopy(dict(target)),
    }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0.get("session_id"),
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(strategy_d0.get("decision_owner")),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "source_action_id": action_id,
        "move_id": move_id,
        "normalized_action": normalized,
        "branch_move_metadata_authority": deepcopy(rebound),
        "provenance": "strict_branch_bound_selected_attack_normalization_v1",
    }


def _metadata_claim_binding_error(
    authority: Mapping[str, Any],
    *,
    actor: Mapping[str, Any],
    action_id: str,
) -> str | None:
    if "active_attacker" in authority:
        explicit_actor = authority["active_attacker"]
        if (
            not isinstance(explicit_actor, Mapping)
            or explicit_actor != dict(actor)
        ):
            return "branch_selected_action_metadata_actor_binding_mismatch"
    if (
        "candidate_id" in authority
        and authority["candidate_id"] != action_id
    ):
        return "branch_selected_action_metadata_candidate_binding_mismatch"
    return None


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
