"""Detached pair-local Payback power evidence from a completed target action."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_target_already_acted_power_family import resolve_canonical_target_already_acted_power_move

SCHEMA_VERSION = "detached-target-already-acted-power-authority-v1"
_EXECUTED_ACTION_TYPES = frozenset({"attack", "protection", "status", "status_protection"})

def materialize_detached_target_already_acted_power_authority(*, strategy_d0: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], target: Mapping[str, Any], source_terminal_leaf: Mapping[str, Any] | None = None, source_selected_action: Mapping[str, Any] | None = None, execution_order_provenance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    canonical = resolve_canonical_target_already_acted_power_move(move=move)
    if canonical.get("status") != "resolved": return _bad(canonical.get("status", "rejected"), canonical.get("reason", "catalog_unavailable"))
    bindings = _bindings(strategy_d0, move, user, target)
    if isinstance(bindings, str): return _bad("rejected", bindings)
    if source_terminal_leaf is None: return _resolved(canonical, bindings, None, execution_order_provenance)
    action = _completed_target_action(source_terminal_leaf, source_selected_action, target)
    if isinstance(action, str): return _bad("rejected", action)
    return _resolved(canonical, bindings, action, execution_order_provenance)

def _bindings(d0: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | str:
    if not all(isinstance(value, Mapping) for value in (d0, move, user, target)): return "target_already_acted_power_request_invalid"
    if not all(isinstance(d0.get(key), str) and d0.get(key) for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return "target_already_acted_power_d0_provenance_missing"
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(user.get("side")) != user or active.get(target.get("side")) != target or user == target: return "target_already_acted_power_active_identity_mismatch"
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "user": deepcopy(dict(user)), "target": deepcopy(dict(target)), "move_id": move.get("move_id")}

def _completed_target_action(leaf: Mapping[str, Any], selected: Mapping[str, Any] | None, target: Mapping[str, Any]) -> dict[str, Any] | None | str:
    if not isinstance(leaf, Mapping) or leaf.get("action_type") not in _EXECUTED_ACTION_TYPES or not isinstance(leaf.get("leaf_id"), str): return "target_already_acted_source_leaf_invalid"
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("attacker") != target: return None
    execution_move = provenance.get("move_id") or leaf.get("move_id"); action_id = leaf.get("candidate_id")
    if not isinstance(execution_move, str) or not execution_move or not isinstance(action_id, str) or not action_id: return "target_already_acted_execution_identity_missing"
    selected_id = selected.get("action_id") if isinstance(selected, Mapping) else action_id
    selected_move = (selected.get("identity") or selected.get("move_id")) if isinstance(selected, Mapping) else execution_move
    if not isinstance(selected_id, str) or not isinstance(selected_move, str): return "target_already_acted_selected_identity_invalid"
    return {"pair_branch_source_leaf_id": leaf["leaf_id"], "source_action_id": action_id, "source_selected_action_id": selected_id, "source_selected_move_id": selected_move, "source_execution_move_id": execution_move, "source_action_type": leaf["action_type"], "source_action_result": "executed" if leaf.get("hit_state") != "not_applicable" else "executed_non_damaging", "event_order": "before_payback_execution", "source_leaf_provenance": deepcopy(dict(provenance))}

def _resolved(canonical: Mapping[str, Any], bindings: Mapping[str, Any], action: Mapping[str, Any] | None, order: Mapping[str, Any] | None) -> dict[str, Any]:
    effect = canonical["effect"]; condition = isinstance(action, Mapping)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(bindings)), "trigger_family": "target_already_acted", "canonical_base_power": effect["power"], "target_already_acted_before_execution": condition, "selected_base_power": effect["boosted_power"] if condition else effect["power"], "qualifying_target_action": deepcopy(dict(action)) if condition else None, "execution_order_provenance": deepcopy(dict(order)) if isinstance(order, Mapping) else None, "rule": deepcopy(dict(effect)), "provenance": "exact_d0_pair_branch_target_already_acted_before_execution_v1"}

def _bad(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
