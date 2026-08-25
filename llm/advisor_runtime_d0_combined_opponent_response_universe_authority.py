"""Strict D0-bound union of complete opponent move and switch responses.

This is an authority boundary only.  It does not attach likelihoods or execute
responses.  In particular, a complete moveset whose four moves are all known
unusable is *complete zero selectable-move evidence*, not missing knowledge.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_complete_opponent_response_set_authority import (
    SCHEMA_VERSION as MOVE_RESPONSE_SET_SCHEMA_VERSION,
)
from llm.advisor_runtime_d0_opponent_action_authority import (
    SCHEMA_VERSION as OPPONENT_ACTION_SCHEMA_VERSION,
)
from llm.advisor_runtime_d0_opponent_switch_response_authority import (
    SCHEMA_VERSION as SWITCH_RESPONSE_SET_SCHEMA_VERSION,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-combined-opponent-response-universe-authority-v1"
_STATUSES = frozenset({"incomplete", "unsupported", "rejected"})


def freeze_runtime_d0_combined_opponent_response_universe_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    move_response_authority: Mapping[str, Any],
    switch_response_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the complete current response universe without inferring gaps."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_d0", {})
    freshness = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)

    moves = _move_dimension(move_response_authority, base)
    switches = _switch_dimension(switch_response_authority, base)
    for dimension in (moves, switches):
        if dimension["status"] in _STATUSES:
            return _result(
                dimension["status"], dimension["reason"], base,
                move_dimension_status=moves["status"],
                switch_dimension_status=switches["status"],
            )

    actions = tuple(moves["actions"] + switches["actions"])
    action_ids = tuple(action["action_id"] for action in actions)
    if len(set(action_ids)) != len(action_ids):
        return _result("rejected", "combined_response_action_id_collision", base)
    selectable = tuple(action["action_id"] for action in actions if action["selectability"] == "selectable")
    universe_state = (
        "complete_with_selectable_responses"
        if selectable
        else "complete_zero_response_universe"
    )
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **base,
        "universe_state": universe_state,
        "move_dimension": _dimension_output(moves),
        "switch_dimension": _dimension_output(switches),
        "source_move_response_authority": deepcopy(dict(move_response_authority)),
        "source_switch_response_authority": deepcopy(dict(switch_response_authority)),
        "response_action_ids": action_ids,
        "selectable_response_action_ids": selectable,
        "actions": deepcopy(actions),
        "response_probability": "not_modeled",
        "provenance": "runtime_d0_complete_combined_opponent_response_universe_v1",
    }


def _move_dimension(value: Any, base: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != MOVE_RESPONSE_SET_SCHEMA_VERSION:
        return _dimension("rejected", "invalid_move_response_authority")
    if not _matches(value, base, ("opponent_actor", "target_owner")):
        return _dimension("rejected", "move_response_authority_binding_mismatch")
    status = value.get("status")
    if status == "resolved":
        if value.get("moveset_completeness") != "complete":
            return _dimension("rejected", "move_response_authority_completeness_invalid")
        actions = _move_actions(value.get("actions"), base)
        if actions is None:
            return _dimension("rejected", "move_response_actions_invalid")
        selectable = _selected_ids(value.get("selectable_response_action_ids"), actions)
        if selectable is None:
            return _dimension("rejected", "move_response_selectable_ids_invalid")
        return _dimension("resolved", None, actions, selectable, value.get("response_set_provenance"))
    # The existing move-only authority intentionally reports this situation as
    # incomplete because it cannot itself form a usable move response profile.
    # Its composed, all-not-selectable known actions are nevertheless exact
    # evidence that this dimension is complete for the combined universe.
    if status == "incomplete" and value.get("reason") == "no_currently_selectable_opponent_response":
        actions = _move_actions(value.get("known_actions"), base)
        if actions is None or any(action["selectability"] != "not_selectable" for action in actions):
            return _dimension("rejected", "move_response_zero_selectable_seam_invalid")
        return _dimension(
            "resolved", None, actions, (),
            {"source_status": "incomplete", "source_reason": value["reason"]},
        )
    return _dimension(_unavailable_status(status), value.get("reason", "move_response_authority_unavailable"))


def _switch_dimension(value: Any, base: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != SWITCH_RESPONSE_SET_SCHEMA_VERSION:
        return _dimension("rejected", "invalid_switch_response_authority")
    if not _matches(value, base, ("own_actor", "opponent_actor")):
        return _dimension("rejected", "switch_response_authority_binding_mismatch")
    status = value.get("status")
    if status != "resolved":
        return _dimension(_unavailable_status(status), value.get("reason", "switch_response_authority_unavailable"))
    if value.get("target_set_completeness") != "complete" or value.get("switch_permission") not in {"permitted", "blocked"}:
        return _dimension("rejected", "switch_response_authority_completeness_invalid")
    actions = _switch_actions(value.get("actions"), base)
    if actions is None:
        return _dimension("rejected", "switch_response_actions_invalid")
    selectable = _selected_ids(value.get("selectable_response_action_ids"), actions)
    if selectable is None:
        return _dimension("rejected", "switch_response_selectable_ids_invalid")
    return _dimension("resolved", None, actions, selectable, value.get("response_set_provenance"))


def _move_actions(value: Any, base: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | None:
    if not isinstance(value, (tuple, list)) or not value:
        return None
    actions = []
    for action in value:
        if not isinstance(action, Mapping) or action.get("schema_version") != OPPONENT_ACTION_SCHEMA_VERSION:
            return None
        if action.get("status") != "resolved" or action.get("action_type") != "attack" or action.get("acting_side") != "opponent" or action.get("target_side") != "self":
            return None
        if action.get("selectability") not in {"selectable", "not_selectable"} or not isinstance(action.get("action_id"), str):
            return None
        if not _matches(action, base, ("opponent_actor", "target_owner")):
            return None
        actions.append(_with_kind(action, "move"))
    return tuple(actions) if len({action["action_id"] for action in actions}) == len(actions) else None


def _switch_actions(value: Any, base: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | None:
    if not isinstance(value, (tuple, list)):
        return None
    actions = []
    for action in value:
        if not isinstance(action, Mapping) or action.get("action_type") != "manual_switch":
            return None
        if action.get("acting_side") != "opponent" or action.get("target_side") != "self" or action.get("selectability") not in {"selectable", "not_selectable"}:
            return None
        if action.get("availability") not in {"alive", "fainted"} or not isinstance(action.get("action_id"), str):
            return None
        target = action.get("target_owner")
        if not isinstance(target, Mapping) or target.get("session_id") != base["session_id"] or target.get("side") != "opponent":
            return None
        actions.append(_with_kind(action, "switch"))
    return tuple(actions) if len({action["action_id"] for action in actions}) == len(actions) else None


def _selected_ids(value: Any, actions: tuple[dict[str, Any], ...]) -> tuple[str, ...] | None:
    if not isinstance(value, (tuple, list)) or any(not isinstance(item, str) for item in value):
        return None
    selected = tuple(value)
    expected = tuple(action["action_id"] for action in actions if action["selectability"] == "selectable")
    return selected if selected == expected else None


def _matches(value: Mapping[str, Any], base: Mapping[str, Any], owners: tuple[str, ...]) -> bool:
    fields = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", *owners)
    return all(value.get(field) == base.get(field) for field in fields)


def _with_kind(value: Mapping[str, Any], kind: str) -> dict[str, Any]:
    action = deepcopy(dict(value))
    action["response_kind"] = kind
    return action


def _dimension(status: str, reason: str | None, actions: tuple[dict[str, Any], ...] = (), selectable: tuple[str, ...] = (), provenance: Any = None) -> dict[str, Any]:
    return {"status": status, "reason": reason, "actions": actions, "selectable_response_action_ids": selectable, "provenance": deepcopy(provenance)}


def _dimension_output(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(value[key]) for key in ("status", "actions", "selectable_response_action_ids", "provenance")}


def _unavailable_status(value: Any) -> str:
    return value if value in _STATUSES else "rejected"


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return None
    owners = d0.get("active_owners")
    own = owners.get("self") if isinstance(owners, Mapping) else None
    opponent = owners.get("opponent") if isinstance(owners, Mapping) else None
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner")
    if not isinstance(own, Mapping) or not isinstance(opponent, Mapping) or any(key not in d0 for key in required):
        return None
    return {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "own_actor": deepcopy(own),
        "opponent_actor": deepcopy(opponent),
        "target_owner": deepcopy(own),
    }


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
