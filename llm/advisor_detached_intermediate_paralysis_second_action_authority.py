"""Exact hypothetical-paralysis authority for one already-selected second move."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_intermediate_predictive_authority import (
    SCHEMA_VERSION as _INTERMEDIATE_SCHEMA_VERSION,
    detached_intermediate_builder_inputs,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


SCHEMA_VERSION = "detached-intermediate-paralysis-second-action-authority-v1"
_PENDING_STATUS_SCHEMA = "runtime-d0-pending-status-action-execution-authority-v1"
_BINDINGS = (
    "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
    "decision_owner", "intermediate_state_id", "source_first_action_leaf_id",
    "predictive_actor", "predictive_target", "move_id",
)


def consume_detached_intermediate_paralysis_for_second_action(
    *, intermediate_predictive_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose a private builder view and exact paralysis action branches.

    This is conditional on the selected second move.  It does not assign a
    probability to selecting that move and never promotes the condition into
    reducer or current-D0 authority.
    """
    authority = intermediate_predictive_authority
    base = _base(authority)
    if base is None:
        return _result("rejected", "invalid_detached_intermediate_predictive_authority", {})
    if authority.get("status") != "resolved" or authority.get("schema_version") != _INTERMEDIATE_SCHEMA_VERSION or authority.get("hypothetical") is not True:
        return _result("rejected", "invalid_detached_intermediate_predictive_authority", base)
    if not _inner_view_valid(authority):
        return _result("rejected", "detached_intermediate_predictive_binding_mismatch", base)
    overrides = authority.get("intermediate_overrides")
    if not isinstance(overrides, Mapping):
        return _result("rejected", "intermediate_condition_overrides_missing", base)
    changed = _changed_conditions(overrides, authority.get("source_first_action_leaf_id"))
    if isinstance(changed, str):
        return _result("incomplete", changed, base)
    if not changed:
        inputs = detached_intermediate_builder_inputs(authority)
        if inputs.get("status") != "resolved":
            return _result(_status(inputs), inputs.get("reason", "second_action_builder_inputs_unavailable"), base)
        return _resolved(base, inputs, (), _execution_branches(paralyzed=False))
    if any(condition not in {"none", "paralysis", "burn", "poison", "toxic"} for condition in changed.values()):
        return _result("incomplete", "changed_intermediate_condition_not_supported_for_second_action", base)
    inputs = _condition_builder_inputs(authority, changed)
    if inputs.get("status") != "resolved":
        return _result(_status(inputs), inputs.get("reason", "paralysis_second_action_builder_inputs_unavailable"), base)
    actor_changed = changed.get("actor") == "paralysis"
    return _resolved(base, inputs, tuple(sorted(changed)), _execution_branches(paralyzed=actor_changed))


