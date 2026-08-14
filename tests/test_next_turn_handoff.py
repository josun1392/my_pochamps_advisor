from copy import deepcopy

from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _pre_eot(*, condition="poison", hp=80, maximum=160, toxic=False):
    owner = lambda side, pokemon, slot: {"session_id": "handoff-session", "side": side, "slot_index": slot, "pokemon_id": pokemon}
    self_owner = owner("self", "pikachu", 0)
    state = {
        "schema_version": "deterministic-transition-preview-v1",
        "active": {"self": {**self_owner, "current_hp": hp, "max_hp": maximum, "fainted": False}, "opponent": {**owner("opponent", "arcanine", 1), "current_hp": 100, "max_hp": 100, "fainted": False}},
        "current_state": {
            "current_hp_context": {"current_hp": [{"side": "self", "current_hp": hp, "maximum_hp": maximum}, {"side": "opponent", "current_hp": 100, "maximum_hp": 100}]},
            "condition_context": {"current_conditions": [{"side": "self", "condition_type": "none" if toxic else condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]},
            "ability_context": {"current_abilities": [{"side": "self", "ability": "blaze", "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": "blaze", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]},
            "stat_stage_context": {"self": {"attack": 2}, "opponent": {"attack": 0}},
        },
    }
    if toxic:
        state["predicted_condition_context"] = {"schema_version": "hypothetical-move-poison-condition-v1", "source_snapshot_fingerprint": "source", "branch_state_fingerprint": "before-eot", "owner": self_owner, "condition_type": "toxic", "provenance": "turn_engine_predicted_move_poison"}
        state["predicted_toxic_lifecycle"] = {"schema_version": "hypothetical-predictive-toxic-lifecycle-v1", "source_snapshot_fingerprint": "source", "branch_state_fingerprint": "before-eot", "owner": self_owner, "current_stage": 1, "provenance": "turn_engine_predicted_toxic_application"}
    return {"source_snapshot_fingerprint": "source", "next_state": state, "boundary": {"phase": "pre_end_of_turn"}}


def _eot(**kwargs):
    result = project_poison_end_of_turn(pre_end_of_turn=_pre_eot(**kwargs))
    assert result["status"] == "resolved"
    return result


def test_handoff_carries_persistent_state_and_excludes_completed_turn_evidence_detached():
    eot = _eot()
    eot["next_state"]["current_state"].update({"direct_mechanics_context": {"old": True}, "same_turn_event_context": {"old": True}, "selected_actions": {"old": True}})
    eot["next_state"]["action_order"] = {"status": "acts_first"}
    eot["resulting_branch_fingerprint"] = fingerprint_transition_preview_state(eot["next_state"])
    before = deepcopy(eot)
    result = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)
    assert result["status"] == "resolved" and result["boundary"] == {"phase": "next_turn_start"}
    state = result["next_state"]
    assert state["active"]["self"]["current_hp"] == 60
    assert state["current_state"]["stat_stage_context"]["self"]["attack"] == 2
    assert "direct_mechanics_context" not in state["current_state"] and "same_turn_event_context" not in state["current_state"] and "action_order" not in state
    assert eot == before and result["resulting_branch_fingerprint"] != eot["resulting_branch_fingerprint"]


def test_handoff_keeps_toxic_stage_two_without_new_residual_or_reducer_writeback():
    eot = _eot(toxic=True)
    before = deepcopy(eot)
    result = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)
    assert result["status"] == "resolved"
    state = result["next_state"]
    assert state["active"]["self"]["current_hp"] == 70
    assert state["predicted_toxic_lifecycle"]["current_stage"] == 2
    assert state["predicted_condition_context"]["condition_type"] == "toxic"
    assert eot == before and state["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] == "none"


def test_handoff_preserves_faint_and_rejects_stale_fingerprint_or_mismatched_lifecycle_owner():
    eot = _eot(hp=20)
    result = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["self"]["fainted"] is True
    assert result["lifecycle_trace"][0]["requires_replacement_before_action"] == ["self"]

    stale = deepcopy(eot); stale["resulting_branch_fingerprint"] = "wrong"
    assert handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=stale) == {"status": "rejected", "reason": "stale_or_invalid_end_of_turn_fingerprint"}
    toxic = _eot(toxic=True); toxic["next_state"]["predicted_toxic_lifecycle"]["owner"] = {"session_id": "bad"}
    toxic["resulting_branch_fingerprint"] = fingerprint_transition_preview_state(toxic["next_state"])
    assert handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=toxic) == {"status": "rejected", "reason": "stale_or_mismatched_predicted_toxic_lifecycle"}
