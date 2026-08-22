from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_damage_application import apply_exact_observed_target_stage_consequence
from llm.advisor_observed_damage_plus_target_stage import materialize_observed_acid_spray
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _owner, _state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _pre


def _with_stages(state, self_stage=0, opponent_stage=0):
    state.setdefault("current_state", {})["stat_stage_context"] = {"current_stages": [
        {"side": side, "stat": "special-defense", "stage": stage, "status": "user_confirmed",
         "source": "user_confirmed_current_stat_stage", "confidence": "known"}
        for side, stage in (("self", self_stage), ("opponent", opponent_stage))
    ]}
    return state


def _stage(state, side):
    return next(row["stage"] for row in state["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == side and row["stat"] == "special-defense")


def _observation(state, side="self", target="opponent", damage=20, result="applied", **overrides):
    user, target_owner = _owner(state, side), _owner(state, target)
    value = {
        "schema_version": "observed-damage-plus-target-stage-result-v1", "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user, "target_owner": target_owner,
        "move_id": "acid-spray", "damage_amount": damage, "damaging_hit_result": "applied",
        "target_stage_result": result, "stat": "special-defense" if result == "applied" else None,
        "stage_delta": -2 if result == "applied" else None,
        "provenance": "trusted_observed_damage_plus_target_stage_result_v1",
    }
    value.update(overrides)
    return value


def _materialize(state, observation=None):
    return materialize_observed_acid_spray(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_result=_observation(state) if observation is None else observation,
    )


def test_acid_spray_f0_f1_f2_is_side_neutral_and_pure():
    state, _ = _state(); _with_stages(state); baseline = deepcopy(state)
    result = _materialize(state)
    assert result["status"] == "resolved" and state == baseline
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 80
    assert _stage(result["next_state"], "opponent") == -2
    state, _ = _state(); _with_stages(state)
    reverse = _materialize(state, _observation(state, side="opponent", target="self"))
    assert reverse["status"] == "resolved" and _stage(reverse["next_state"], "self") == -2


def test_acid_spray_composes_current_stage_and_respects_bound_and_replay():
    state, _ = _state(); _with_stages(state)
    observation = _observation(state); first = _materialize(state, observation)
    assert _stage(first["next_state"], "opponent") == -2
    second = _materialize(first["next_state"])
    assert second["status"] == "resolved" and _stage(second["next_state"], "opponent") == -4
    assert _materialize(first["next_state"], observation)["status"] == "rejected"
    assert apply_exact_observed_target_stage_consequence(
        branch_state=first["next_state"], source_branch_fingerprint=first["resulting_branch_fingerprint"],
        stage_authority=first["target_stage_authority"],
    )["status"] == "rejected"
    floor, _ = _state(); _with_stages(floor, opponent_stage=-6)
    assert _materialize(floor)["reason"] == "target_stage_already_at_bound"
    near, _ = _state(); _with_stages(near, opponent_stage=-5)
    capped = _materialize(near)
    assert capped["status"] == "resolved" and _stage(capped["next_state"], "opponent") == -6


def test_acid_spray_composes_a_matching_detached_stage_overlay():
    state, _ = _state(); _with_stages(state)
    target = _owner(state, "self")
    state["predicted_stage_context"] = {
        "schema_version": "hypothetical-self-stage-v1", "owner": target,
        "stat": "special-defense", "previous_stage": 0, "delta": -1, "projected_stage": -1,
    }
    result = _materialize(state, _observation(state, side="opponent", target="self"))
    assert result["status"] == "resolved" and _stage(result["next_state"], "self") == -3
    assert "predicted_stage_context" not in result["next_state"]


def test_acid_spray_not_applied_terminal_and_fail_closed():
    state, _ = _state(); _with_stages(state)
    stopped = _materialize(state, _observation(state, result="not_applied"))
    assert stopped["status"] == "resolved" and stopped["target_stage"] == "not_applied" and _stage(stopped["next_state"], "opponent") == 0
    terminal, _ = _state(); _with_stages(terminal)
    assert _materialize(terminal, _observation(terminal, damage=100))["reason"] == "target_stage_after_terminal_damage"
    for invalid in (
        _observation(state, move_id="water-gun"), _observation(state, stat="special-attack"),
        _observation(state, stage_delta=-1), _observation(state, target_stage_result="unknown"),
        _observation(state, damage_amount=-1), _observation(state, provenance="forged"),
        _observation(state, user={**_owner(state, "self"), "pokemon_id": "foreign"}),
    ):
        assert _materialize(state, invalid)["status"] == "rejected"
    malformed, _ = _state(); _with_stages(malformed)
    malformed["active"]["opponent"]["current_hp"] = None
    assert _materialize(malformed)["status"] == "rejected"
    unknown_stage, _ = _state(); _with_stages(unknown_stage)
    next(row for row in unknown_stage["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "opponent")["stage"] = None
    assert _materialize(unknown_stage)["status"] == "rejected"


def test_acid_spray_stage_persists_through_handoff_and_old_authority_is_stale():
    pre = _pre(self_hp=50, self_item=None, self_condition="none")
    _ingrain(pre["next_state"], self_state="unknown")
    state = apply_successful_ingrain(branch_state=pre["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(pre["next_state"]), action_effect=_effect(pre["next_state"]))["next_state"]
    _with_stages(state); observation = _observation(state); result = _materialize(state, observation)
    eot = project_per_owner_end_of_turn(
        pre_end_of_turn={"status": "resolved", "next_state": result["next_state"], "boundary": {"phase": "pre_end_of_turn"}},
        owner=_owner(result["next_state"], "self"),
    )
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    assert _stage(handoff, "opponent") == -2
    assert materialize_observed_acid_spray(
        branch_state=handoff, source_branch_fingerprint=fingerprint_transition_preview_state(handoff), observed_result=observation,
    )["status"] == "rejected"
    assert _materialize(handoff)["status"] == "resolved"
