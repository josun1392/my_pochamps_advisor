"""Strict current-D0 Silk Trap blocked-attacker interaction coverage."""
from copy import deepcopy

from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    SCHEMA_VERSION,
    build_silk_trap_speed_drop_interaction_resolution,
    freeze_runtime_d0_silk_trap_speed_drop_interaction_authority,
)
from llm.advisor_reducer_state_model import state_fingerprint
from tests.test_detached_immediate_protection_response_pair import _own_action, _protect_action, _success
from tests.test_detached_opponent_response_profile import _inputs


def _contact(d0, snapshot, action):
    return freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )


def _protection(d0):
    return {
        "status": "resolved", "owner": deepcopy(d0["active_owners"]["opponent"]),
        "metadata": {"move_id": "silk-trap"}, "provenance": "exact_successful_silk_trap_block_v1",
    }


def _resolution(d0, *, outcome="applies", delta=-1, ability=None, item=None):
    return build_silk_trap_speed_drop_interaction_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"],
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id="attack:tackle",
        blocked_move_id="tackle", outcome=outcome, resulting_delta=delta,
        ability_authority=ability or {"status": "known", "value": "pressure"},
        item_authority=item or {"status": "known_absent"},
    )


def _freeze(d0, snapshot, action, resolution):
    return freeze_runtime_d0_silk_trap_speed_drop_interaction_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, shield_owner=d0["active_owners"]["opponent"],
        blocked_attacker=d0["active_owners"]["self"], blocked_action=action,
        contact_authority=_contact(d0, snapshot, action), protection_authority=_protection(d0),
        interaction_resolution=resolution,
    )


def test_exact_current_silk_trap_interaction_resolves_apply_prevent_and_explicit_reverse_without_mutation():
    state, snapshot, d0, _unused, _responses, _orders = _inputs(); before = deepcopy(state)
    action = _own_action(d0, "tackle")
    applies = _freeze(d0, snapshot, action, _resolution(d0))
    prevented = _freeze(d0, snapshot, action, _resolution(d0, outcome="prevented", delta=0))
    reversed_ = _freeze(d0, snapshot, action, _resolution(d0, outcome="reversed", delta=1))
    assert applies["status"] == "resolved" and applies["schema_version"] == SCHEMA_VERSION
    assert (applies["outcome"], applies["speed_stage_before"], applies["speed_stage_after"]) == ("applies", 0, -1)
    assert (prevented["outcome"], prevented["speed_stage_after"]) == ("prevented", 0)
    assert (reversed_["outcome"], reversed_["speed_stage_after"]) == ("reversed", 1)
    assert state == before


def test_unknown_or_stale_or_foreign_silk_trap_interaction_fails_closed():
    state, snapshot, d0, _unused, _responses, _orders = _inputs(); action = _own_action(d0, "tackle")
    unknown = _freeze(d0, snapshot, action, _resolution(d0, ability={"status": "unknown"}))
    assert unknown["status"] == "incomplete" and unknown["reason"] == "silk_trap_relevant_modifier_authority_unknown"
    wrong_ability = _freeze(d0, snapshot, action, _resolution(d0, ability={"status": "known", "value": "contrary"}))
    assert wrong_ability["status"] == "rejected" and wrong_ability["reason"] == "silk_trap_relevant_modifier_authority_binding_mismatch"
    bad = _resolution(d0); bad["blocked_move_id"] = "scratch"
    assert _freeze(d0, snapshot, action, bad)["status"] == "rejected"
    stale_state = deepcopy(state); stale_state["self_side"]["pokemon"][0]["current_hp"] = 99
    stale_snapshot = {**snapshot, "state": stale_state, "state_fingerprint": state_fingerprint(stale_state)}
    assert _freeze(d0, stale_snapshot, action, _resolution(d0))["status"] == "rejected"
