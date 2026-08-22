"""Roar/Whirlwind observations only materialize exact existing drag-out requests."""
from copy import deepcopy

from llm.advisor_forced_switch_execution import execute_allowed_forced_switch
from llm.advisor_forced_switch_replacement import materialize_forced_switch_replacement_authority
from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_observed_forced_switch_source_application import materialize_observed_forced_switch_source_application
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _observed, _owner, _state


def _source_result(state, *, move_id="roar", user_side="opponent", target_side="self", **changes):
    user, target = _owner(state, user_side), _owner(state, target_side)
    value = {
        "schema_version": "observed-forced-switch-source-application-v1",
        "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state),
        "user": user, "target_owner": target, "move_id": move_id,
        "applied_effect": "drag_out", "result": "applied",
        "provenance": "trusted_observed_forced_switch_source_application_v1",
    }
    value.update(changes)
    return value


def _materialize(state, source=None):
    return materialize_observed_forced_switch_source_application(
        branch_state=state,
        source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_source_result=_source_result(state) if source is None else source,
    )


def test_roar_and_whirlwind_materialize_exact_side_neutral_drag_out_requests_idempotently():
    state, _ = _state()
    source = _source_result(state, move_id="roar")
    first, repeated = _materialize(state, source), _materialize(state, source)
    assert first == repeated
    assert first["forced_switch_request"]["request_kind"] == "drag_out"
    assert first["forced_switch_request"]["target_owner"] == _owner(state, "self")

    opposite = _materialize(state, _source_result(state, move_id="whirlwind", user_side="self", target_side="opponent"))
    assert opposite["status"] == "resolved"
    assert opposite["forced_switch_request"]["target_owner"] == _owner(state, "opponent")


def test_source_materialized_request_uses_existing_cancellation_and_allowed_execution_path():
    state, observed_replacement = _state()
    request = _materialize(state)["forced_switch_request"]
    decision = decide_forced_switch_cancellation(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), forced_switch_request=request,
    )
    authority = materialize_forced_switch_replacement_authority(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        forced_switch_request=request, cancellation_decision=decision, observed_replacement=observed_replacement,
    )
    result = execute_allowed_forced_switch(
        source_branch=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority,
    )
    assert decision["decision"] == "allowed_to_proceed"
    assert result["status"] == "resolved", result


def test_ingrain_cancels_source_materialized_request_and_stale_evidence_cannot_replay():
    state, _ = _state()
    next(row for row in state["branch_persistent_effect_authority"]["states"] if row["family"] == "ingrain" and row["owner"] == _owner(state, "self"))["state"] = "known_active"
    source = _source_result(state)
    request = _materialize(state, source)["forced_switch_request"]
    decision = decide_forced_switch_cancellation(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), forced_switch_request=request,
    )
    assert decision["decision"] == "cancelled"

    changed = deepcopy(state)
    changed["active"]["self"]["current_hp"] -= 1
    assert materialize_observed_forced_switch_source_application(
        branch_state=changed, source_branch_fingerprint=fingerprint_transition_preview_state(changed), observed_source_result=source,
    ) == {"status": "rejected", "reason": "invalid_observed_forced_switch_source_application"}


def test_only_exact_trusted_applied_roar_or_whirlwind_results_materialize():
    state, _ = _state()
    base = _source_result(state)
    cases = [
        {**base, "move_id": "dragon-tail"}, {**base, "move_id": "roar", "applied_effect": "damage"},
    ]
    cases.extend({**base, "result": result} for result in ("selected", "attempted", "allowed", "failed", "blocked", "cancelled", "unknown", "unresolved"))
    cases.extend((
        {**base, "source_branch_fingerprint": "stale"}, {**base, "session_id": "foreign"},
        {**base, "user": _owner(state, "self")}, {**base, "target_owner": {**_owner(state, "self"), "pokemon_id": "foreign"}},
        {**base, "provenance": "ui_text"},
    ))
    for case in cases:
        assert _materialize(state, case) == {"status": "rejected", "reason": "invalid_observed_forced_switch_source_application"}
