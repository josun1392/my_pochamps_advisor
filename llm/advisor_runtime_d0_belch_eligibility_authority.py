"""Exact Belch legality/execution gate from persistent Berry-eaten authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "runtime-d0-belch-eligibility-authority-v1"
OPPONENT_USABILITY_SCHEMA_VERSION = "runtime-d0-opponent-move-usability-authority-v1"
_BINDING_KEYS = (
    "session_id", "source_runtime_fingerprint",
    "source_branch_fingerprint", "decision_owner",
)


def freeze_runtime_d0_belch_eligibility_authority(
    *, strategy_d0: Mapping[str, Any], action: Mapping[str, Any],
    actor: Mapping[str, Any], observed_usability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    move_id = action.get("identity") if isinstance(action, Mapping) and action.get("action_type") == "attack" else None
    if move_id is None and isinstance(action, Mapping):
        move_id = action.get("move_id")
    base = {
        "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0.get("session_id") if isinstance(strategy_d0, Mapping) else None,
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint") if isinstance(strategy_d0, Mapping) else None,
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint") if isinstance(strategy_d0, Mapping) else None,
        "decision_owner": deepcopy(strategy_d0.get("decision_owner")) if isinstance(strategy_d0, Mapping) else None,
        "actor": deepcopy(dict(actor)) if isinstance(actor, Mapping) else actor,
        "action_id": action.get("action_id") if isinstance(action, Mapping) else None,
        "move_id": move_id,
    }
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(actor, Mapping):
        return {"status": "rejected", **base, "reason": "invalid_belch_gate_input"}
    if move_id != "belch":
        return {"status": "not_applicable", **base, "reason": "move_not_belch"}
    if action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str) or not action["action_id"].endswith(":belch"):
        return {"status": "rejected", **base, "reason": "belch_action_identity_invalid"}
    if strategy_d0.get("active_owners", {}).get(actor.get("side")) != dict(actor):
        return {"status": "rejected", **base, "reason": "belch_actor_identity_mismatch"}
    if not _action_bound_to_d0(action, strategy_d0):
        return {"status": "rejected", **base, "reason": "belch_action_runtime_d0_binding_mismatch"}

    berry = strategy_d0.get("current_berry_eaten_authority", {}).get(actor["side"])
    if not isinstance(berry, Mapping) or berry.get("owner") != dict(actor):
        return {"status": "rejected", **base, "reason": "belch_berry_eaten_authority_missing"}
    if berry.get("status") == "resolved":
        if berry.get("state") == "known_true":
            return {
                "status": "resolved", **base, "eligibility": "eligible",
                "berry_eaten_authority": deepcopy(dict(berry)),
                "provenance": "persistent_berry_eaten_true_belch_gate_v1",
            }
        if berry.get("state") == "known_false":
            return {
                "status": "resolved", **base, "eligibility": "not_eligible",
                "berry_eaten_authority": deepcopy(dict(berry)),
                "reason": "belch_requires_prior_berry_eaten",
                "provenance": "persistent_berry_eaten_false_belch_gate_v1",
            }
        return {"status": "rejected", **base, "reason": "belch_berry_eaten_state_invalid"}

    if _known_usable_belch_authority(observed_usability, action, actor, strategy_d0):
        return {
            "status": "resolved", **base, "eligibility": "eligible",
            "berry_eaten_authority": deepcopy(dict(berry)),
            "observed_usability_authority": deepcopy(dict(observed_usability)),
            "provenance": "observed_current_belch_usability_gate_v1",
        }
    return {
        "status": "incomplete", **base, "eligibility": "unknown",
        "berry_eaten_authority": deepcopy(dict(berry)),
        "reason": "belch_berry_eaten_state_unknown",
    }


def _action_bound_to_d0(action: Mapping[str, Any], d0: Mapping[str, Any]) -> bool:
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    sources = (
        action,
        action.get("move_metadata_authority"),
        action.get("metadata_authority"),
    )
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        if all(source.get(key) == value for key, value in expected.items()):
            return source.get("move_id", "belch") == "belch"
    return False


def _known_usable_belch_authority(
    value: Any, action: Mapping[str, Any], actor: Mapping[str, Any],
    d0: Mapping[str, Any],
) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != OPPONENT_USABILITY_SCHEMA_VERSION
        or value.get("status") != "resolved"
        or value.get("action_id") != action.get("action_id")
        or value.get("move_id") != "belch"
        or value.get("opponent_actor") != dict(actor)
        or value.get("session_id") != d0.get("session_id")
        or value.get("source_runtime_fingerprint") != d0.get("source_runtime_fingerprint")
        or value.get("source_branch_fingerprint") != d0.get("strategy_preview_fingerprint")
        or value.get("decision_owner") != d0.get("decision_owner")
        or value.get("selectability") != "selectable"
        or value.get("provenance") != "runtime_reducer_current_opponent_move_usability_v1"
    ):
        return False
    usage = value.get("usability")
    provenance = usage.get("provenance") if isinstance(usage, Mapping) else None
    return (
        isinstance(usage, Mapping)
        and usage.get("status") == "known_usable"
        and usage.get("reason") is None
        and isinstance(provenance, Mapping)
        and provenance.get("event_kind") in {
            "current_move_usability_observed",
            "current_opponent_response_set_observed",
        }
        and provenance.get("trust") == "user_confirmed_observation"
        and isinstance(provenance.get("source_sequence"), int)
        and not isinstance(provenance.get("source_sequence"), bool)
        and provenance["source_sequence"] >= 1
    )
