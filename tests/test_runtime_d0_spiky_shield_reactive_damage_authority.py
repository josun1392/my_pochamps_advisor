"""Strict detached Spiky Shield blocked-contact damage coverage."""
from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_spiky_shield_reactive_damage_authority import (
    build_spiky_shield_reactive_damage_applicability_resolution,
    build_spiky_shield_successful_block_context,
    freeze_runtime_d0_spiky_shield_reactive_damage_authority,
    materialize_detached_spiky_shield_reactive_damage,
)
from tests.test_detached_immediate_protection_response_pair import _own_action
from tests.test_detached_opponent_response_profile import _inputs


def _protection(d0):
    return {"status": "resolved", "owner": deepcopy(d0["active_owners"]["opponent"]), "metadata": {"move_id": "spiky-shield"}, "provenance": "existing_exact_successful_spiky_shield_protection_v1"}


def _context(d0, action, *, blocked=True, bypass=False, substitute=None):
    return build_spiky_shield_successful_block_context(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:spiky-shield",
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id=action["action_id"], blocked_move_id=action["identity"],
        protection_authority=_protection(d0), action_blocked=blocked, protection_bypass=bypass,
        substitute_authority=substitute or {"status": "known_absent"},
    )


def _applicability(d0, action, *, outcome="applies", ability=None, item=None):
    return build_spiky_shield_reactive_damage_applicability_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], blocked_attacker=d0["active_owners"]["self"],
        blocked_action_id=action["action_id"], blocked_move_id=action["identity"], outcome=outcome,
        ability_authority=ability or {"status": "known", "value": "pressure"}, item_authority=item or {"status": "known_absent"},
    )


def _contact(d0, snapshot, action):
    return freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )


def _freeze(d0, snapshot, action, **kwargs):
    return freeze_runtime_d0_spiky_shield_reactive_damage_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:spiky-shield",
        blocked_attacker=d0["active_owners"]["self"], blocked_action=action, contact_authority=kwargs.get("contact", _contact(d0, snapshot, action)),
        protection_block_context=kwargs.get("context", _context(d0, action)), applicability_resolution=kwargs.get("applicability", _applicability(d0, action)),
    )


def test_spiky_shield_uses_its_explicit_eighth_floor_minimum_one_rule_and_detached_overlay():
    for maximum, current, expected_damage, expected_post in ((80, 80, 10, 70), (81, 81, 10, 71), (7, 7, 1, 6), (80, 4, 10, 0)):
        state, snapshot, d0, _unused, _responses, _orders = _inputs(own_hp=current)
        state["self_side"]["pokemon"][0]["max_hp"] = maximum
        snapshot["state"] = deepcopy(state); snapshot["state_fingerprint"] = state_fingerprint(state)
        d0["strategy_state"]["active"]["self"].update(current_hp=current, max_hp=maximum, fainted=False)
        d0["source_runtime_fingerprint"] = snapshot["state_fingerprint"]
        # Re-freeze from the exact runtime snapshot so all D0 bindings remain current.
        from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])
        action = _own_action(d0, "tackle")
        result = _freeze(d0, snapshot, action)
        assert result["status"] == "resolved", result
        assert result["rule_id"] == "spiky_shield_blocked_contact_max_hp_eighth_floor_minimum_one"
        assert result["damage_fraction"] == {"numerator": 1, "denominator": 8}
        assert (result["reactive_damage"], result["post_hp"], result["fainted"]) == (expected_damage, expected_post, expected_post == 0)
        overlay = materialize_detached_spiky_shield_reactive_damage(authority=result)
        assert overlay["status"] == "resolved" and overlay["hypothetical_hp_authority"]["current_hp"] == expected_post


def test_spiky_shield_non_contact_failed_bypassed_and_prevented_are_exact_no_reactive_consequence():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs(); action = _own_action(d0, "shadow-ball")
    non_contact = _freeze(d0, snapshot, action)
    assert non_contact["status"] == "resolved" and non_contact["outcome"] == "not_applicable" and non_contact["reactive_damage"] is None

    contact_action = _own_action(d0, "tackle")
    for context, applicability in ((_context(d0, contact_action, blocked=False), None), (_context(d0, contact_action, bypass=True), None), (_context(d0, contact_action), _applicability(d0, contact_action, outcome="prevented"))):
        result = _freeze(d0, snapshot, contact_action, context=context, applicability=applicability or _applicability(d0, contact_action))
        assert result["status"] == "resolved" and result["outcome"] == "not_applicable" and result["reactive_damage"] is None


def test_spiky_shield_unknown_and_foreign_inputs_fail_closed_without_hit_identity():
    state, snapshot, d0, _unused, _responses, _orders = _inputs(); action = _own_action(d0, "tackle")
    unknown_contact = deepcopy(_contact(d0, snapshot, action)); unknown_contact["status"] = "incomplete"; unknown_contact["reason"] = "contact_unknown"
    assert _freeze(d0, snapshot, action, contact=unknown_contact)["status"] == "incomplete"
    unknown_modifier = _applicability(d0, action, ability={"status": "unknown"})
    assert _freeze(d0, snapshot, action, applicability=unknown_modifier)["status"] == "incomplete"
    unresolved_substitute = _context(d0, action, substitute={"status": "unknown"})
    assert _freeze(d0, snapshot, action, context=unresolved_substitute)["status"] == "incomplete"
    bad_contact = deepcopy(_contact(d0, snapshot, action)); bad_contact["move_id"] = "scratch"
    assert _freeze(d0, snapshot, action, contact=bad_contact)["status"] == "rejected"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert _freeze(d0, stale, action)["status"] == "rejected"
