"""Compose one authenticated standard-charge release with one pending action.

This is deliberately an ordered-pair adapter, not a new secondary engine.
Release secondaries are owned by the standard-charge executor and state changes
are owned by the existing pair-local predictive-mechanics authority.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import materialize_detached_next_turn_pair_local_predictive_mechanics
from llm.advisor_detached_next_turn_ordinary_attack_execution import execute_detached_next_turn_ordinary_attack, validate_detached_next_turn_ordinary_attack_execution
from llm.advisor_detached_standard_charge_turn_two_attack_execution import execute_detached_standard_charge_turn_two_attacks, validate_detached_standard_charge_turn_two_attack_execution
from llm.advisor_detached_next_turn_action_order_authority import validate_detached_next_turn_action_order_authority
from llm.advisor_detached_next_turn_quick_claw_action_order_authority import validate_detached_next_turn_quick_claw_action_order_authority

SCHEMA_VERSION = "standard-charge-turn-two-pair-secondary-interactions-v1"
_SIDES = ("self", "opponent")


def materialize_standard_charge_turn_two_pair_secondary_interactions(*, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, action_order_authority: Mapping[str, Any], action_executions: Mapping[str, Mapping[str, Any]], quick_claw_action_order_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Compose exact ordered terminals without re-resolving a secondary."""
    error = _inputs(next_decision_state, next_decision_fingerprint, action_order_authority, action_executions, quick_claw_action_order_authority)
    if error is not None:
        return _result("rejected", error)
    orders = quick_claw_action_order_authority["order_branches"] if quick_claw_action_order_authority is not None else action_order_authority["order_branch_plan"]
    terminals = []
    for order in orders:
        first_side = "self" if order["order"] == "self_first" else "opponent"
        second_side = "opponent" if first_side == "self" else "self"
        first = action_executions[first_side]
        for leaf in _leaves(first):
            overlay = materialize_detached_next_turn_pair_local_predictive_mechanics(
                next_decision_state=next_decision_state, next_decision_fingerprint=next_decision_fingerprint,
                predictive_mechanics=_predictive(first), first_action_execution=_authority(first),
                first_action_ledger=_result_for_overlay(first), first_leaf_id=leaf["leaf_id"],
            )
            if overlay.get("status") != "resolved":
                return _result(overlay.get("status", "rejected"), overlay.get("reason", "pair_local_overlay_unavailable"))
            first_probability = _fraction(order["conditional_probability"]) * _fraction(leaf["probability"])
            second = _second_terminal(action_executions[second_side], overlay, first_side, second_side)
            if isinstance(second, str):
                return _result("rejected", second)
            for row in second:
                terminals.append({
                    "pair_leaf_id": f"{order['branch_id']}:{leaf['leaf_id']}:{row['leaf_id']}",
                    "order_branch": deepcopy(dict(order)), "first_side": first_side, "second_side": second_side,
                    "first_action": deepcopy(dict(leaf)), "pair_local_predictive_mechanics_projection": _overlay_projection(overlay),
                    "second_action": deepcopy(dict(row)),
                    "probability": _fd(first_probability * _fraction(row["probability"])),
                    "continuation_retirement": _retirement(first_side, second_side, leaf, row),
                    "continuation_pending_after_pair": False,
                })
    mass = sum((_fraction(row["probability"]) for row in terminals), Fraction(0, 1))
    if mass != 1:
        return _result("rejected", "final_order_branch_mass_invalid")
    return {"status": "resolved", "schema_version": SCHEMA_VERSION,
            "source_next_decision_fingerprint": next_decision_fingerprint,
            "action_order_authority": deepcopy(dict(action_order_authority)),
            "action_executions": deepcopy(dict(action_executions)),
            **({"quick_claw_action_order_authority": deepcopy(dict(quick_claw_action_order_authority))} if quick_claw_action_order_authority is not None else {}),
            "terminal_leaves": tuple(terminals), "terminal_probability_mass": _fd(mass),
            "provenance": "authenticated_standard_charge_release_secondary_ordered_pair_v1"}


def validate_standard_charge_turn_two_pair_secondary_interactions(*, result: Any, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str) -> str | None:
    if not isinstance(result, Mapping): return "standard_charge_secondary_pair_invalid"
    expected = materialize_standard_charge_turn_two_pair_secondary_interactions(
        next_decision_state=next_decision_state, next_decision_fingerprint=next_decision_fingerprint,
        action_order_authority=result.get("action_order_authority"), action_executions=result.get("action_executions"),
        quick_claw_action_order_authority=result.get("quick_claw_action_order_authority"),
    )
    return None if expected == result else "standard_charge_secondary_pair_mismatch"


