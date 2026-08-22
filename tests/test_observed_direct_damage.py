"""Trusted observed Water Gun results reuse the shared exact damage core."""
from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_direct_damage import materialize_observed_direct_damage_result
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _owner, _state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _pre


def _result(state, *, user_side="self", target_side="opponent", damage=20, **changes):
    user, target = _owner(state, user_side), _owner(state, target_side)
    value = {
        "schema_version": "observed-direct-damage-result-v1", "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user,
        "target_owner": target, "move_id": "water-gun", "damage_amount": damage,
        "damaging_hit_result": "applied", "provenance": "trusted_observed_direct_damage_result_v1",
    }
    value.update(changes)
    return value


def _materialize(state, observation=None):
    return materialize_observed_direct_damage_result(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_result=_result(state) if observation is None else observation,
    )


def test_water_gun_observation_is_side_neutral_pure_and_stops_at_f1():
    state, _ = _state(); before = deepcopy(state)
    self_to_opponent = _materialize(state); repeated = _materialize(state)
    assert self_to_opponent == repeated and state == before
    assert self_to_opponent["next_state"]["active"]["opponent"]["current_hp"] == 80
    assert self_to_opponent["secondary_effects"] == "out_of_scope"

    opponent_to_self = _materialize(state, _result(state, user_side="opponent", target_side="self"))
    assert opponent_to_self["next_state"]["active"]["self"]["current_hp"] == 70


def test_water_gun_ko_and_f0_replay_boundary_are_exact():
    state, _ = _state()
    observation = _result(state, damage=100)
    result = _materialize(state, observation)
    assert result["damage_application"]["target_fainted"] is True
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 0
    assert result["next_state"]["active"]["opponent"]["fainted"] is True
    assert materialize_observed_direct_damage_result(
        branch_state=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], observed_result=observation,
    )["status"] == "rejected"


def test_direct_damage_evidence_is_stale_after_same_turn_eot_and_handoff_but_fresh_turn_two_is_valid():
    pre = _pre(self_hp=50, self_item=None, self_condition="none")
    _ingrain(pre["next_state"], self_state="unknown")
    applied = apply_successful_ingrain(branch_state=pre["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(pre["next_state"]), action_effect=_effect(pre["next_state"]))
    f0 = applied["next_state"]
    observation = _result(f0)
    f1 = _materialize(f0, observation)
    f2 = deepcopy(f1["next_state"])
    f2["active"]["self"]["current_hp"] -= 1
    assert materialize_observed_direct_damage_result(branch_state=f2, source_branch_fingerprint=fingerprint_transition_preview_state(f2), observed_result=observation)["status"] == "rejected"

    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": f1["next_state"], "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner(f1["next_state"], "self"))
    eot_state, eot_fp = eot["next_state"], eot["resulting_branch_fingerprint"]
    assert materialize_observed_direct_damage_result(branch_state=eot_state, source_branch_fingerprint=eot_fp, observed_result=observation)["status"] == "rejected"
    turn_two = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    turn_two_fp = fingerprint_transition_preview_state(turn_two)
    assert materialize_observed_direct_damage_result(branch_state=turn_two, source_branch_fingerprint=turn_two_fp, observed_result=observation)["status"] == "rejected"
    assert _materialize(turn_two)["status"] == "resolved"


def test_only_exact_trusted_applied_water_gun_results_materialize():
    state, _ = _state(); base = _result(state)
    cases = [
        {**base, "move_id": "tackle"}, {**base, "damaging_hit_result": "missed"},
        {**base, "damaging_hit_result": "failed"}, {**base, "damaging_hit_result": "unresolved"},
        {**base, "damage_amount": 0}, {**base, "damage_amount": -1},
        {**base, "source_branch_fingerprint": "stale"}, {**base, "session_id": "foreign"},
        {**base, "user": _owner(state, "opponent")},
        {**base, "target_owner": {**_owner(state, "opponent"), "pokemon_id": "foreign"}},
        {**base, "provenance": "ui_text"},
    ]
    for candidate in cases:
        assert _materialize(state, candidate)["status"] == "rejected"


def test_missing_or_malformed_target_hp_fails_closed_before_direct_damage():
    for field, value in (("current_hp", None), ("max_hp", None), ("current_hp", True)):
        state, _ = _state()
        state["active"]["opponent"][field] = value
        assert _materialize(state) == {"status": "rejected", "reason": "invalid_observed_damage_authority"}
