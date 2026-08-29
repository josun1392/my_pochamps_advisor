"""Strict detached Burning Bulwark blocked-contact burn coverage."""

from copy import deepcopy

from llm.advisor_reducer_state_model import make_unknown_battle_fact, state_fingerprint
from llm.advisor_runtime_d0_burning_bulwark_reactive_burn_authority import (
    build_burning_bulwark_reactive_burn_applicability_resolution,
    build_burning_bulwark_successful_block_context,
    freeze_runtime_d0_burning_bulwark_reactive_burn_authority,
    materialize_detached_burning_bulwark_reactive_burn,
)
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_immediate_protection_response_pair import _own_action
from tests.test_detached_opponent_response_profile import _inputs


def _protection(d0):
    return {
        "status": "resolved",
        "owner": deepcopy(d0["active_owners"]["opponent"]),
        "metadata": {"move_id": "burning-bulwark"},
        "provenance": "existing_exact_successful_burning_bulwark_protection_v1",
    }


def _context(d0, action, *, blocked=True, bypass=False, substitute=None):
    return build_burning_bulwark_successful_block_context(
        session_id=d0["session_id"],
        shield_owner=d0["active_owners"]["opponent"],
        shield_action_id="opponent_attack:burning-bulwark",
        blocked_attacker=d0["active_owners"]["self"],
        blocked_action_id=action["action_id"],
        blocked_move_id=action["identity"],
        protection_authority=_protection(d0),
        action_blocked=blocked,
        protection_bypass=bypass,
        substitute_authority=substitute or {"status": "known_absent"},
    )


def _applicability(d0, action, *, outcome="applies", ability=None, item=None):
    return build_burning_bulwark_reactive_burn_applicability_resolution(
        session_id=d0["session_id"],
        shield_owner=d0["active_owners"]["opponent"],
        blocked_attacker=d0["active_owners"]["self"],
        blocked_action_id=action["action_id"],
        blocked_move_id=action["identity"],
        outcome=outcome,
        ability_authority=ability or {"status": "known", "value": "pressure"},
        item_authority=item or {"status": "known_absent"},
    )


def _contact(d0, snapshot, action):
    return freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        attacker=d0["active_owners"]["self"],
        target=d0["active_owners"]["opponent"],
    )


def _freeze(d0, snapshot, action, **kwargs):
    return freeze_runtime_d0_burning_bulwark_reactive_burn_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        shield_owner=d0["active_owners"]["opponent"],
        shield_action_id="opponent_attack:burning-bulwark",
        blocked_attacker=d0["active_owners"]["self"],
        blocked_action=action,
        contact_authority=kwargs.get("contact", _contact(d0, snapshot, action)),
        protection_block_context=kwargs.get("context", _context(d0, action)),
        applicability_resolution=kwargs.get("applicability", _applicability(d0, action)),
    )


def _refresh(state, d0):
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    return snapshot, freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot, decision_owner=d0["decision_owner"]
    )


def test_burning_bulwark_exact_eligible_contact_applies_and_materializes_detached_burn_without_mutation():
    state, snapshot, d0, _unused, _responses, _orders = _inputs()
    before = deepcopy(state)
    action = _own_action(d0, "tackle")

    result = _freeze(d0, snapshot, action)

    assert result["status"] == "resolved" and result["outcome"] == "applies"
    assert result["condition_before"] == "none"
    assert result["condition_after"] == "burn"
    assert result["probability"] == {"numerator": 1, "denominator": 1}
    assert all(key not in result for key in ("hit_state", "critical_state", "damage_roll"))
    overlay = materialize_detached_burning_bulwark_reactive_burn(authority=result)
    assert overlay["status"] == "resolved" and overlay["transition_applied"] is True
    assert overlay["hypothetical_condition_authority"]["condition"] == "burn"
    assert overlay["hypothetical_condition_authority"]["condition_before"] == "known_none"
    assert state == before


