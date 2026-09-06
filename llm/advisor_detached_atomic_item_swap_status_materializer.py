"""Immutable detached projection for an exact atomic item-swap authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_atomic_item_swap_status_execution_authority import SCHEMA_VERSION as AUTHORITY_SCHEMA

SCHEMA_VERSION = "detached-atomic-item-swap-status-materialization-v1"


def materialize_detached_atomic_item_swap_status(*, execution_authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(execution_authority, Mapping) or execution_authority.get("schema_version") != AUTHORITY_SCHEMA:
        return _result("rejected", "atomic_item_swap_execution_authority_invalid", {})
    base = _base(execution_authority)
    if base is None: return _result("rejected", "atomic_item_swap_execution_authority_binding_invalid", {})
    if execution_authority.get("status") != "resolved": return _result(execution_authority.get("status", "incomplete"), execution_authority.get("reason", "atomic_item_swap_authority_unavailable"), base)
    before_a, before_t = execution_authority.get("actor_item_before"), execution_authority.get("target_item_before")
    if not _before(before_a) or not _before(before_t): return _result("rejected", "atomic_item_swap_before_state_invalid", base)
    outcome = execution_authority.get("outcome")
    success = outcome == "executed_swap"
    expected_a, expected_t = (before_t, before_a) if success else (before_a, before_t)
    after_a, after_t = execution_authority.get("actor_item_after", expected_a), execution_authority.get("target_item_after", expected_t)
    if after_a != expected_a or after_t != expected_t: return _result("rejected", "atomic_item_swap_after_state_forged", base)
    if outcome not in {"executed_swap", "failed_both_no_item", "failed_item_restriction", "blocked_sticky_hold", "blocked_protection"}: return _result("rejected", "atomic_item_swap_outcome_invalid", base)
    transition = {"outcome": outcome, "actor": deepcopy(base["actor"]), "target": deepcopy(base["target"]), "actor_item_before": deepcopy(before_a), "target_item_before": deepcopy(before_t), "actor_item_after": deepcopy(after_a), "target_item_after": deepcopy(after_t), "authority": deepcopy(dict(execution_authority))}
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": outcome,
            "probability": {"numerator": 1, "denominator": 1}, "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "damage": "not_applicable",
            "item_transition": transition, "consequences": {"atomic_item_swap_status": deepcopy(transition)}, "provenance": "strict_detached_atomic_item_swap_status_materialization_v1"}


def _before(value: Any) -> bool: return isinstance(value, Mapping) and value.get("state") in {"known_present", "known_absent"} and ((value.get("state") == "known_present" and isinstance(value.get("item"), str) and value["item"]) or (value.get("state") == "known_absent" and value.get("item") is None))
def _base(value: Mapping[str, Any]) -> dict[str, Any] | None:
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "target", "action_id", "selected_move_id", "execution_move_id", "move_id", "move_family")
    if not all(key in value for key in keys) or value.get("move_family") != "atomic_item_swap_status" or value.get("selected_move_id") != value.get("execution_move_id") or value.get("move_id") != value.get("execution_move_id") or not all(isinstance(value.get(k), Mapping) for k in ("decision_owner", "actor", "target")): return None
    return {key: deepcopy(value[key]) for key in keys}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
