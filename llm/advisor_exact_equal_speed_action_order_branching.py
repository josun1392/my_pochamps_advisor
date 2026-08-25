"""Exact detached order branches for a proven equal-Speed tie."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "exact-equal-speed-action-order-branching-v1"
_ORDER_SCHEMA_VERSION = "runtime-d0-action-order-authority-v1"
_BINDING_KEYS = (
    "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
    "decision_owner", "own_action_id", "opponent_action_id", "own_actor",
    "opponent_actor",
)


def materialize_exact_equal_speed_action_order_branches(
    *, action_order_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Branch only an already-resolved narrow-engine equal-Speed tie.

    The returned probabilities are mechanical order probabilities, conditional
    on the two selected actions; they never model opponent action selection.
    """
    if not isinstance(action_order_authority, Mapping):
        return _result("rejected", "action_order_authority_invalid", {})
    base = {key: deepcopy(action_order_authority.get(key)) for key in _BINDING_KEYS}
    if action_order_authority.get("schema_version") != _ORDER_SCHEMA_VERSION:
        return _result("rejected", "action_order_authority_invalid", base)
    if any(not _binding_present(key, base.get(key)) for key in _BINDING_KEYS):
        return _result("rejected", "action_order_binding_incomplete", base)
    if action_order_authority.get("status") != "resolved":
        return _result(_status(action_order_authority), action_order_authority.get("reason", "action_order_unavailable"), base)
    if action_order_authority.get("order") != "unresolved_tie":
        return _result("incomplete", "action_order_is_not_equal_speed_tie", base)
    engine = action_order_authority.get("order_engine")
    if not isinstance(engine, Mapping) or engine.get("status") != "speed_tie":
        return _result("rejected", "unresolved_tie_not_mechanically_established", base)
    branches = (
        _branch("own_first"),
        _branch("opponent_first"),
    )
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **base,
        "source_action_order_authority": deepcopy(dict(action_order_authority)),
        "order_branches": branches,
        "probability_semantics": "mechanical_equal_speed_order_conditional_on_selected_actions",
        "opponent_action_selection_probability": "not_modeled",
        "ranking_influence": "none",
    }


def _branch(order: str) -> dict[str, Any]:
    return {
        "order_branch_id": f"equal_speed:{order}",
        "order": order,
        "conditional_probability": {"numerator": 1, "denominator": 2},
    }


def _binding_present(key: str, value: Any) -> bool:
    if key in {"session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "own_action_id", "opponent_action_id"}:
        return isinstance(value, str) and bool(value)
    return isinstance(value, Mapping) and bool(value)


def _status(value: Mapping[str, Any]) -> str:
    return value.get("status") if value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