def consume_detached_sleep_freeze_execution_for_second_action(
    *, intermediate_predictive_authority: Mapping[str, Any], pending_action_id: str,
    pending_status_execution_authority: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Apply only an already-resolved current-D0 sleep/freeze action result.

    A first-action-created sleep/freeze override cannot consume a runtime
    observation: it has no leaf-bound execution-result producer in this v1.
    """
    result = consume_detached_intermediate_paralysis_for_second_action(
        intermediate_predictive_authority=intermediate_predictive_authority,
    )
    if result.get("status") != "resolved":
        return result
    authority = intermediate_predictive_authority
    condition = _current_pending_actor_sleep_or_freeze(authority)
    if condition in {"intermediate_condition_override_missing", "hypothetical_sleep_freeze_execution_authority_missing"}:
        return _result("incomplete", condition, _base(authority) or {})
    if condition is None:
        return result
    if pending_status_execution_authority is None:
        return _result("incomplete", "pending_sleep_freeze_execution_authority_missing", _base(authority) or {})
    if not _pending_status_matches(result, pending_status_execution_authority, pending_action_id, condition):
        return _result("rejected", "pending_sleep_freeze_execution_authority_binding_mismatch", _base(authority) or {})
    execution_state, blocker = pending_status_execution_authority["execution_state"], pending_status_execution_authority["blocker"]
    branches = (
        {"execution_branch_id": "second_action:can_act_after_status_execution_observation", "state": "executed", "conditional_probability": _fd(Fraction(1, 1))},
    ) if execution_state == "executable" else (
        {"execution_branch_id": f"second_action:blocked_by_{blocker}", "state": f"cancelled_due_to_{blocker}", "conditional_probability": _fd(Fraction(1, 1)), "reason": f"second_action_cancelled_due_to_{blocker}"},
    )
    return {**result, "second_action_execution_branches": branches,
            "pending_status_execution_authority": deepcopy(dict(pending_status_execution_authority)),
            "provenance": "detached_second_action_sleep_freeze_execution_consumer_v1"}


def _resolved(base: Mapping[str, Any], inputs: Mapping[str, Any], changed_roles: tuple[str, ...], branches: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "hypothetical": True,
        "horizon": "immediate_action_pair", **deepcopy(dict(base)),
        "builder_inputs": deepcopy(dict(inputs)),
        "changed_condition_roles": changed_roles,
        "second_action_execution_branches": branches,
        "paralysis_speed_semantics": "action_order_already_frozen_before_first_action",
        "provenance": "exact_intermediate_paralysis_second_action_consumer_v1",
    }


def _execution_branches(*, paralyzed: bool) -> tuple[dict[str, Any], ...]:
    if not paralyzed:
        return ({"execution_branch_id": "second_action:can_act", "state": "executed", "conditional_probability": _fd(Fraction(1, 1))},)
    return (
        {"execution_branch_id": "second_action:fully_paralyzed", "state": "cancelled_due_to_paralysis", "conditional_probability": _fd(Fraction(1, 4)), "reason": "second_action_cancelled_due_to_paralysis"},
        {"execution_branch_id": "second_action:can_act_after_paralysis", "state": "executed", "conditional_probability": _fd(Fraction(3, 4))},
    )


def _changed_conditions(overrides: Mapping[str, Any], source_leaf_id: Any) -> dict[str, str] | str:
    changed: dict[str, str] = {}
    for role in ("actor", "target"):
        row = overrides.get(role)
        if not isinstance(row, Mapping):
            return "intermediate_condition_override_missing"
        condition = row.get("condition")
        changed_flag = row.get("condition_changed")
        if not isinstance(changed_flag, bool):
            return "intermediate_condition_change_flag_invalid"
        if not changed_flag:
            continue
        if not isinstance(condition, Mapping):
            return "intermediate_exact_condition_authority_missing"
        if condition.get("source") == "exact_terminal_leaf_condition_effect" and condition.get("status") == "known_present" and isinstance(condition.get("condition"), str):
            changed[role] = condition["condition"]
            continue
        if condition.get("source") == "exact_terminal_leaf_condition_removal" and condition.get("status") == "known_none" and _sparkling_aria_burn_removal(condition.get("effect"), source_leaf_id):
            changed[role] = "none"
            continue
        return "intermediate_exact_condition_authority_missing"
    return changed


def _current_pending_actor_sleep_or_freeze(authority: Mapping[str, Any]) -> str | None:
    overrides = authority.get("intermediate_overrides")
    actor = overrides.get("actor") if isinstance(overrides, Mapping) else None
    if not isinstance(actor, Mapping):
        return "intermediate_condition_override_missing"
    if actor.get("condition_changed") is True:
        condition = actor.get("condition")
        if isinstance(condition, Mapping) and condition.get("status") == "known_present" and condition.get("condition") in {"sleep", "freeze"}:
            return "hypothetical_sleep_freeze_execution_authority_missing"
        return None
    snapshot, owner = authority.get("predictive_runtime_snapshot"), authority.get("predictive_actor")
    raw = _pokemon(snapshot.get("state", {}), owner) if isinstance(snapshot, Mapping) and isinstance(owner, Mapping) else None
    provenance = raw.get("condition_provenance") if isinstance(raw, Mapping) else None
    if isinstance(raw, Mapping) and raw.get("condition") in {"sleep", "freeze"} and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_condition_observed" and provenance.get("trust") == "user_confirmed_observation" and provenance.get("condition") == raw.get("condition"):
        return raw["condition"]
    return None


def _pending_status_matches(result: Mapping[str, Any], pending: Mapping[str, Any], action_id: Any, condition: str) -> bool:
    return isinstance(action_id, str) and bool(action_id) and pending.get("status") == "resolved" and pending.get("schema_version") == _PENDING_STATUS_SCHEMA and pending.get("execution_state") in {"executable", "blocked"} and ((pending.get("execution_state") == "executable" and pending.get("blocker") is None) or (pending.get("execution_state") == "blocked" and pending.get("blocker") == condition)) and pending.get("condition") == condition and pending.get("pending_action_id") == action_id and pending.get("pending_move_id") == result.get("move_id") and pending.get("pending_actor") == result.get("predictive_actor") and all(pending.get(left) == result.get(right) for left, right in (("session_id", "session_id"), ("source_runtime_fingerprint", "source_runtime_fingerprint"), ("source_branch_fingerprint", "source_branch_fingerprint"), ("decision_owner", "decision_owner")))


def _condition_builder_inputs(authority: Mapping[str, Any], changed: Mapping[str, str]) -> dict[str, Any]:
    snapshot = authority.get("predictive_runtime_snapshot")
    actor, target = authority.get("predictive_actor"), authority.get("predictive_target")
    if not isinstance(snapshot, Mapping) or not isinstance(actor, Mapping) or not isinstance(target, Mapping):
        return {"status": "rejected", "reason": "intermediate_predictive_builder_view_invalid"}
    synthetic = deepcopy(dict(snapshot.get("state", {})))
    if not synthetic:
        return {"status": "rejected", "reason": "intermediate_predictive_snapshot_missing"}
    known_none = len(changed) == 1 and next(iter(changed.values())) == "none"
    for role, owner in (("actor", actor), ("target", target)):
        if role not in changed:
            continue
        raw = _pokemon(synthetic, owner)
        if raw is None:
            return {"status": "rejected", "reason": "intermediate_condition_owner_identity_mismatch"}
        # Full-paralysis is handled by explicit execution branches. Other
        # admitted conditions, including exact detached known-none, only flow
        # into the private existing direct/crit consumers.
        raw["condition"] = changed[role]
        raw["detached_exact_intermediate_condition_authority"] = True
        raw["condition_provenance"] = {
            "event_kind": "current_condition_observed", "trust": "user_confirmed_observation",
            "turn_number": 1, "condition": changed[role],
            "hypothetical_provenance": "private_exact_intermediate_condition_calculator_view",
        }
    private_snapshot = {
        "status": "runtime_snapshot_ready", "session_id": authority["session_id"],
        "state": synthetic, "state_fingerprint": state_fingerprint(synthetic),
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=private_snapshot, decision_owner=actor)
    if d0.get("status") != "resolved":
        return {"status": "incomplete", "reason": d0.get("reason", "intermediate_condition_hypothetical_d0_unavailable")}
    return {
        "status": "resolved", "strategy_d0": deepcopy(d0), "runtime_snapshot": private_snapshot,
        "attacker": deepcopy(dict(actor)), "target": deepcopy(dict(target)),
        "move_metadata": deepcopy(dict(authority.get("move_metadata", {}))),
        "hypothetical_condition_authority": {
            "status": "known_none" if known_none else "known_present",
            **({} if known_none else {"condition": next(iter(changed.values())) if len(changed) == 1 else None}),
            "conditions": deepcopy(dict(changed)),
            "provenance": "exact_terminal_leaf_condition_removal" if known_none else "exact_terminal_leaf_condition_effect",
            "calculator_view": "exact_intermediate_condition_for_supported_status_dependent_damage",
        },
        "provenance": "private_exact_hypothetical_intermediate_condition_builder_view_v1",
    }


def _sparkling_aria_burn_removal(value: Any, source_leaf_id: Any) -> bool:
    return isinstance(value, Mapping) and value == {
        "schema_version": "detached-hypothetical-target-condition-removal-v1",
        "condition_before": "burn", "condition_removed": "burn", "condition_after": "none",
        "removal_trigger": "successful_damaging_hit_target_survives",
        "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1",
        "source_leaf_id": source_leaf_id,
    }


def _base(authority: Any) -> dict[str, Any] | None:
    if not isinstance(authority, Mapping) or not all(key in authority for key in _BINDINGS):
        return None
    strings = {"session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "intermediate_state_id", "source_first_action_leaf_id", "move_id"}
    if any(not isinstance(authority.get(key), str) or not authority[key] for key in strings):
        return None
    if not isinstance(authority.get("decision_owner"), Mapping) or not isinstance(authority.get("predictive_actor"), Mapping) or not isinstance(authority.get("predictive_target"), Mapping):
        return None
    return {key: deepcopy(authority[key]) for key in _BINDINGS}


def _inner_view_valid(authority: Mapping[str, Any]) -> bool:
    d0, snapshot = authority.get("predictive_strategy_d0"), authority.get("predictive_runtime_snapshot")
    actor, target = authority.get("predictive_actor"), authority.get("predictive_target")
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(snapshot, Mapping) or snapshot.get("status") != "runtime_snapshot_ready":
        return False
    if d0.get("session_id") != authority.get("session_id") or snapshot.get("session_id") != authority.get("session_id"):
        return False
    if d0.get("decision_owner") != actor or not isinstance(actor, Mapping) or not isinstance(target, Mapping) or actor.get("side") == target.get("side"):
        return False
    state = snapshot.get("state")
    return isinstance(state, Mapping) and _pokemon(state, actor) is not None and _pokemon(state, target) is not None


def _pokemon(state: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    side = state.get(f"{owner.get('side')}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    return value if isinstance(value, dict) and value.get("pokemon_id") == owner.get("pokemon_id") else None


def _fd(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _status(value: Mapping[str, Any]) -> str:
    return value.get("status") if value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
