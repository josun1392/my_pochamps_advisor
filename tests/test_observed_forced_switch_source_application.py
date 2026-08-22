"""Roar/Whirlwind observations only materialize exact existing drag-out requests."""
from copy import deepcopy

from llm.advisor_forced_switch_execution import execute_allowed_forced_switch
from llm.advisor_forced_switch_replacement import materialize_forced_switch_replacement_authority
from llm.advisor_forced_switch_request import decide_forced_switch_cancellation, materialize_forced_switch_request
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_forced_switch_source_application import materialize_observed_forced_switch_source_application
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _observed, _owner, _state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _pre


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
    original = deepcopy(state)
    source = _source_result(state, move_id="roar")
    first, repeated = _materialize(state, source), _materialize(state, source)
    assert first == repeated and state == original
    assert first["forced_switch_request"]["request_kind"] == "drag_out"
    assert first["forced_switch_request"]["target_owner"] == _owner(state, "self")

    opposite = _materialize(state, _source_result(state, move_id="whirlwind", user_side="self", target_side="opponent"))
    assert opposite["status"] == "resolved"
    assert opposite["forced_switch_request"]["target_owner"] == _owner(state, "opponent")


def test_whirlwind_source_drives_opponent_replacement_through_the_shared_executor():
    state, observed = _state()
    outgoing = _owner(state, "opponent")
    incoming = deepcopy(observed["incoming_authority"])
    incoming["owner"] = {"session_id": outgoing["session_id"], "side": "opponent", "slot_index": 1, "pokemon_id": "opponent-incoming"}
    target = deepcopy(observed["entry_authority"]["target_roster_mechanics"])
    target.update(incoming["owner"]); target["fainted_authority"] = {"status": "known", "value": False}
    state["current_state"]["opponent_roster_mechanics_context"] = {"session_id": outgoing["session_id"], "side": "opponent", "entries": [target]}
    observed.update({
        "outgoing_owner": outgoing, "session_id": outgoing["session_id"], "incoming_authority": incoming,
        "outgoing_bench_authority": {**observed["outgoing_bench_authority"], "owner": outgoing, "hp_authority": {"status": "known", "current_hp": 100, "maximum_hp": 100}},
        "entry_authority": {**observed["entry_authority"], "hazards": {**observed["entry_authority"]["hazards"], "affected_side": "opponent"}, "target_roster_mechanics": target},
    })
    fp = fingerprint_transition_preview_state(state)
    observed["source_branch_fingerprint"] = fp
    source = _source_result(state, move_id="whirlwind", user_side="self", target_side="opponent")
    request = _materialize(state, source)["forced_switch_request"]
    decision = decide_forced_switch_cancellation(branch_state=state, source_branch_fingerprint=fp, forced_switch_request=request)
    authority = materialize_forced_switch_replacement_authority(branch_state=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, observed_replacement=observed)
    result = execute_allowed_forced_switch(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)
    assert decision["decision"] == "allowed_to_proceed"
    assert result["status"] == "resolved" and result["next_state"]["active"]["opponent"]["pokemon_id"] == "opponent-incoming"


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

    next(row for row in state["branch_persistent_effect_authority"]["states"] if row["family"] == "ingrain" and row["owner"] == _owner(state, "opponent"))["state"] = "known_active"
    opponent_source = _source_result(state, move_id="whirlwind", user_side="self", target_side="opponent")
    opponent_request = _materialize(state, opponent_source)["forced_switch_request"]
    assert decide_forced_switch_cancellation(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), forced_switch_request=opponent_request)["decision"] == "cancelled"


def test_source_and_request_are_stale_after_eot_and_handoff_while_fresh_source_is_accepted():
    pre = _pre(self_hp=50, self_item=None, self_condition="none")
    _ingrain(pre["next_state"], self_state="unknown")
    source_state = pre["next_state"]
    applied = apply_successful_ingrain(branch_state=source_state, source_branch_fingerprint=fingerprint_transition_preview_state(source_state), action_effect=_effect(source_state))
    state = applied["next_state"]
    source = _source_result(state)
    request = _materialize(state, source)["forced_switch_request"]
    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": state, "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner(state, "self"))
    eot_state = eot["next_state"]
    eot_fp = fingerprint_transition_preview_state(eot_state)
    assert materialize_observed_forced_switch_source_application(branch_state=eot_state, source_branch_fingerprint=eot_fp, observed_source_result=source) == {"status": "rejected", "reason": "invalid_observed_forced_switch_source_application"}
    assert materialize_forced_switch_request(branch_state=eot_state, source_branch_fingerprint=eot_fp, observed_request=request)["status"] == "rejected"
    turn_two = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    fp = fingerprint_transition_preview_state(turn_two)
    assert materialize_observed_forced_switch_source_application(branch_state=turn_two, source_branch_fingerprint=fp, observed_source_result=source) == {"status": "rejected", "reason": "invalid_observed_forced_switch_source_application"}
    assert materialize_forced_switch_request(branch_state=turn_two, source_branch_fingerprint=fp, observed_request=request)["status"] == "rejected"
    assert _materialize(turn_two)["status"] == "resolved"


def test_source_driven_hazard_ko_retains_existing_terminal_boundary_without_replay():
    state, observed = _state(hp=1, rock="present")
    fp = fingerprint_transition_preview_state(state)
    request = _materialize(state)["forced_switch_request"]
    decision = decide_forced_switch_cancellation(branch_state=state, source_branch_fingerprint=fp, forced_switch_request=request)
    authority = materialize_forced_switch_replacement_authority(branch_state=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, observed_replacement=observed)
    result = execute_allowed_forced_switch(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)
    assert result["status"] == "unsupported" and result["reason"] == "replacement_required_after_entry_hazard_ko"
    assert result["next_state"]["active"]["self"]["fainted"] is True
    assert execute_allowed_forced_switch(source_branch=result["next_state"], source_branch_fingerprint=result["post_entry_branch_fingerprint"], forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)["status"] == "rejected"


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
