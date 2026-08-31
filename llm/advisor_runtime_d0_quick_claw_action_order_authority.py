"""Strict D0-bound Quick Claw applicability for one already-resolved action pair."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-quick-claw-action-order-authority-v1"
_BINDINGS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")


def freeze_runtime_d0_quick_claw_action_order_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze only this pair's current held-item Quick Claw order plan.

    The supplied action-order authority remains the sole source of effective
    priority and non-activation Speed/order semantics.
    """
    base = _base(strategy_d0, own_action, opponent_action)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    order = _order(action_order_authority, base, own_action, opponent_action)
    if isinstance(order, tuple):
        return _result(*order, base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    own_item = _item_authority(_pokemon(state, base["own_actor"]), base["own_actor"])
    opponent_item = _item_authority(_pokemon(state, base["opponent_actor"]), base["opponent_actor"])
    common = {**base, "source_action_order_authority": deepcopy(dict(action_order_authority)), "current_held_item_authorities": {"own": own_item, "opponent": opponent_item}}
    if own_item["status"] != "known" or opponent_item["status"] != "known":
        return _result("incomplete", "quick_claw_current_held_item_authority_missing", common)
    own_quick, opponent_quick = own_item["item_id"] == "quick-claw", opponent_item["item_id"] == "quick-claw"
    if own_quick and opponent_quick:
        return _result("unsupported", "simultaneous_quick_claw_trigger_precedence_unowned", common)
    if not own_quick and not opponent_quick:
        return {"status": "resolved", "schema_version": SCHEMA_VERSION, **common, "outcome": "known_no_effect", "reason": "current_known_items_are_not_quick_claw", "provenance": "runtime_d0_current_held_item_quick_claw_plan_v1"}
    holder_side = "self" if own_quick else "opponent"
    holder = base["own_actor"] if own_quick else base["opponent_actor"]
    holder_action = own_action if own_quick else opponent_action
    priorities = order["order_engine"]
    if priorities["self_priority"] != priorities["opponent_priority"]:
        return {"status": "resolved", "schema_version": SCHEMA_VERSION, **common, "outcome": "known_no_effect", "reason": "quick_claw_cannot_cross_strict_effective_priority_bracket", "holder": deepcopy(dict(holder)), "holder_side": holder_side, "holder_action_id": holder_action["action_id"], "holder_move_id": _move_id(holder_action, holder_side), "effective_priority": {"own": priorities["self_priority"], "opponent": priorities["opponent_priority"]}, "provenance": "runtime_d0_current_held_item_quick_claw_plan_v1"}
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **common, "outcome": "applicable", "holder": deepcopy(dict(holder)), "holder_side": holder_side, "holder_action_id": holder_action["action_id"], "holder_move_id": _move_id(holder_action, holder_side), "effective_priority": {"own": priorities["self_priority"], "opponent": priorities["opponent_priority"]}, "activation_probability": {"numerator": 1, "denominator": 5}, "non_activation_probability": {"numerator": 4, "denominator": 5}, "non_activation_order": order["order"], "provenance": "runtime_d0_current_held_item_quick_claw_plan_v1"}


def _order(value: Any, base: Mapping[str, Any], own: Mapping[str, Any], opponent: Mapping[str, Any]) -> dict[str, Any] | tuple[str, str]:
    if not isinstance(value, Mapping) or value.get("schema_version") != "runtime-d0-action-order-authority-v1":
        return ("rejected", "quick_claw_source_action_order_authority_invalid")
    if any(value.get(key) != base.get(key) for key in _BINDINGS):
        return ("rejected", "quick_claw_source_action_order_authority_binding_mismatch")
    if value.get("status") != "resolved":
        return (_status(value), value.get("reason", "quick_claw_source_action_order_unavailable"))
    if value.get("own_action_id") != own.get("action_id") or value.get("opponent_action_id") != opponent.get("action_id"):
        return ("rejected", "quick_claw_action_identity_mismatch")
    engine = value.get("order_engine")
    if value.get("order") not in {"own_first", "opponent_first", "unresolved_tie"} or not isinstance(engine, Mapping):
        return ("rejected", "quick_claw_source_action_order_result_invalid")
    if any(not isinstance(engine.get(key), int) or isinstance(engine.get(key), bool) for key in ("self_priority", "opponent_priority")):
        return ("rejected", "quick_claw_effective_priority_missing")
    return {"order": value["order"], "order_engine": engine}


def _item_authority(pokemon: Any, owner: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(pokemon, Mapping):
        return {"status": "invalid", "owner": deepcopy(dict(owner)), "reason": "current_owner_item_identity_missing"}
    value, provenance = pokemon.get("known_item"), pokemon.get("known_item_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") not in {"current_item_observed", "item_consumption_observed", "item_removed_observed"} or provenance.get("trust") != "user_confirmed_observation":
        return {"status": "unknown", "owner": deepcopy(dict(owner)), "reason": "current_held_item_authority_unknown"}
    if value is not None and (not isinstance(value, str) or not value):
        return {"status": "invalid", "owner": deepcopy(dict(owner)), "reason": "current_held_item_authority_malformed"}
    return {"status": "known", "owner": deepcopy(dict(owner)), "item_id": value, "source_provenance": deepcopy(dict(provenance))}


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return value if isinstance(value, Mapping) and value.get("pokemon_id") == owner.get("pokemon_id") else None


def _move_id(action: Mapping[str, Any], side: str) -> Any:
    return action.get("identity") if side == "self" else action.get("move_id")


def _base(d0: Any, own_action: Any, opponent_action: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(own_action, Mapping) or not isinstance(opponent_action, Mapping): return None
    own, opponent = d0.get("active_owners", {}).get("self"), d0.get("active_owners", {}).get("opponent")
    if not isinstance(own, Mapping) or not isinstance(opponent, Mapping) or d0.get("decision_owner") != own: return None
    if not isinstance(own_action.get("action_id"), str) or not isinstance(opponent_action.get("action_id"), str): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(own)), "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"], "own_actor": deepcopy(dict(own)), "opponent_actor": deepcopy(dict(opponent))}


def _status(value: Mapping[str, Any]) -> str:
    return value.get("status") if value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
