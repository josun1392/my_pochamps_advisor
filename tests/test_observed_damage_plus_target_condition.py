from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_damage_plus_target_condition import materialize_observed_sludge_bomb
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_leftovers_end_of_turn import _pre


def _owner(state, side):
    return {key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}


def _observation(state, side="self", target="opponent", damage=20, result="applied", **overrides):
    user, target_owner = _owner(state, side), _owner(state, target)
    value = {
        "schema_version": "observed-damage-plus-target-condition-result-v1", "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user, "target_owner": target_owner,
        "move_id": "sludge-bomb", "damage_amount": damage, "damaging_hit_result": "applied",
        "target_condition_result": result, "condition": "poison" if result == "applied" else None,
        "provenance": "trusted_observed_damage_plus_target_condition_result_v1",
    }
    value.update(overrides)
    return value


def _materialize(state, observation=None):
    return materialize_observed_sludge_bomb(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_result=_observation(state) if observation is None else observation,
    )


def test_sludge_bomb_f0_f1_f2_is_side_neutral_and_pure():
    state = _pre(self_condition="none", opponent_condition="none")["next_state"]; baseline = deepcopy(state)
    result = _materialize(state)
    assert result["status"] == "resolved" and state == baseline
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 60
    assert result["next_state"]["predicted_condition_context"]["owner"] == _owner(result["next_state"], "opponent")
    assert result["next_state"]["predicted_condition_context"]["condition_type"] == "poison"
    reverse = _pre(self_condition="none", opponent_condition="none")["next_state"]
    result = _materialize(reverse, _observation(reverse, side="opponent", target="self"))
    assert result["status"] == "resolved" and result["next_state"]["predicted_condition_context"]["owner"]["side"] == "self"


def test_sludge_bomb_condition_eot_handoff_and_replay():
    state = _pre(self_condition="none", opponent_condition="none", opponent_hp=80)["next_state"]
    observation = _observation(state); result = _materialize(state, observation)
    eot = project_per_owner_end_of_turn(
        pre_end_of_turn={"status": "resolved", "source_snapshot_fingerprint": result["f1_branch_fingerprint"], "next_state": result["next_state"], "boundary": {"phase": "pre_end_of_turn"}},
        owner=_owner(result["next_state"], "opponent"),
    )
    assert eot["status"] == "resolved" and any(row.get("effect") == "poison_residual" for row in eot["eot_consequence_trace"])
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    assert handoff["predicted_condition_context"]["condition_type"] == "poison"
    assert materialize_observed_sludge_bomb(branch_state=handoff, source_branch_fingerprint=fingerprint_transition_preview_state(handoff), observed_result=observation)["status"] == "rejected"
    assert _materialize(handoff)["status"] == "rejected"


def test_sludge_bomb_not_applied_conflict_terminal_and_fail_closed():
    state = _pre(self_condition="none", opponent_condition="none")["next_state"]
    stopped = _materialize(state, _observation(state, result="not_applied"))
    assert stopped["status"] == "resolved" and stopped["target_condition"] == "not_applied" and "predicted_condition_context" not in stopped["next_state"]
    existing = _pre(self_condition="none", opponent_condition="burn")["next_state"]
    assert _materialize(existing)["reason"] == "target_existing_condition_conflict"
    terminal = _pre(self_condition="none", opponent_condition="none")["next_state"]
    assert _materialize(terminal, _observation(terminal, damage=80))["reason"] == "condition_after_terminal_damage"
    for invalid in (
        _observation(state, move_id="water-gun"), _observation(state, condition="burn"),
        _observation(state, target_condition_result="unknown"), _observation(state, damage_amount=-1),
        _observation(state, provenance="forged"), _observation(state, user={**_owner(state, "self"), "pokemon_id": "foreign"}),
    ):
        assert _materialize(state, invalid)["status"] == "rejected"
    missing = _pre(self_condition="none", opponent_condition="none")["next_state"]
    missing["active"]["opponent"]["current_hp"] = None
    assert _materialize(missing)["status"] == "rejected"
