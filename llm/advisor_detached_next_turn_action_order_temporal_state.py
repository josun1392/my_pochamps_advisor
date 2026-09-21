"""Authenticated EOT carry for bounded next-turn action-order facts.

Only explicitly observed inactive Tailwind and Trick Room facts cross this
boundary.  Active effects require expiry authority and unknown facts remain
incomplete; this owner never turns absence into a fact.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "detached-next-turn-action-order-temporal-state-authority-v1"
SOURCE_SCHEMA_VERSION = "detached-action-order-temporal-source-authority-v1"
_CHARGE_MOVES = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade", "meteor-beam", "skull-bash"})


def freeze_detached_action_order_temporal_source_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any], action_order_authority: Mapping[str, Any], evaluated_pair: Mapping[str, Any], source_move_ids: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze one D0's trusted inactive order facts before EOT projection."""
    from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority

    expected = freeze_runtime_d0_action_order_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own_action, opponent_action=opponent_action)
    if expected != action_order_authority:
        return _source("rejected", "turn_one_action_order_authority_mismatch")
    moves = {"self": own_action.get("identity"), "opponent": opponent_action.get("move_id")}
    if not isinstance(source_move_ids, Mapping) or dict(source_move_ids) != moves:
        return _source("rejected", "action_order_temporal_source_move_identity_mismatch")
    if not _owned_move_pair(moves):
        return _source("unsupported", "action_order_temporal_source_move_family_unowned")
    owners = strategy_d0.get("active_owners", {})
    branch = strategy_d0.get("strategy_preview_fingerprint")
    expected_pair = {
        "session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": branch, "decision_owner": strategy_d0.get("decision_owner"),
        "own_action_id": own_action.get("action_id"), "opponent_action_id": opponent_action.get("action_id"),
        "own_actor": owners.get("self"), "opponent_actor": owners.get("opponent"),
    }
    if not isinstance(evaluated_pair, Mapping) or evaluated_pair.get("status") != "evaluable" or not isinstance(evaluated_pair.get("pair_id"), str) or not evaluated_pair["pair_id"] or evaluated_pair.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1} or any(evaluated_pair.get(key) != value for key, value in expected_pair.items()):
        return _source("rejected", "action_order_temporal_source_pair_binding_invalid")
    facts = action_order_authority.get("order_input_authority", {})
    values: dict[str, dict[str, str]] = {}
    for name, reason in (("self_tailwind", "next_turn_tailwind_expiry_authority_unavailable"), ("opponent_tailwind", "next_turn_tailwind_expiry_authority_unavailable"), ("trick_room", "next_turn_trick_room_expiry_authority_unavailable")):
        value = facts.get(name)
        if value == "active":
            return _source("incomplete", reason)
        if value != "inactive":
            return _source("incomplete", f"{name}_source_authority_unknown")
        values[name] = {"status": "resolved", "state": "inactive", "source_state": "inactive", "carry_decision": "exact_inactive_no_supported_turn_one_mutator"}
    return {"status": "resolved", "schema_version": SOURCE_SCHEMA_VERSION, **expected_pair, "pair_id": evaluated_pair["pair_id"], "source_move_ids": deepcopy(moves), "source_action_order_authority": deepcopy(dict(action_order_authority)), "temporal_facts": values, "validation_request": {"strategy_d0": deepcopy(dict(strategy_d0)), "runtime_snapshot": deepcopy(dict(runtime_snapshot)), "own_action": deepcopy(dict(own_action)), "opponent_action": deepcopy(dict(opponent_action)), "action_order_authority": deepcopy(dict(action_order_authority)), "evaluated_pair": deepcopy(dict(evaluated_pair)), "source_move_ids": deepcopy(moves)}, "provenance": "authenticated_turn_one_inactive_action_order_temporal_source_v1"}


def validate_detached_action_order_temporal_source_authority(*, authority: Any, **request: Any) -> str | None:
    required = ("strategy_d0", "runtime_snapshot", "own_action", "opponent_action", "action_order_authority", "evaluated_pair", "source_move_ids")
    supplied = request or (authority.get("validation_request", {}) if isinstance(authority, Mapping) else {})
    if not isinstance(authority, Mapping) or not isinstance(supplied, Mapping) or any(key not in supplied for key in required):
        return "action_order_temporal_source_authority_invalid"
    expected = freeze_detached_action_order_temporal_source_authority(**{key: supplied[key] for key in required})
    return None if deepcopy(dict(authority)) == expected else "action_order_temporal_source_authority_mismatch"


def materialize_detached_next_turn_action_order_temporal_state(*, source_temporal_authority: Mapping[str, Any], source_post_eot_fingerprint: str, next_turn_fingerprint: str) -> dict[str, Any]:
    if validate_detached_action_order_temporal_source_authority(authority=source_temporal_authority) is not None or not isinstance(source_post_eot_fingerprint, str) or not source_post_eot_fingerprint or not isinstance(next_turn_fingerprint, str) or not next_turn_fingerprint:
        return _result("rejected", "action_order_temporal_source_invalid")
    facts = source_temporal_authority.get("temporal_facts", {})
    rows = {}
    for key in ("self_tailwind", "opponent_tailwind", "trick_room"):
        if facts.get(key, {}).get("state") != "inactive":
            return _result("incomplete", f"{key}_source_authority_unknown")
        rows[key] = {"status": "resolved", "state": "inactive", "source_state": "inactive", "carry_decision": "exact_inactive_no_supported_turn_one_mutator"}
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "source_post_eot_fingerprint": source_post_eot_fingerprint, "source_next_turn_fingerprint": next_turn_fingerprint, "source_temporal_authority": deepcopy(dict(source_temporal_authority)), "source_move_ids": deepcopy(source_temporal_authority["source_move_ids"]), "temporal_facts": rows, "provenance": "exact_inactive_action_order_temporal_state_carried_across_eot_v1"}


def validate_detached_next_turn_action_order_temporal_state_authority(*, authority: Any, **kwargs: Any) -> str | None:
    if not isinstance(authority, Mapping):
        return "next_turn_action_order_temporal_authority_invalid"
    expected = materialize_detached_next_turn_action_order_temporal_state(source_temporal_authority=kwargs.get("source_temporal_authority", authority.get("source_temporal_authority")), source_post_eot_fingerprint=kwargs.get("source_post_eot_fingerprint", authority.get("source_post_eot_fingerprint")), next_turn_fingerprint=kwargs.get("next_turn_fingerprint", authority.get("source_next_turn_fingerprint")))
    return None if deepcopy(dict(authority)) == expected else "next_turn_action_order_temporal_authority_mismatch"


def _owned_move_pair(moves: Mapping[str, Any]) -> bool:
    values = tuple(moves.values())
    return values in (("razor-wind", "tackle"), ("razor-wind", "razor-wind")) or all(value in _CHARGE_MOVES for value in values)


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}


def _source(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SOURCE_SCHEMA_VERSION, "reason": reason}
