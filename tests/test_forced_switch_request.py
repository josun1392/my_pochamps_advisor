"""Ingrain-only cancellation of exact branch-bound forced-removal requests."""
from copy import deepcopy

from llm.advisor_forced_switch_request import (
    decide_forced_switch_cancellation,
    materialize_forced_switch_request,
)
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_persistent_action_result import materialize_observed_persistent_action_result
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _owner_id, _pre
from tests.test_observed_persistent_action_result import _observed


def _request(state, side="self", **changes):
    owner = _owner_id(state, side)
    value = {
        "schema_version": "forced-switch-request-v1",
        "session_id": owner["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state),
        "target_owner": owner,
        "request_kind": "drag_out",
        "provenance": "trusted_forced_switch_request_v1",
    }
    value.update(changes)
    return value


def _decision(state, request=None):
    return decide_forced_switch_cancellation(
        branch_state=state,
        source_branch_fingerprint=fingerprint_transition_preview_state(state),
        forced_switch_request=_request(state) if request is None else request,
    )


def test_exact_active_ingrain_cancels_without_mutating_current_branch_or_identity():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state, original = pre["next_state"], deepcopy(pre["next_state"])
    request = _request(state)
    materialized = materialize_forced_switch_request(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), observed_request=request)
    result = _decision(state, request)
    assert materialized["status"] == "resolved"
    assert result["decision"] == "cancelled" and result["cancellation_source"] == "ingrain_on_drag_out"
    assert result["replacement_execution"] == "out_of_scope" and result["branch_mutation"] == "none"
    assert state == original and result["target_owner"] == _owner_id(state, "self")


def test_inactive_allows_unknown_is_incomplete_and_other_persistent_families_do_not_cancel():
    inactive = _pre(self_item=None, self_condition="none"); _ingrain(inactive["next_state"], self_state="known_inactive")
    assert _decision(inactive["next_state"])["decision"] == "allowed_to_proceed"
    unknown = _pre(self_item=None, self_condition="none"); _ingrain(unknown["next_state"], self_state="unknown")
    assert _decision(unknown["next_state"]) == {"status": "incomplete", "reason": "ingrain_persistent_effect_unknown"}
    aqua_only = _pre(self_item=None, self_condition="none"); _ingrain(aqua_only["next_state"], self_state="known_inactive")
    rows = aqua_only["next_state"]["branch_persistent_effect_authority"]["states"]
    next(row for row in rows if row["family"] == "aqua_ring" and row["owner"]["side"] == "self")["state"] = "known_active"
    assert _decision(aqua_only["next_state"])["decision"] == "allowed_to_proceed"
    seed_only = _pre(self_item=None, self_condition="none"); _ingrain(seed_only["next_state"], self_state="known_inactive")
    next(row for row in seed_only["next_state"]["branch_persistent_effect_authority"]["states"] if row["family"] == "leech_seed" and row["owner"]["side"] == "self")["state"] = "known_active"
    assert _decision(seed_only["next_state"])["decision"] == "allowed_to_proceed"


def test_successful_observed_and_handoff_ingrain_authority_cancel_exact_requests():
    pre = _pre(self_hp=50, self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="unknown")
    source = pre["next_state"]
    applied = apply_successful_ingrain(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))
    assert _decision(applied["next_state"])["decision"] == "cancelled"

    observed = _pre(self_hp=50, self_item=None, self_condition="none"); _ingrain(observed["next_state"], self_state="unknown")
    observed_source = observed["next_state"]
    action = materialize_observed_persistent_action_result(branch_state=observed_source, source_branch_fingerprint=fingerprint_transition_preview_state(observed_source), observed_result=_observed(observed_source, "ingrain"))
    observed_applied = apply_successful_ingrain(branch_state=observed_source, source_branch_fingerprint=fingerprint_transition_preview_state(observed_source), action_effect=action["successful_action_effect"])
    assert _decision(observed_applied["next_state"])["decision"] == "cancelled"

    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": applied["next_state"], "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner_id(applied["next_state"], "self"))
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)
    assert _decision(handoff["next_state"])["decision"] == "cancelled"


def test_requests_are_exact_and_never_reuse_voluntary_or_stale_authority():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active")
    state = pre["next_state"]; request = _request(state)
    cases = [
        {**request, "request_kind": "voluntary_switch"},
        {**request, "source_branch_fingerprint": "stale"},
        {**request, "session_id": "foreign"},
        {**request, "target_owner": {**_owner_id(state, "self"), "pokemon_id": "incoming"}},
        {**request, "target_owner": {**_owner_id(state, "self"), "side": "foreign"}},
        {**request, "provenance": "ui_text"},
    ]
    for candidate in cases:
        assert _decision(state, candidate) == {"status": "rejected", "reason": "stale_or_invalid_forced_switch_request"}
    stale = _request(state)
    assert decide_forced_switch_cancellation(branch_state=state, source_branch_fingerprint="stale", forced_switch_request=stale) == {"status": "rejected", "reason": "stale_or_invalid_forced_switch_branch"}
    malformed = deepcopy(state); malformed["branch_persistent_effect_authority"]["session_id"] = "foreign"
    assert _decision(malformed) == {"status": "rejected", "reason": "stale_or_invalid_ingrain_forced_switch_authority"}
