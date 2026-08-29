"""Strict D0-bound Quick Guard priority applicability coverage."""
from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_quick_guard_priority_applicability_authority import (
    build_quick_guard_protection_context,
    freeze_runtime_d0_quick_guard_priority_applicability_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_immediate_protection_response_pair import _own_action
from tests.test_detached_opponent_response_profile import _inputs


def _context(d0, action, *, blocked=True, bypass=False):
    protection = {"status": "resolved", "owner": deepcopy(d0["active_owners"]["opponent"]), "metadata": {"move_id": "quick-guard"}}
    return build_quick_guard_protection_context(
        session_id=d0["session_id"], guard_user=d0["active_owners"]["opponent"], guard_action_id="opponent_attack:quick-guard",
        incoming_actor=d0["active_owners"]["self"], incoming_action_id=action["action_id"], incoming_move_id=action["identity"],
        selected_target=d0["active_owners"]["opponent"], protection_authority=protection, action_blocked=blocked, protection_bypass=bypass,
    )


def _freeze(d0, snapshot, action, **kwargs):
    return freeze_runtime_d0_quick_guard_priority_applicability_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, guard_user=d0["active_owners"]["opponent"], guard_action_id="opponent_attack:quick-guard",
        incoming_actor=d0["active_owners"]["self"], incoming_action=action, selected_target=kwargs.get("target", d0["active_owners"]["opponent"]),
        protection_context=kwargs.get("context", _context(d0, action)),
    )


def test_quick_guard_exact_positive_base_priority_applies_and_zero_priority_does_not():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    positive = _own_action(d0, "tackle")
    positive["move_metadata_authority"]["metadata"].update(priority=1, target="selected-pokemon")
    applied = _freeze(d0, snapshot, positive)
    assert applied["status"] == "resolved" and applied["outcome"] == "applies"
    assert applied["effective_priority_authority"]["effective_priority"] == 1

    zero = _own_action(d0, "tackle")
    zero["move_metadata_authority"]["metadata"].update(priority=0, target="selected-pokemon")
    no_effect = _freeze(d0, snapshot, zero)
    assert no_effect["status"] == "resolved" and no_effect["outcome"] == "not_applicable"


def test_quick_guard_uses_exact_gale_wings_calculation_not_action_order_output():
    state, snapshot, d0, _unused, _responses, _orders = _inputs()
    row = state["self_side"]["pokemon"][0]
    row["current_ability"] = "gale-wings"
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])
    action = _own_action(d0, "tackle")
    action["move_metadata_authority"]["metadata"].update(priority=0, type="flying", target="selected-pokemon")
    result = _freeze(d0, snapshot, action)
    assert result["status"] == "resolved" and result["outcome"] == "applies"
    assert result["effective_priority_authority"]["effective_priority"] == 1
    assert result["effective_priority_authority"]["priority_engine"]["self_gale_wings_applied"] is True


def test_quick_guard_unknown_unsupported_and_binding_fail_closed():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    action = _own_action(d0, "tackle")
    action["move_metadata_authority"]["metadata"].update(priority=0, type="flying", target="selected-pokemon")
    state = deepcopy(snapshot["state"])
    state["self_side"]["pokemon"][0]["current_ability"] = "unknown"
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])
    action = _own_action(d0, "tackle"); action["move_metadata_authority"]["metadata"].update(priority=0, type="flying", target="selected-pokemon")
    assert _freeze(d0, snapshot, action)["status"] == "incomplete"

    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    action = _own_action(d0, "tackle"); action["move_metadata_authority"]["metadata"].update(priority=1, target="selected-pokemon")
    assert _freeze(d0, snapshot, action, target=d0["active_owners"]["self"])["status"] == "rejected"
    foreign = deepcopy(_context(d0, action)); foreign["incoming_action_id"] = "foreign"
    assert _freeze(d0, snapshot, action, context=foreign)["status"] == "rejected"
    assert _freeze(d0, snapshot, action, context=_context(d0, action, blocked=False))["outcome"] == "not_applicable"
    assert _freeze(d0, snapshot, action, context=_context(d0, action, bypass=True))["outcome"] == "not_applicable"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert _freeze(d0, stale, action)["status"] == "rejected"
