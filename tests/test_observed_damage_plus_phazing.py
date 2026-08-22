"""Dragon Tail/Circle Throw observed damage composes into the forced-switch family."""
from copy import deepcopy

from llm.advisor_forced_switch_execution import execute_allowed_forced_switch
from llm.advisor_forced_switch_replacement import materialize_forced_switch_replacement_authority
from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_observed_damage_plus_phazing import materialize_observed_damage_plus_phazing_result
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _observed, _owner, _state


def _result(state, *, move_id="dragon-tail", user_side="opponent", target_side="self", damage=20, drag_out="drag_out_requested", **changes):
    user, target = _owner(state, user_side), _owner(state, target_side)
    value = {
        "schema_version": "observed-damage-plus-phazing-result-v1", "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user, "target_owner": target,
        "move_id": move_id, "damage_amount": damage, "damaging_hit_result": "applied",
        "drag_out_result": drag_out, "provenance": "trusted_observed_damage_plus_phazing_result_v1",
    }
    value.update(changes)
    return value


def _materialize(state, result=None):
    return materialize_observed_damage_plus_phazing_result(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), observed_result=_result(state) if result is None else result)


def test_dragon_tail_damage_then_f1_request_reuses_allowed_self_forced_execution_idempotently():
    state, observed_replacement = _state(); before = deepcopy(state)
    observation = _result(state); first, repeated = _materialize(state, observation), _materialize(state, observation)
    assert first == repeated and state == before
    assert first["next_state"]["active"]["self"]["current_hp"] == 70
    assert first["forced_switch_request"]["source_branch_fingerprint"] == first["resulting_branch_fingerprint"]
    decision = decide_forced_switch_cancellation(branch_state=first["next_state"], source_branch_fingerprint=first["resulting_branch_fingerprint"], forced_switch_request=first["forced_switch_request"])
    observed_replacement["source_branch_fingerprint"] = first["resulting_branch_fingerprint"]
    observed_replacement["outgoing_bench_authority"]["hp_authority"] = {"status": "known", "current_hp": 70, "maximum_hp": 100}
    authority = materialize_forced_switch_replacement_authority(branch_state=first["next_state"], source_branch_fingerprint=first["resulting_branch_fingerprint"], forced_switch_request=first["forced_switch_request"], cancellation_decision=decision, observed_replacement=observed_replacement)
    executed = execute_allowed_forced_switch(source_branch=first["next_state"], source_branch_fingerprint=first["resulting_branch_fingerprint"], forced_switch_request=first["forced_switch_request"], cancellation_decision=decision, replacement_authority=authority)
    assert decision["decision"] == "allowed_to_proceed" and executed["status"] == "resolved", executed


def test_circle_throw_is_side_neutral_and_ingrain_cancels_only_after_surviving_f1_request():
    state, _ = _state()
    next(row for row in state["branch_persistent_effect_authority"]["states"] if row["family"] == "ingrain" and row["owner"] == _owner(state, "opponent"))["state"] = "known_active"
    result = _materialize(state, _result(state, move_id="circle-throw", user_side="self", target_side="opponent"))
    assert result["status"] == "resolved" and result["next_state"]["active"]["opponent"]["current_hp"] == 80
    decision = decide_forced_switch_cancellation(branch_state=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], forced_switch_request=result["forced_switch_request"])
    assert decision["decision"] == "cancelled"


def test_circle_throw_f1_request_reuses_allowed_opponent_forced_execution():
    state, observed_replacement = _state()
    outgoing = _owner(state, "opponent")
    incoming = deepcopy(observed_replacement["incoming_authority"])
    incoming["owner"] = {"session_id": outgoing["session_id"], "side": "opponent", "slot_index": 1, "pokemon_id": "opponent-incoming"}
    target = deepcopy(observed_replacement["entry_authority"]["target_roster_mechanics"])
    target.update(incoming["owner"]); target["fainted_authority"] = {"status": "known", "value": False}
    state["current_state"]["opponent_roster_mechanics_context"] = {"session_id": outgoing["session_id"], "side": "opponent", "entries": [target]}
    observed_replacement.update({
        "outgoing_owner": outgoing, "session_id": outgoing["session_id"], "incoming_authority": incoming,
        "outgoing_bench_authority": {**observed_replacement["outgoing_bench_authority"], "owner": outgoing, "hp_authority": {"status": "known", "current_hp": 80, "maximum_hp": 100}},
        "entry_authority": {**observed_replacement["entry_authority"], "hazards": {**observed_replacement["entry_authority"]["hazards"], "affected_side": "opponent"}, "target_roster_mechanics": target},
    })
    result = _materialize(state, _result(state, move_id="circle-throw", user_side="self", target_side="opponent"))
    fp = result["resulting_branch_fingerprint"]
    observed_replacement["source_branch_fingerprint"] = fp
    decision = decide_forced_switch_cancellation(branch_state=result["next_state"], source_branch_fingerprint=fp, forced_switch_request=result["forced_switch_request"])
    authority = materialize_forced_switch_replacement_authority(branch_state=result["next_state"], source_branch_fingerprint=fp, forced_switch_request=result["forced_switch_request"], cancellation_decision=decision, observed_replacement=observed_replacement)
    executed = execute_allowed_forced_switch(source_branch=result["next_state"], source_branch_fingerprint=fp, forced_switch_request=result["forced_switch_request"], cancellation_decision=decision, replacement_authority=authority)
    assert decision["decision"] == "allowed_to_proceed" and executed["status"] == "resolved", executed
    assert executed["next_state"]["active"]["opponent"]["pokemon_id"] == "opponent-incoming"


def test_terminal_damage_suppresses_drag_out_and_rejects_stale_replay():
    state, _ = _state()
    observation = _result(state, damage=90, drag_out="not_applied")
    terminal = _materialize(state, observation)
    assert terminal["status"] == "resolved" and terminal["drag_out"] == "not_applied"
    assert terminal["next_state"]["active"]["self"]["current_hp"] == 0 and terminal["next_state"]["active"]["self"]["fainted"] is True
    assert "forced_switch_request" not in terminal
    assert materialize_observed_damage_plus_phazing_result(branch_state=terminal["next_state"], source_branch_fingerprint=terminal["resulting_branch_fingerprint"], observed_result=observation)["status"] == "rejected"
    assert _materialize(state, _result(state, damage=90, drag_out="drag_out_requested")) == {"status": "rejected", "reason": "drag_out_after_terminal_damage"}


def test_only_exact_supported_applied_damage_plus_phazing_results_materialize():
    state, _ = _state(); base = _result(state)
    cases = [
        {**base, "move_id": "roar"}, {**base, "damaging_hit_result": "missed"}, {**base, "drag_out_result": "unresolved"},
        {**base, "damage_amount": 0}, {**base, "source_branch_fingerprint": "stale"}, {**base, "session_id": "foreign"},
        {**base, "user": _owner(state, "self")}, {**base, "target_owner": {**_owner(state, "self"), "pokemon_id": "foreign"}}, {**base, "provenance": "ui_text"},
    ]
    cases.extend({**base, "damaging_hit_result": status} for status in ("failed", "blocked", "unresolved"))
    for candidate in cases:
        assert _materialize(state, candidate) == {"status": "rejected", "reason": "invalid_observed_damage_plus_phazing_result"}
