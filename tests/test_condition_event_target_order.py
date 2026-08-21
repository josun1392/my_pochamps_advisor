"""Trusted cross-owner tier-nine condition target-order coverage."""
from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_cross_owner_condition_end_of_turn, project_cross_owner_weather_phase
from tests.test_weather_event_target_order import _pre as weather_pre, _projection as weather_projection
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import _project_bounded_eot


def _owner(side, pokemon, hp):
    return {"session_id": "condition-order", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": hp, "max_hp": 100, "fainted": hp == 0}


def _pre(*, self_condition="poison", opponent_condition="poison", self_ability="blaze", opponent_ability="blaze", self_hp=50, opponent_hp=50, toxic_opponent=False):
    state = {"schema_version": "deterministic-transition-preview-v1", "active": {"self": _owner("self", "first", self_hp), "opponent": _owner("opponent", "second", opponent_hp)}, "current_state": {"current_state_session_id": "condition-order", "current_hp_context": {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": opponent_hp, "maximum_hp": 100}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": self_condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none" if toxic_opponent else opponent_condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": self_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": opponent_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}}}
    root = fingerprint_transition_preview_state(state)
    if toxic_opponent:
        owner = {key: state["active"]["opponent"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
        state["predicted_condition_context"] = {"schema_version": "hypothetical-move-poison-condition-v1", "source_snapshot_fingerprint": root, "branch_state_fingerprint": "application", "owner": owner, "condition_type": "toxic", "provenance": "turn_engine_predicted_move_poison"}
        state["predicted_toxic_lifecycle"] = {"schema_version": "hypothetical-predictive-toxic-lifecycle-v1", "source_snapshot_fingerprint": root, "branch_state_fingerprint": "application", "owner": owner, "current_stage": 1, "provenance": "turn_engine_predicted_toxic_application"}
    return {"status": "resolved", "source_snapshot_fingerprint": root, "next_state": state, "boundary": {"phase": "pre_end_of_turn"}}


def _projection(pre, sides=("self", "opponent")):
    state = pre["next_state"]
    return {"schema_version": "detached-condition-event-target-order-v1", "status": "known", "session_id": "condition-order", "event_family": "ResidualConditionTier9", "source_branch_fingerprint": fingerprint_transition_preview_state(state), "ordered_active_owners": [{key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")} for side in sides], "provenance": "trusted_canonical_showdown_condition_residual_target_order"}


def test_cross_owner_condition_plan_is_frozen_sequential_and_survives_handoff():
    pre = _pre(); before = deepcopy(pre); order = _projection(pre, ("opponent", "self"))
    result = project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=order)
    assert result["status"] == "resolved", result
    assert [row["owner"]["side"] for row in result["eot_consequence_trace"]] == ["opponent", "self"]
    assert result["eot_consequence_trace"][1]["branch_fingerprint_consumed"] != result["eot_consequence_trace"][0]["branch_fingerprint_consumed"]
    assert result["next_state"]["active"]["self"]["current_hp"] == result["next_state"]["active"]["opponent"]["current_hp"] == 38
    assert pre == before
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved" and handoff["next_state"]["active"]["opponent"]["current_hp"] == 38
    assert _project_bounded_eot(pre_end_of_turn=pre, condition_event_target_order=order)["resulting_branch_fingerprint"] == result["resulting_branch_fingerprint"]


def test_lethal_first_owner_continues_to_toxic_owner_and_preserves_lifecycle():
    pre = _pre(self_hp=12, opponent_hp=50, toxic_opponent=True)
    result = project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=_projection(pre))
    assert result["status"] == "resolved", result
    assert result["next_state"]["active"]["self"]["fainted"] is True
    toxic = result["eot_consequence_trace"][1]
    assert (toxic["owner"]["side"], toxic["condition"], toxic["post_hp"], toxic["resulting_toxic_stage"]) == ("opponent", "toxic", 44, 2)


def test_poison_heal_is_one_compound_event_and_invalid_plans_fail_closed():
    pre = _pre(self_ability="poison-heal", self_hp=50, opponent_hp=50); order = _projection(pre)
    result = project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=order)
    assert result["status"] == "resolved"
    assert result["eot_consequence_trace"][0]["effect"] == "poison_heal_recovery"
    assert result["next_state"]["active"]["self"]["current_hp"] == 62
    assert project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=None) == {"status": "incomplete", "reason": "cross_owner_condition_order_unrepresented"}
    stale = deepcopy(order); stale["source_branch_fingerprint"] = "stale"
    assert project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=stale) == {"status": "rejected", "reason": "stale_or_foreign_condition_event_target_order"}
    duplicate = deepcopy(order); duplicate["ordered_active_owners"][1] = deepcopy(duplicate["ordered_active_owners"][0])
    assert project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=duplicate) == {"status": "rejected", "reason": "invalid_condition_event_target_order_owners"}
    untrusted = deepcopy(order); untrusted["provenance"] = "hand_authored"
    assert project_cross_owner_condition_end_of_turn(pre_end_of_turn=pre, condition_event_target_order=untrusted) == {"status": "incomplete", "reason": "cross_owner_condition_order_unrepresented"}


def test_weather_phase_result_is_the_exact_condition_projection_source():
    pre = weather_pre()
    pre["next_state"]["current_state"]["condition_context"]["current_conditions"][1]["condition_type"] = "poison"
    weather = project_cross_owner_weather_phase(pre_end_of_turn=pre, weather_event_target_order=weather_projection(pre))
    assert weather["status"] == "resolved", weather
    state = weather["next_state"]
    order = {"schema_version": "detached-condition-event-target-order-v1", "status": "known", "session_id": "weather-order", "event_family": "ResidualConditionTier9", "source_branch_fingerprint": weather["resulting_branch_fingerprint"], "ordered_active_owners": [{key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")} for side in ("opponent", "self")], "provenance": "trusted_canonical_showdown_condition_residual_target_order"}
    post_weather = {"status": "resolved", "source_snapshot_fingerprint": pre["source_snapshot_fingerprint"], "next_state": state, "boundary": {"phase": "pre_end_of_turn"}}
    result = project_cross_owner_condition_end_of_turn(pre_end_of_turn=post_weather, condition_event_target_order=order)
    assert result["status"] == "resolved", result
    assert result["eot_consequence_trace"][0]["branch_fingerprint_consumed"] == weather["resulting_branch_fingerprint"]
