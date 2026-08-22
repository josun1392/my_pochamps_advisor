from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_damage_application import apply_exact_observed_self_stage_consequence
from llm.advisor_observed_damage_plus_self_stage import materialize_observed_flame_charge
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _owner, _state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _pre


def _observation(state, side="self", target="opponent", damage=20, stage_result="applied", **overrides):
    user, target_owner = _owner(state, side), _owner(state, target)
    result = {
        "schema_version": "observed-damage-plus-self-stage-result-v1", "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user,
        "target_owner": target_owner, "move_id": "flame-charge", "damage_amount": damage,
        "damaging_hit_result": "applied", "self_stage_result": stage_result,
        "stat": "speed" if stage_result == "applied" else None,
        "stage_delta": 1 if stage_result == "applied" else None,
        "provenance": "trusted_observed_damage_plus_self_stage_result_v1",
    }
    result.update(overrides)
    return result


def _materialize(state, observation=None):
    return materialize_observed_flame_charge(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_result=_observation(state) if observation is None else observation,
    )


def _with_stages(state):
    state.setdefault("current_state", {})["stat_stage_context"] = {
        "current_stages": [
            {"side": side, "stat": "speed", "stage": 0, "status": "user_confirmed",
             "source": "user_confirmed_current_stat_stage", "confidence": "known"}
            for side in ("self", "opponent")
        ]
    }
    return state


def _stage(state, side):
    return next(row["stage"] for row in state["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == side and row["stat"] == "speed")


def test_flame_charge_applies_exact_side_neutral_f0_f1_f2_stage_change():
    state, _ = _state(); _with_stages(state); baseline = deepcopy(state)
    result = _materialize(state)
    assert result["status"] == "resolved" and state == baseline
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 80
    assert _stage(result["next_state"], "self") == 1
    state, _ = _state(); _with_stages(state)
    reverse = _materialize(state, _observation(state, side="opponent", target="self"))
    assert reverse["status"] == "resolved" and _stage(reverse["next_state"], "opponent") == 1


def test_flame_charge_ko_cap_not_applied_and_replay_boundaries():
    state, _ = _state(); _with_stages(state)
    observation = _observation(state, damage=100)
    result = _materialize(state, observation)
    assert result["next_state"]["active"]["opponent"]["fainted"] and _stage(result["next_state"], "self") == 1
    assert _materialize(result["next_state"], observation)["status"] == "rejected"
    assert apply_exact_observed_self_stage_consequence(branch_state=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], stage_authority=result["self_stage_authority"])["status"] == "rejected"
    state, _ = _state(); _with_stages(state); next(row for row in state["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "self" and row["stat"] == "speed")["stage"] = 6
    stopped = _materialize(state, _observation(state, stage_result="not_applied"))
    assert stopped["status"] == "resolved" and stopped["self_stage"] == "not_applied" and _stage(stopped["next_state"], "self") == 6 and "self_stage_authority" not in stopped


def test_flame_charge_stage_handoff_and_fail_closed():
    pre = _pre(self_hp=50, self_item=None, self_condition="none")
    _ingrain(pre["next_state"], self_state="unknown")
    state = apply_successful_ingrain(branch_state=pre["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(pre["next_state"]), action_effect=_effect(pre["next_state"]))["next_state"]
    _with_stages(state); observation = _observation(state); result = _materialize(state, observation)
    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": result["next_state"], "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner(result["next_state"], "self"))
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    assert _stage(handoff, "self") == 1
    assert materialize_observed_flame_charge(branch_state=handoff, source_branch_fingerprint=fingerprint_transition_preview_state(handoff), observed_result=observation)["status"] == "rejected"
    assert _materialize(handoff)["status"] == "resolved"
    state, _ = _state(); _with_stages(state)
    for invalid in (
        _observation(state, move_id="water-gun"), _observation(state, self_stage_result="unknown"),
        _observation(state, stat="attack"), _observation(state, stage_delta=2),
        _observation(state, provenance="untrusted"), _observation(state, damage_amount=-1),
    ):
        assert _materialize(state, invalid)["status"] == "rejected"
    state, _ = _state(); _with_stages(state); next(row for row in state["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "self" and row["stat"] == "speed")["stage"] = None
    assert _materialize(state)["status"] == "rejected"


def test_flame_charge_rejects_foreign_owners_hp_and_forged_f1_stage_authority():
    state, _ = _state(); _with_stages(state)
    foreign_user = _observation(state); foreign_user["user"] = {**foreign_user["user"], "pokemon_id": "foreign"}
    foreign_target = _observation(state); foreign_target["target_owner"] = {**foreign_target["target_owner"], "slot_index": 99}
    malformed_hp, _ = _state(); _with_stages(malformed_hp); malformed_hp["active"]["opponent"]["current_hp"] = None
    assert _materialize(state, foreign_user)["status"] == "rejected"
    assert _materialize(state, foreign_target)["status"] == "rejected"
    assert _materialize(malformed_hp)["status"] == "rejected"
    result = _materialize(state)
    forged = {**result["self_stage_authority"], "provenance": "forged"}
    assert apply_exact_observed_self_stage_consequence(
        branch_state=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"],
        stage_authority=forged,
    )["status"] == "rejected"
