"""Authenticated single-hop detached routing for reflected status actions.

This owner proves only the route.  It does not apply any family mechanic,
create a second selected action, or mutate current runtime state.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_runtime_d0_status_special_application_authority import (
    freeze_runtime_d0_status_special_current_ability_authority,
    validate_runtime_d0_status_special_reflection_authority,
)


SCHEMA_VERSION = "detached-reflected-status-routing-authority-v1"
_DETECTION_SCHEMA = "runtime-d0-status-special-application-authority-v1"
_BINDING = (
    "session_id",
    "source_runtime_fingerprint",
    "source_branch_fingerprint",
    "decision_owner",
)


def freeze_detached_reflected_status_routing_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    original_actor: Mapping[str, Any],
    original_target: Mapping[str, Any],
    reflection_detection_authority: Mapping[str, Any],
    source_route: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze exactly one Magic Bounce route from original target to actor."""
    if source_route is not None:
        if (
            isinstance(source_route, Mapping)
            and source_route.get("schema_version") == SCHEMA_VERSION
            and source_route.get("reflection_consumed") is True
        ):
            return _result("rejected", "reflected_status_route_already_consumed", {})
        return _result("rejected", "reflected_status_source_route_invalid", {})

    base = _base(strategy_d0, action, original_actor, original_target)
    if base is None:
        return _result("rejected", "reflected_status_routing_binding_invalid", {})
    if runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot
    ).get("status") != "current":
        return _result("rejected", "stale_reflected_status_runtime", base)

    detection = reflection_detection_authority
    if not isinstance(detection, Mapping):
        return _result("rejected", "reflection_detection_authority_missing", base)
    detection_validation = validate_runtime_d0_status_special_reflection_authority(detection)
    if detection_validation.get("status") != "resolved":
        return _result("rejected", "reflection_detection_authority_invalid", base)
    detection = detection_validation["authority"]
    if detection.get("schema_version") != _DETECTION_SCHEMA:
        return _result("rejected", "reflection_detection_authority_invalid", base)
    if any(detection.get(key) != base.get(key) for key in (*_BINDING, "actor", "target", "action_id", "move_id")):
        return _result("rejected", "reflection_detection_binding_mismatch", base)
    if detection.get("outcome") != "reflected":
        return _result("rejected", "reflection_detection_not_reflected", base)
    if (
        detection.get("reflection_kind") != "ability"
        or detection.get("reflection_ability_id") != "magic-bounce"
        or detection.get("reflector") != base["target"]
    ):
        return _result("rejected", "magic_bounce_reflection_evidence_invalid", base)

    ability = detection.get("reflector_ability_authority")
    expected_ability = freeze_runtime_d0_status_special_current_ability_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        actor=original_actor,
        target=original_target,
        action_id=base["action_id"],
        move_id=base["move_id"],
    )
    if (
        not isinstance(ability, Mapping)
        or expected_ability.get("status") != "resolved"
        or ability != expected_ability
        or ability.get("ability") != "magic-bounce"
    ):
        return _result("rejected", "magic_bounce_source_authority_invalid", base)

    reflected_source = deepcopy(dict(original_target))
    reflected_target = deepcopy(dict(original_actor))
    authority = {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(base),
        "original_action_id": base["action_id"],
        "original_actor": deepcopy(dict(original_actor)),
        "original_target": deepcopy(dict(original_target)),
        "reflection_kind": "ability",
        "reflection_ability_id": "magic-bounce",
        "reflector": deepcopy(dict(original_target)),
        "reflection_detection_authority": deepcopy(dict(detection)),
        "reflected_source": reflected_source,
        "reflected_target": reflected_target,
        "execution_mode": "reflected_original_action",
        "route_depth": 1,
        "reflection_consumed": True,
        "selected_action_lineage": {
            "selected_action_id": base["action_id"],
            "selected_move_id": base["move_id"],
        },
        "detached_hypothetical": True,
        "provenance": "reflected_status_single_hop_routing_v1",
    }
    authority["validation_request"] = {
        "strategy_d0": deepcopy(strategy_d0),
        "runtime_snapshot": deepcopy(runtime_snapshot),
        "action": deepcopy(action),
        "original_actor": deepcopy(original_actor),
        "original_target": deepcopy(original_target),
        "reflection_detection_authority": deepcopy(reflection_detection_authority),
        "source_route": None,
    }
    return authority


def validate_detached_reflected_status_routing_authority(authority: Any) -> dict[str, Any]:
    """Accept only an exactly reproducible one-hop reflected route."""
    try:
        if (
            not isinstance(authority, Mapping)
            or authority.get("status") != "resolved"
            or authority.get("schema_version") != SCHEMA_VERSION
            or authority.get("route_depth") != 1
            or authority.get("reflection_consumed") is not True
            or authority.get("execution_mode") != "reflected_original_action"
            or authority.get("reflector") != authority.get("original_target")
            or authority.get("reflected_source") != authority.get("original_target")
            or authority.get("reflected_target") != authority.get("original_actor")
            or authority.get("original_action_id") != authority.get("action_id")
            or authority.get("selected_action_lineage")
            != {
                "selected_action_id": authority.get("action_id"),
                "selected_move_id": authority.get("move_id"),
            }
        ):
            raise ValueError()
        request = authority.get("validation_request")
        if not isinstance(request, Mapping):
            raise ValueError()
        expected = freeze_detached_reflected_status_routing_authority(**request)
        if expected != authority:
            raise ValueError()
        return {"status": "resolved", "authority": deepcopy(dict(authority))}
    except (KeyError, TypeError, ValueError):
        return {"status": "rejected", "reason": "reflected_status_routing_provenance_invalid"}


def _base(
    strategy_d0: Any,
    action: Any,
    original_actor: Any,
    original_target: Any,
) -> dict[str, Any] | None:
    if (
        not isinstance(strategy_d0, Mapping)
        or strategy_d0.get("status") != "resolved"
        or not isinstance(action, Mapping)
        or not isinstance(original_actor, Mapping)
        or not isinstance(original_target, Mapping)
    ):
        return None
    active = strategy_d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or active.get(original_actor.get("side")) != dict(original_actor)
        or active.get(original_target.get("side")) != dict(original_target)
        or original_actor.get("side") == original_target.get("side")
    ):
        return None
    action_id = action.get("action_id")
    move_id = action.get("identity", action.get("move_id"))
    metadata_authority = action.get("metadata_authority", action.get("move_metadata_authority"))
    metadata = metadata_authority.get("metadata") if isinstance(metadata_authority, Mapping) else None
    if (
        not isinstance(action_id, str)
        or not action_id
        or not isinstance(move_id, str)
        or not move_id
        or not isinstance(metadata, Mapping)
        or metadata.get("move_id") != move_id
        or metadata.get("category") != "status"
    ):
        return None
    return {
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "actor": deepcopy(dict(original_actor)),
        "target": deepcopy(dict(original_target)),
        "action_id": action_id,
        "move_id": move_id,
    }


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
    }
