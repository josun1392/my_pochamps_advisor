"""Trusted observed drag-out request materialization is branch-bound and pure."""
from copy import deepcopy

from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_forced_switch_request import materialize_observed_forced_switch_request
from llm.advisor_observed_persistent_action_result import materialize_observed_persistent_action_result
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _owner_id, _pre
from tests.test_observed_persistent_action_result import _observed


def _observed_drag_out(state, side="self", **changes):
    owner = _owner_id(state, side)
    value = {
        "schema_version": "observed-forced-switch-request-v1",
        "session_id": owner["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state),
        "target_owner": owner,
        "request_kind": "drag_out",
        "result": "drag_out_requested",
        "provenance": "trusted_observed_forced_switch_request_v1",
    }
    value.update(changes)
    return value


def _materialize(state, observation=None):
    return materialize_observed_forced_switch_request(
        branch_state=state,
        source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_request=_observed_drag_out(state) if observation is None else observation,
    )


def _decide(state, request):
    return decide_forced_switch_cancellation(
        branch_state=state,
        source_branch_fingerprint=fingerprint_transition_preview_state(state),
        forced_switch_request=request,
    )


def test_exact_observed_drag_out_materializes_existing_request_idempotently_and_cancels_ingrain():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state, original = pre["next_state"], deepcopy(pre["next_state"])
    observation = _observed_drag_out(state)
    first, repeated = _materialize(state, observation), _materialize(state, observation)
    assert first == repeated and state == original
    request = first["forced_switch_request"]
    assert request["schema_version"] == "forced-switch-request-v1" and request["target_owner"] == _owner_id(state, "self")
    assert _decide(state, request)["decision"] == "cancelled"


def test_action_observed_and_handoff_ingrain_lifecycle_consumes_observed_requests_and_rejects_replay():
    pre = _pre(self_hp=50, self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="unknown")
    source = pre["next_state"]
    action_created = apply_successful_ingrain(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))
    materialized = _materialize(action_created["next_state"])
    assert _decide(action_created["next_state"], materialized["forced_switch_request"])["decision"] == "cancelled"

    observed_pre = _pre(self_hp=50, self_item=None, self_condition="none"); _ingrain(observed_pre["next_state"], self_state="unknown")
    observed_source = observed_pre["next_state"]
    ingrain_observation = materialize_observed_persistent_action_result(branch_state=observed_source, source_branch_fingerprint=fingerprint_transition_preview_state(observed_source), observed_result=_observed(observed_source, "ingrain"))
    observed_created = apply_successful_ingrain(branch_state=observed_source, source_branch_fingerprint=fingerprint_transition_preview_state(observed_source), action_effect=ingrain_observation["successful_action_effect"])
    assert _decide(observed_created["next_state"], _materialize(observed_created["next_state"])["forced_switch_request"])["decision"] == "cancelled"

    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": action_created["next_state"], "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner_id(action_created["next_state"], "self"))
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot); turn_two = handoff["next_state"]
    turn_one_observation = materialized["observed_forced_switch_request"]
    assert materialize_observed_forced_switch_request(branch_state=turn_two, source_branch_fingerprint=fingerprint_transition_preview_state(turn_two), observed_request=turn_one_observation) == {"status": "rejected", "reason": "invalid_observed_forced_switch_request"}
    fresh = _materialize(turn_two)
    assert _decide(turn_two, fresh["forced_switch_request"])["decision"] == "cancelled"


def test_only_exact_trusted_drag_out_requested_observations_materialize():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_inactive")
    state = pre["next_state"]; base = _observed_drag_out(state)
    cases = [
        {**base, "request_kind": "voluntary_switch"},
        {**base, "result": "selected"}, {**base, "result": "attempted"}, {**base, "result": "allowed"},
        {**base, "result": "failed"}, {**base, "result": "blocked"}, {**base, "result": "cancelled"},
        {**base, "result": "unknown"}, {**base, "result": "unresolved"},
        {**base, "source_branch_fingerprint": "stale"}, {**base, "session_id": "foreign"},
        {**base, "target_owner": {**_owner_id(state, "self"), "pokemon_id": "foreign"}},
        {**base, "provenance": "ui_text"},
    ]
    for observation in cases:
        assert _materialize(state, observation) == {"status": "rejected", "reason": "invalid_observed_forced_switch_request"}
    stale_branch = materialize_observed_forced_switch_request(branch_state=state, source_branch_fingerprint="stale", observed_request=base)
    assert stale_branch == {"status": "rejected", "reason": "stale_or_invalid_observed_forced_switch_branch"}


def test_materialized_request_only_answers_cancellation_and_does_not_depend_on_other_persistent_families():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_inactive")
    state = pre["next_state"]
    rows = state["branch_persistent_effect_authority"]["states"]
    next(row for row in rows if row["family"] == "aqua_ring" and row["owner"]["side"] == "self")["state"] = "known_active"
    next(row for row in rows if row["family"] == "leech_seed" and row["owner"]["side"] == "self")["state"] = "known_active"
    result = _materialize(state)
    decision = _decide(state, result["forced_switch_request"])
    assert decision["decision"] == "allowed_to_proceed" and decision["replacement_execution"] == "out_of_scope"
