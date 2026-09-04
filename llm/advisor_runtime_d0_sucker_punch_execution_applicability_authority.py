"""Exact selected-action gate for Sucker Punch's conditional execution."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "runtime-d0-sucker-punch-execution-applicability-authority-v1"
_OWNER = ("session_id", "side", "slot_index", "pokemon_id")
_BASE = {"move_id": "sucker-punch", "category": "physical", "power": 70, "type": "dark", "accuracy": 100, "priority": 1}


def freeze_runtime_d0_sucker_punch_execution_applicability_authority(*, strategy_d0: Mapping[str, Any], own_action: Mapping[str, Any], own_move_metadata_authority: Mapping[str, Any], target_action: Mapping[str, Any], target_move_metadata_authority: Mapping[str, Any] | None, action_order_authority: Mapping[str, Any] | None, order: str, action_order_branch: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Decide only whether the selected Sucker Punch may enter attack execution.

    ``order`` is a materialized existing action-order branch.  The target is
    already acted exactly when that branch places the own Sucker Punch second.
    No accuracy, damage, contact, or target-effectiveness mechanics are owned
    here.
    """
    base = _base(strategy_d0, own_action, own_move_metadata_authority, target_action, action_order_authority, order, action_order_branch)
    if isinstance(base, str):
        return _result("rejected", base)
    target = _target(target_action, target_move_metadata_authority, base)
    if isinstance(target, str):
        return _result("rejected", target, base)
    already_acted = order == "opponent_first"
    common = {**base, "target_selected_action_id": target["action_id"], "target_selected_action_kind": target["kind"], "target_selected_move_metadata": deepcopy(target.get("metadata")), "target_selected_move_category": target.get("category"), "target_already_acted": already_acted}
    if target["kind"] != "attack" or target["category"] not in {"physical", "special"}:
        return _result("not_applicable", "sucker_punch_target_not_readying_attack", common)
    if already_acted:
        return _result("not_applicable", "sucker_punch_target_already_acted", common)
    return {"status": "applies", "schema_version": SCHEMA_VERSION, **common, "provenance": "exact_selected_damaging_target_action_and_order_branch_v1"}


def _base(d0: Any, own: Any, own_meta: Any, target: Any, order_auth: Any, order: Any, order_branch: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(d0.get("decision_owner")):
        return "runtime_d0_invalid"
    actor = d0["decision_owner"]
    target_owner = d0.get("active_owners", {}).get("opponent")
    if not _owner(target_owner) or not isinstance(own, Mapping) or own.get("action_id") != "attack:sucker-punch" or own.get("action_type") != "attack":
        return "sucker_punch_action_identity_invalid"
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": actor}
    meta = own_meta.get("metadata") if isinstance(own_meta, Mapping) else None
    if own_meta.get("status") != "resolved" or any(own_meta.get(k) != v for k, v in expected.items()) or not isinstance(meta, Mapping) or any(meta.get(k) != v for k, v in _BASE.items()):
        return "canonical_sucker_punch_metadata_binding_invalid"
    if not isinstance(target, Mapping) or not isinstance(target.get("action_id"), str) or order not in {"own_first", "opponent_first"}:
        return "target_action_or_order_missing"
    required = {**expected, "own_action_id": own["action_id"], "opponent_action_id": target["action_id"], "own_actor": actor, "opponent_actor": target_owner}
    if target.get("action_type") == "manual_switch" and order == "opponent_first" and order_auth is None:
        order_source = {"kind": "opponent_selected_switch_response", "order": "opponent_first"}
    elif isinstance(order_auth, Mapping) and order_auth.get("schema_version") == "runtime-d0-action-order-authority-v1" and all(order_auth.get(k) == v for k, v in required.items()):
        if order_auth.get("order") == order:
            order_source = deepcopy(dict(order_auth))
        elif isinstance(order_branch, Mapping) and order_branch.get("order") == order and isinstance(order_branch.get("order_branch_id"), str) and all(order_branch.get(k) == v for k, v in required.items()):
            order_source = {"authority": deepcopy(dict(order_auth)), "branch": deepcopy(dict(order_branch))}
        else:
            return "action_order_branch_binding_mismatch"
    else:
        return "action_order_binding_mismatch"
    return {**expected, "sucker_punch_actor": deepcopy(dict(actor)), "target": deepcopy(dict(target_owner)), "own_action_id": own["action_id"], "move_id": "sucker-punch", "canonical_move_metadata": deepcopy(dict(meta)), "action_order": order, "action_order_authority": order_source}


def _target(action: Mapping[str, Any], metadata_authority: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    kind = action.get("action_type")
    if kind == "manual_switch":
        return {"action_id": action["action_id"], "kind": "manual_switch", "metadata": None, "category": None}
    metadata = metadata_authority.get("metadata") if isinstance(metadata_authority, Mapping) else None
    if kind not in {"attack", "status"} or not isinstance(metadata, Mapping):
        return "target_selected_action_kind_or_metadata_invalid"
    expected = {key: base[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    if metadata_authority.get("status") != "resolved" or any(metadata_authority.get(k) != v for k, v in expected.items()) or metadata.get("move_id") != action.get("move_id"):
        return "target_selected_move_metadata_binding_mismatch"
    category = metadata.get("category")
    if category not in {"physical", "special", "status"}:
        return "target_selected_move_category_invalid"
    if kind == "attack" and category == "status":
        kind = "status"
    if kind == "status" and category != "status":
        return "target_selected_action_category_mismatch"
    return {"action_id": action["action_id"], "kind": kind, "metadata": deepcopy(dict(metadata)), "category": category}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and isinstance(value.get("pokemon_id"), str)


def _result(status: str, reason: str, base: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **(deepcopy(dict(base)) if isinstance(base, Mapping) else {}), "reason": reason}
