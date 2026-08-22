"""Closure audit for observed drag-out request, request, and decision layers."""
from copy import deepcopy

from llm.advisor_forced_switch_request import decide_forced_switch_cancellation, materialize_forced_switch_request
from llm.advisor_observed_forced_switch_request import materialize_observed_forced_switch_request
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _owner_id, _pre
from tests.test_observed_forced_switch_request import _observed_drag_out


def _materialize(state, observation):
    return materialize_observed_forced_switch_request(
        branch_state=state,
        source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_request=observation,
    )


def _decision(state, request):
    return decide_forced_switch_cancellation(
        branch_state=state,
        source_branch_fingerprint=fingerprint_transition_preview_state(state),
        forced_switch_request=request,
    )


def test_layers_are_separate_and_same_current_observation_and_request_are_idempotent():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state, original = pre["next_state"], deepcopy(pre["next_state"])
    observation = _observed_drag_out(state)
    first, duplicate = _materialize(state, observation), _materialize(state, observation)
    request = first["forced_switch_request"]
    first_decision, duplicate_decision = _decision(state, request), _decision(state, request)
    assert first == duplicate and first_decision == duplicate_decision and state == original
    assert first["observed_forced_switch_request"] == observation
    assert request["schema_version"] == "forced-switch-request-v1"
    assert first_decision["schema_version"] == "forced-switch-cancellation-decision-v1"
    assert first_decision["decision"] == "cancelled" and first_decision["branch_mutation"] == "none"


def test_historical_observation_request_and_decision_reject_after_same_turn_branch_mutation():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state = pre["next_state"]; observation = _observed_drag_out(state); request = _materialize(state, observation)["forced_switch_request"]
    decision = _decision(state, request)
    changed = deepcopy(state); changed["audit_nonmechanical_branch_metadata"] = {"generation": 2}
    changed_fp = fingerprint_transition_preview_state(changed)
    assert materialize_observed_forced_switch_request(branch_state=changed, source_branch_fingerprint=changed_fp, observed_request=observation) == {"status": "rejected", "reason": "invalid_observed_forced_switch_request"}
    assert materialize_forced_switch_request(branch_state=changed, source_branch_fingerprint=changed_fp, observed_request=request) == {"status": "rejected", "reason": "stale_or_invalid_forced_switch_request"}
    assert decide_forced_switch_cancellation(branch_state=changed, source_branch_fingerprint=changed_fp, forced_switch_request=request) == {"status": "rejected", "reason": "stale_or_invalid_forced_switch_request"}
    assert decide_forced_switch_cancellation(branch_state=changed, source_branch_fingerprint=changed_fp, forced_switch_request=decision) == {"status": "rejected", "reason": "stale_or_invalid_forced_switch_request"}


def test_forced_ingrain_cancellation_never_reuses_voluntary_ghost_or_shed_shell_exceptions():
    pre = _pre(self_item="shed-shell", self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state = pre["next_state"]
    state["current_state"]["current_type_context"] = {"current_types": [
        {"side": "self", "state": "known", "types": ["ghost"], "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current", "confidence": "known"},
        {"side": "opponent", "state": "known", "types": ["normal"], "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current", "confidence": "known"},
    ]}
    request = _materialize(state, _observed_drag_out(state))["forced_switch_request"]
    assert _decision(state, request)["decision"] == "cancelled"


def test_exact_request_target_cannot_be_retargeted_to_an_incoming_identity():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state = pre["next_state"]; observation = _observed_drag_out(state)
    foreign_target = {**observation, "target_owner": {**_owner_id(state, "self"), "slot_index": 1, "pokemon_id": "incoming"}}
    assert _materialize(state, foreign_target) == {"status": "rejected", "reason": "invalid_observed_forced_switch_request"}
