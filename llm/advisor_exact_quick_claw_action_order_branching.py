"""Exact Quick Claw activation/non-activation order branches."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_exact_equal_speed_action_order_branching import materialize_exact_equal_speed_action_order_branches


SCHEMA_VERSION = "exact-quick-claw-action-order-branching-v1"
_BINDINGS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")


def materialize_exact_quick_claw_action_order_branches(*, quick_claw_authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(quick_claw_authority, Mapping): return _result("rejected", "quick_claw_authority_invalid", {})
    base = {key: deepcopy(quick_claw_authority.get(key)) for key in _BINDINGS}
    if quick_claw_authority.get("schema_version") != "runtime-d0-quick-claw-action-order-authority-v1" or any(not _present(key, base.get(key)) for key in _BINDINGS): return _result("rejected", "quick_claw_authority_invalid", base)
    if quick_claw_authority.get("status") != "resolved": return _result(_status(quick_claw_authority), quick_claw_authority.get("reason", "quick_claw_authority_unavailable"), base)
    if quick_claw_authority.get("outcome") != "applicable": return _result("incomplete", "quick_claw_not_applicable", base)
    holder, source = quick_claw_authority.get("holder"), quick_claw_authority.get("source_action_order_authority")
    if holder not in (base["own_actor"], base["opponent_actor"]) or not isinstance(source, Mapping) or any(source.get(key) != base.get(key) for key in _BINDINGS): return _result("rejected", "quick_claw_authority_binding_mismatch", base)
    if quick_claw_authority.get("activation_probability") != {"numerator": 1, "denominator": 5} or quick_claw_authority.get("non_activation_probability") != {"numerator": 4, "denominator": 5}: return _result("rejected", "quick_claw_probability_plan_invalid", base)
    holder_order = "own_first" if holder == base["own_actor"] else "opponent_first"
    branches = [_branch(holder_order, holder, "activated", Fraction(1, 5))]
    non_activation = quick_claw_authority.get("non_activation_order")
    if non_activation in {"own_first", "opponent_first"}:
        branches.append(_branch(non_activation, holder, "not_activated", Fraction(4, 5)))
    elif non_activation == "unresolved_tie":
        tied = materialize_exact_equal_speed_action_order_branches(action_order_authority=source)
        if tied.get("status") != "resolved": return _result(_status(tied), tied.get("reason", "quick_claw_non_activation_tie_unavailable"), base)
        for row in tied["order_branches"]:
            branches.append(_branch(row["order"], holder, "not_activated", Fraction(2, 5), row))
    else: return _result("rejected", "quick_claw_non_activation_order_invalid", base)
    if sum((_fraction(row["conditional_probability"]) for row in branches), Fraction()) != Fraction(1, 1): return _result("rejected", "quick_claw_branch_mass_invalid", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "source_quick_claw_authority": deepcopy(dict(quick_claw_authority)), "order_branches": tuple(branches), "probability_semantics": "exact_quick_claw_activation_conditional_on_selected_actions", "ranking_influence": "none"}


def _branch(order: str, holder: Mapping[str, Any], state: str, probability: Fraction, tie: Mapping[str, Any] | None = None) -> dict[str, Any]:
    suffix = f":{order}" if state == "not_activated" else ""
    return {"order_branch_id": f"quick_claw:{holder['side']}:{state}{suffix}", "mechanic": "quick_claw", "order": order, "holder": deepcopy(dict(holder)), "activation_state": state, "conditional_probability": {"numerator": probability.numerator, "denominator": probability.denominator}, **({"non_activation_order_branch": deepcopy(dict(tie))} if tie else {})}


def _present(key: str, value: Any) -> bool:
    return isinstance(value, str) and bool(value) if key not in {"decision_owner", "own_actor", "opponent_actor"} else isinstance(value, Mapping) and bool(value)
def _fraction(value: Any) -> Fraction:
    try: return Fraction(value["numerator"], value["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return Fraction(-1, 1)
def _status(value: Mapping[str, Any]) -> str:
    return value.get("status") if value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