def _inputs(state, fingerprint, order, actions, quick):
    if not isinstance(actions, Mapping) or set(actions) != set(_SIDES): return "ordered_pair_actions_invalid"
    predictive = _predictive(actions["self"])
    if any(_predictive(actions[side]) != predictive for side in _SIDES): return "ordered_pair_predictive_source_mismatch"
    if validate_detached_next_turn_action_order_authority(authority=order, next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive) is not None: return "ordered_pair_action_order_invalid"
    if order.get("status") != "resolved" or not isinstance(order.get("order_branch_plan"), tuple): return "ordered_pair_action_order_unavailable"
    if quick is not None and validate_detached_next_turn_quick_claw_action_order_authority(authority=quick, next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive) is not None: return "ordered_pair_quick_claw_order_invalid"
    for side in _SIDES:
        row=actions[side]
        if not isinstance(row, Mapping) or row.get("side") != side or row.get("family") not in {"standard_charge", "ordinary"}: return "ordered_pair_action_family_invalid"
        if row["family"] == "standard_charge":
            if validate_detached_standard_charge_turn_two_attack_execution(result=row.get("result"), execution_authority=row.get("execution_authority")) is not None: return "ordered_pair_charge_execution_invalid"
        elif validate_detached_next_turn_ordinary_attack_execution(result=row.get("result"), execution_authority=row.get("execution_authority")) is not None: return "ordered_pair_ordinary_execution_invalid"
        action = _action(row)
        intent = order.get(f"{side}_action_intent", {})
        if not isinstance(action, Mapping) or not isinstance(intent, Mapping): return "ordered_pair_action_identity_unavailable"
        if action.get("actor") != intent.get("actor") or action.get("move_id") != intent.get("move_id"): return "ordered_pair_action_intent_mismatch"
        target = action.get("target")
        expected_target = order.get(f"{'opponent' if side == 'self' else 'self'}_actor")
        if target != expected_target: return "ordered_pair_action_target_mismatch"
    return None


def _leaves(action):
    result=action["result"]
    if action["family"] == "standard_charge":
        ledger=result["actions"].get(action["side"])
    else: ledger=result.get("action_ledger")
    return tuple(ledger.get("terminal_leaves", ()))
def _result_for_overlay(action): return action["result"]
def _authority(action): return action["execution_authority"]
def _predictive(action):
    authority=_authority(action)
    return authority.get("predictive_mechanics")

def _second_terminal(action, overlay, first_side, second_side):
    first_target=overlay["first_target"]
    if overlay["sides"][second_side].get("fainted") is True:
        return (_cancel("cancelled_due_to_faint", "second_action_cancelled_due_to_faint"),)
    flinch=overlay.get("pending_action_flinch", {})
    if flinch.get("status") == "known_flinched":
        if flinch.get("owner") != _actor(action): return "pending_flinch_owner_mismatch"
        return (_cancel("cancelled_due_to_flinch", "second_action_cancelled_due_to_flinch"),)
    if action["family"] == "standard_charge":
        result=execute_detached_standard_charge_turn_two_attacks(execution_authority=action["execution_authority"], pair_local_predictive_mechanics=overlay)
        ledger=result.get("actions", {}).get(second_side)
    else:
        result=execute_detached_next_turn_ordinary_attack(execution_authority=action["execution_authority"], pair_local_predictive_mechanics=overlay)
        ledger=result.get("action_ledger")
    if not isinstance(ledger, Mapping) or ledger.get("status") != "resolved": return "pending_second_action_execution_unavailable"
    return tuple({"leaf_id": leaf["leaf_id"], "state": _state(leaf), "reason": None, "probability": leaf["probability"], "leaf": deepcopy(dict(leaf))} for leaf in ledger["terminal_leaves"])
def _actor(action):
    return _action(action).get("actor")
def _action(action):
    authority=action["execution_authority"]
    return authority.get("action", {}) if action["family"] == "ordinary" else authority.get("actions", {}).get(action["side"], {})
def _cancel(state, reason): return {"leaf_id": f"second_action:{state}", "state": state, "reason": reason, "probability": _fd(Fraction(1)), "leaf": None}
def _state(leaf):
    path=" ".join(str(x) for x in leaf.get("branch_path", ()))
    return "cancelled_due_to_paralysis" if "cancelled_due_to_paralysis" in path else "executed"
def _retirement(first, second, leaf, row):
    first_state = _state(leaf)
    first_reason = None if first_state == "executed" else "first_action_cancelled_due_to_paralysis"
    return {
        first: {"state": first_state, "reason": first_reason, "source_leaf_id": leaf["leaf_id"]},
        second: {"state": row["state"], "reason": row.get("reason"), "source_leaf_id": row["leaf_id"]},
    }
def _overlay_projection(overlay):
    """Keep terminal leaves bounded while top-level actions retain replay sources."""
    return {
        "status": overlay["status"],
        "first_leaf_id": overlay["first_leaf_id"],
        "first_actor": deepcopy(overlay["first_actor"]),
        "first_target": deepcopy(overlay["first_target"]),
        "pending_action_flinch": deepcopy(overlay["pending_action_flinch"]),
        "sides": deepcopy(overlay["sides"]),
    }
def _fraction(value): return Fraction(value["numerator"], value["denominator"])
def _fd(value): return {"numerator":value.numerator,"denominator":value.denominator}
def _result(status, reason): return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
