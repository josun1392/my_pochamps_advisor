"""D0-bound, branch-local authority for Gen 9 Analytic.

This adapter intentionally consumes an already materialized immediate-pair
order.  It never looks at speeds, priorities, field effects, or RNG itself.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "runtime-d0-analytic-action-order-authority-v1"


def freeze_runtime_d0_analytic_action_order_authority(
    *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any],
    own_action_id: str, opponent_action_id: str, action_order: str,
    source_action_order_authority: Mapping[str, Any] | None = None,
    action_order_branch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze the exact already-selected immediate action-order branch.

    ``opponent_first`` is the only move-vs-move outcome that can enable
    Analytic.  The switch owner passes ``opponent_switch_first`` explicitly.
    The consumer still checks all D0 and actor bindings before using this.
    """
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved":
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    if not _owner(attacker) or not _owner(target) or not isinstance(own_action_id, str) or not isinstance(opponent_action_id, str):
        return _result("rejected", "analytic_action_order_identity_invalid", {})
    if attacker != strategy_d0.get("decision_owner") or target != strategy_d0.get("active_owners", {}).get("opponent"):
        return _result("rejected", "analytic_action_order_identity_mismatch", {})
    if action_order not in {"own_first", "opponent_first", "opponent_switch_first"}:
        return _result("rejected", "analytic_action_order_invalid", {})
    base = {
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)),
        "own_action_id": own_action_id, "opponent_action_id": opponent_action_id,
    }
    if action_order == "opponent_switch_first":
        if source_action_order_authority is not None or action_order_branch is not None:
            return _result("rejected", "analytic_switch_order_provenance_invalid", base)
    else:
        source = source_action_order_authority
        if not isinstance(source, Mapping) or source.get("schema_version") != "runtime-d0-action-order-authority-v1" or source.get("status") != "resolved":
            return _result("rejected", "analytic_source_action_order_authority_invalid", base)
        # A second action runs under a detached intermediate D0.  Its D0
        # fingerprint legitimately differs from the root order authority, but
        # action identities and actors must remain exact.
        expected = {"own_action_id": own_action_id, "opponent_action_id": opponent_action_id,
                    "own_actor": attacker, "opponent_actor": target}
        if any(source.get(key) != value for key, value in expected.items()):
            return _result("rejected", "analytic_source_action_order_binding_mismatch", base)
        source_order = source.get("order")
        if source_order in {"own_first", "opponent_first"}:
            if source_order != action_order or action_order_branch is not None:
                return _result("rejected", "analytic_source_action_order_branch_mismatch", base)
        elif source_order == "unresolved_tie":
            if not _tie_branch(action_order_branch, action_order):
                return _result("rejected", "analytic_tie_order_branch_invalid", base)
        else:
            # Quick Claw materialization likewise supplies an exact branch.
            if not _branch(action_order_branch, action_order):
                return _result("rejected", "analytic_source_action_order_branch_invalid", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "action_order": action_order,
        "outcome": "applicable" if action_order in {"opponent_first", "opponent_switch_first"} else "not_applicable",
        "source_action_order_authority": deepcopy(dict(source_action_order_authority)) if isinstance(source_action_order_authority, Mapping) else None,
        "action_order_branch": deepcopy(dict(action_order_branch)) if isinstance(action_order_branch, Mapping) else None,
        "provenance": "exact_immediate_action_order_branch_v1",
    }


def valid_runtime_d0_analytic_action_order_authority(
    value: Any, *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move_id: str,
) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("status") != "resolved":
        return False
    expected = {
        "session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "decision_owner": strategy_d0.get("decision_owner"),
        "attacker": attacker, "target": target,
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        return False
    if not isinstance(value.get("own_action_id"), str) or value.get("own_action_id") not in {move_id, f"attack:{move_id}"}:
        return False
    order = value.get("action_order")
    return order in {"own_first", "opponent_first", "opponent_switch_first"} and value.get("outcome") == ("applicable" if order in {"opponent_first", "opponent_switch_first"} else "not_applicable")


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and isinstance(value.get("pokemon_id"), str)


def _tie_branch(value: Any, order: str) -> bool:
    return _branch(value, order) and value.get("order_branch_id") in {"equal_speed:own_first", "equal_speed:opponent_first"}


def _branch(value: Any, order: str) -> bool:
    probability = value.get("conditional_probability") if isinstance(value, Mapping) else None
    return isinstance(value, Mapping) and value.get("order") == order and isinstance(value.get("order_branch_id"), str) and isinstance(probability, Mapping) and probability.get("numerator") in {1, 2, 3, 4} and probability.get("denominator") in {2, 5}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
