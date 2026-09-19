"""Authenticated detached Berry-eaten transition from one Fling target Eat."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_berry_eat_item_interactions import resolve_canonical_fling_berry_item_identity

SCHEMA_VERSION = "detached-berry-eaten-transition-v1"


def materialize_detached_fling_berry_eaten_transition(
    *, strategy_d0: Mapping[str, Any], source_leaf: Mapping[str, Any],
    interaction_authority: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(interaction_authority, Mapping) or interaction_authority.get("status") != "resolved":
        return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "berry_eat_interaction_invalid"}
    base = {
        "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0.get("session_id"),
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(strategy_d0.get("decision_owner")),
        "owner": deepcopy(dict(target)) if isinstance(target, Mapping) else target,
        "source_action_id": interaction_authority.get("action_id"),
        "source_leaf_id": source_leaf.get("leaf_id") if isinstance(source_leaf, Mapping) else None,
        "source_berry_item_id": interaction_authority.get("item_id"),
    }
    if interaction_authority.get("phase") != "post_hit_target_berry_interaction":
        return {"status": "rejected", **base, "reason": "berry_eaten_transition_wrong_phase"}
    if interaction_authority.get("target") != dict(target) or interaction_authority.get("source_hit", {}).get("source_leaf_id") != base["source_leaf_id"]:
        return {"status": "rejected", **base, "reason": "berry_eaten_transition_binding_mismatch"}
    identity = resolve_canonical_fling_berry_item_identity(base["source_berry_item_id"])
    if identity.get("status") != "resolved":
        return {"status": "rejected", **base, "reason": "berry_eaten_transition_item_invalid"}
    if interaction_authority.get("outcome") != "post_hit_target_eat_item_dispatched" or interaction_authority.get("target_eat_occurred") is not True or interaction_authority.get("target_eat_item_dispatched") is not True:
        return {"status": "not_applicable", **base, "reason": interaction_authority.get("reason", "target_berry_eat_not_reached")}
    prior = strategy_d0.get("current_berry_eaten_authority", {}).get(target["side"], {})
    if not isinstance(prior, Mapping) or prior.get("owner") != dict(target):
        return {"status": "rejected", **base, "reason": "berry_eaten_prior_authority_missing"}
    prior_state = prior.get("state") if prior.get("status") == "resolved" else "unknown"
    return {
        "status": "resolved", **base,
        "prior_state": prior_state,
        "prior_state_authority": deepcopy(dict(prior)),
        "resulting_state": "known_true",
        "transition": "true_to_true" if prior_state == "known_true" else "to_true",
        "berry_eat_item_interaction_authority": deepcopy(dict(interaction_authority)),
        "provenance": "authenticated_fling_target_berry_eat_to_persistent_state_v1",
    }


def validate_detached_berry_eaten_transition(value: Any, *, leaf: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or not isinstance(leaf, Mapping) or not isinstance(target, Mapping):
        return False
    provenance = leaf.get("provenance")
    interaction = value.get("berry_eat_item_interaction_authority")
    prior = value.get("prior_state_authority")
    if not isinstance(provenance, Mapping) or not isinstance(interaction, Mapping) or not isinstance(prior, Mapping):
        return False
    berry = resolve_canonical_fling_berry_item_identity(value.get("source_berry_item_id"))
    prior_state = value.get("prior_state")
    prior_valid = (
        prior.get("owner") == dict(target)
        and prior.get("session_id") == provenance.get("session_id")
        and prior.get("source_runtime_fingerprint") == provenance.get("source_runtime_fingerprint")
        and prior.get("source_branch_fingerprint") == provenance.get("source_branch_fingerprint")
        and (
            prior.get("status") == "resolved"
            and prior.get("state") in {"known_true", "known_false"}
            and prior_state == prior.get("state")
            or prior.get("status") == "incomplete"
            and prior.get("state") == "unknown"
            and prior_state == "unknown"
        )
    )
    return (
        value.get("status") == "resolved"
        and value.get("schema_version") == SCHEMA_VERSION
        and value.get("owner") == dict(target)
        and value.get("source_leaf_id") == leaf.get("leaf_id")
        and value.get("source_action_id") == leaf.get("candidate_id")
        and value.get("source_action_id") == interaction.get("action_id")
        and value.get("source_berry_item_id") == interaction.get("item_id")
        and berry.get("status") == "resolved"
        and prior_valid
        and value.get("resulting_state") == "known_true"
        and value.get("transition") == ("true_to_true" if prior_state == "known_true" else "to_true")
        and value.get("provenance") == "authenticated_fling_target_berry_eat_to_persistent_state_v1"
        and interaction.get("status") == "resolved"
        and interaction.get("phase") == "post_hit_target_berry_interaction"
        and interaction.get("outcome") == "post_hit_target_eat_item_dispatched"
        and interaction.get("source_hit", {}).get("source_leaf_id") == leaf.get("leaf_id")
        and interaction.get("target") == dict(target)
        and interaction.get("target_eat_occurred") is True
        and interaction.get("target_eat_item_dispatched") is True
        and value.get("session_id") == provenance.get("session_id")
        and value.get("source_runtime_fingerprint") == provenance.get("source_runtime_fingerprint")
        and value.get("source_branch_fingerprint") == provenance.get("source_branch_fingerprint")
        and value.get("decision_owner") == provenance.get("decision_owner")
    )
