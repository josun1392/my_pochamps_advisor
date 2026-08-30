"""Strict applicability coverage for the bounded canonical Wide Guard owner."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_runtime_d0_wide_guard_spread_applicability_authority import (
    build_wide_guard_protection_context,
    freeze_runtime_d0_wide_guard_spread_applicability_authority,
)
from tests.test_detached_rock_slide_multi_recipient_predictive_graph_materialization import _inputs


def _protection(guard):
    return {"status": "resolved", "owner": deepcopy(guard), "metadata": {"move_id": "wide-guard"}}


def _authority(*, blocked=True, bypass=False, target_set=None, scope=None):
    _state, snapshot, d0, action, frozen_scope = _inputs()
    guard = d0["active_owners"]["opponent"]
    targets = frozen_scope["target_set_authority"] if target_set is None else target_set
    use_scope = frozen_scope if scope is None else scope
    context = build_wide_guard_protection_context(
        session_id=d0["session_id"], guard_user=guard, guard_action_id="opponent_action:wide-guard",
        incoming_actor=d0["decision_owner"], incoming_action_id=action["action_id"], incoming_move_id=action["identity"],
        protected_side="opponent", protection_authority=_protection(guard), action_blocked=blocked, protection_bypass=bypass,
    )
    return freeze_runtime_d0_wide_guard_spread_applicability_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard",
        incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=targets,
        execution_scope_authority=use_scope, protection_context=context,
    ), d0, snapshot, action, frozen_scope, context


def test_canonical_rock_slide_spread_scope_applies_and_preserves_exact_protected_recipients():
    result, _d0, _snapshot, _action, scope, _context = _authority()
    assert result["status"] == "resolved", result.get("reason")
    assert result["outcome"] == "applies"
    assert result["protected_side"] == "opponent"
    assert result["protected_recipients"] == scope["recipients"]
    assert result["incoming_recipient_classification"] == "spread_multi_target"


def test_wide_guard_exact_no_effect_and_incomplete_boundaries():
    failed, *_ = _authority(blocked=False)
    bypassed, *_ = _authority(bypass=True)
    assert failed["outcome"] == "not_applicable" and bypassed["outcome"] == "not_applicable"
    missing_targets, *_ = _authority(target_set=None, scope=None)
    # Explicitly omit rather than use the default fixture value.
    _state, snapshot, d0, action, scope = _inputs()
    guard = d0["active_owners"]["opponent"]
    context = build_wide_guard_protection_context(session_id=d0["session_id"], guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_actor=d0["decision_owner"], incoming_action_id=action["action_id"], incoming_move_id=action["identity"], protected_side="opponent", protection_authority=_protection(guard), action_blocked=True, protection_bypass=False)
    missing_targets = freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=None, execution_scope_authority=scope, protection_context=context)
    missing_scope = freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=scope["target_set_authority"], execution_scope_authority=None, protection_context=context)
    assert missing_targets["status"] == "incomplete"
    assert missing_scope["status"] == "incomplete"


def test_wide_guard_exact_nonspread_and_no_protected_recipient_are_not_applicable():
    _result, d0, snapshot, action, scope, context = _authority()
    guard = d0["active_owners"]["opponent"]
    nonspread = deepcopy(scope["target_set_authority"])
    nonspread["recipient_classification"] = "single_target"
    result = freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=nonspread, execution_scope_authority=scope, protection_context=context)
    assert result["status"] == "resolved" and result["outcome"] == "not_applicable"

    target_set = deepcopy(scope["target_set_authority"])
    rewritten = tuple({**row, "side": "self", "owner": {**row["owner"], "side": "self"}} for row in target_set["recipients"])
    target_set["recipients"] = rewritten
    no_side_scope = deepcopy(scope); no_side_scope["recipients"] = rewritten; no_side_scope["target_set_authority"] = deepcopy(target_set)
    no_side = freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=target_set, execution_scope_authority=no_side_scope, protection_context=context)
    assert no_side["status"] == "resolved" and no_side["outcome"] == "not_applicable"


def test_wide_guard_rejects_stale_and_conflicting_frozen_authority_bindings():
    result, d0, snapshot, action, scope, context = _authority()
    assert result["status"] == "resolved"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99
    from llm.advisor_reducer_state_model import state_fingerprint
    stale["state_fingerprint"] = state_fingerprint(stale["state"])
    guard = d0["active_owners"]["opponent"]
    assert freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=stale, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=scope["target_set_authority"], execution_scope_authority=scope, protection_context=context)["status"] == "rejected"
    conflicting = deepcopy(scope); conflicting["recipients"] = tuple(reversed(conflicting["recipients"]))
    assert freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=action, protected_side="opponent", decision_point="turn:1", target_set_authority=scope["target_set_authority"], execution_scope_authority=conflicting, protection_context=context)["status"] == "rejected"
    foreign_action = {**action, "action_id": "attack:foreign"}
    assert freeze_runtime_d0_wide_guard_spread_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=guard, guard_action_id="opponent_action:wide-guard", incoming_action=foreign_action, protected_side="opponent", decision_point="turn:1", target_set_authority=scope["target_set_authority"], execution_scope_authority=scope, protection_context=context)["status"] == "rejected"