def test_burning_bulwark_exact_no_effect_conditions_fire_and_prevention_preserve_condition():
    for condition, types, reason in (
        ("burn", ["normal"], "blocked_attacker_already_statused"),
        ("poison", ["normal"], "blocked_attacker_already_statused"),
        ("paralysis", ["normal"], "blocked_attacker_already_statused"),
        ("none", ["fire"], "blocked_attacker_fire_type_immune"),
    ):
        state, _snapshot, d0, _unused, _responses, _orders = _inputs()
        row = state["self_side"]["pokemon"][0]
        row["condition"] = condition
        row["condition_provenance"]["condition"] = condition
        row["current_type"] = types
        snapshot, d0 = _refresh(state, d0)
        action = _own_action(d0, "tackle")
        result = _freeze(d0, snapshot, action)
        assert result["status"] == "resolved"
        assert result["outcome"] == "not_applicable"
        assert result["reason"] == reason
        assert materialize_detached_burning_bulwark_reactive_burn(authority=result)["transition_applied"] is False

    state, snapshot, d0, _unused, _responses, _orders = _inputs()
    action = _own_action(d0, "tackle")
    prevented = _freeze(
        d0, snapshot, action,
        applicability=_applicability(d0, action, outcome="prevented"),
    )
    assert prevented["status"] == "resolved"
    assert prevented["outcome"] == "not_applicable"
    assert prevented["reason"] == "reactive_burn_prevented"


def test_burning_bulwark_non_contact_and_unknown_required_authority_are_exact():
    state, snapshot, d0, _unused, _responses, _orders = _inputs()
    contact = _own_action(d0, "tackle")
    non_contact = _freeze(d0, snapshot, _own_action(d0, "shadow-ball"))
    assert non_contact["status"] == "resolved"
    assert non_contact["outcome"] == "not_applicable"
    assert non_contact["reason"] == "blocked_action_known_non_contact"
    failed = _freeze(d0, snapshot, contact, context=_context(d0, contact, blocked=False))
    bypassed = _freeze(d0, snapshot, contact, context=_context(d0, contact, bypass=True))
    assert failed["status"] == "resolved" and failed["outcome"] == "not_applicable"
    assert bypassed["status"] == "resolved" and bypassed["outcome"] == "not_applicable"
    unknown_contact = deepcopy(_contact(d0, snapshot, contact))
    unknown_contact["status"] = "incomplete"
    assert _freeze(d0, snapshot, contact, contact=unknown_contact)["status"] == "incomplete"
    assert _freeze(
        d0, snapshot, contact,
        applicability=_applicability(d0, contact, ability={"status": "unknown"}),
    )["status"] == "incomplete"
    assert _freeze(
        d0, snapshot, contact,
        context=_context(d0, contact, substitute={"status": "unknown"}),
    )["status"] == "incomplete"

    state["self_side"]["pokemon"][0].update(
        condition="burn",
        condition_provenance={
            "event_kind": "condition_applied_observed",
            "trust": "user_confirmed_observation",
        },
    )
    snapshot, d0 = _refresh(state, d0)
    assert _freeze(d0, snapshot, _own_action(d0, "tackle"))["status"] == "incomplete"

    state, _snapshot, d0, _unused, _responses, _orders = _inputs()
    state["self_side"]["pokemon"][0].update(
        current_type=make_unknown_battle_fact(), current_type_provenance=None
    )
    snapshot, d0 = _refresh(state, d0)
    assert _freeze(d0, snapshot, _own_action(d0, "tackle"))["status"] == "incomplete"


def test_burning_bulwark_stale_foreign_contact_and_action_mismatches_reject():
    state, snapshot, d0, _unused, _responses, _orders = _inputs()
    action = _own_action(d0, "tackle")
    bad_contact = deepcopy(_contact(d0, snapshot, action))
    bad_contact["move_id"] = "scratch"
    assert _freeze(d0, snapshot, action, contact=bad_contact)["status"] == "rejected"

    bad_context = deepcopy(_context(d0, action))
    bad_context["blocked_action_id"] = "foreign"
    assert _freeze(d0, snapshot, action, context=bad_context)["status"] == "rejected"

    stale = deepcopy(snapshot)
    stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99
    stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert _freeze(d0, stale, action)["status"] == "rejected"
