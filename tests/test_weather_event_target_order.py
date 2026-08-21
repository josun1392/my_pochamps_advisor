"""Trusted Weather-event target order projection coverage."""
from copy import deepcopy

from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_per_owner_eot import project_cross_owner_weather_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import _project_bounded_eot


def _owner(side, pokemon, hp):
    return {"session_id": "weather-order", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": hp, "max_hp": 100, "fainted": hp == 0}


def _pre(*, weather="rain", self_ability="rain-dish", opponent_ability="dry-skin", self_hp=50):
    state = {"schema_version": "deterministic-transition-preview-v1", "active": {"self": _owner("self", "first", self_hp), "opponent": _owner("opponent", "second", 80)}, "current_state": {"current_state_session_id": "weather-order", "field_state_context": {"current_field": {"weather": "none", "side_effects": []}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": 80, "maximum_hp": 100}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": self_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": opponent_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": "poison", "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "direct_mechanics_context": {"attacker": {"current_hp": self_hp, "max_hp": 100, "item": {"status": "known_absent"}}, "defender": {"current_hp": 80, "max_hp": 100, "item": {"status": "known_absent"}}}}}
    root = fingerprint_transition_preview_state(state)
    field = project_field_weather(branch_state=state, source_fingerprint=root, frozen_field_state={"current_field": {"weather": "none", "side_effects": []}})
    weather_branch = apply_supported_switch_entry_weather(branch_state=field["next_state"], source_fingerprint=field["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "none", "weather_after": weather})
    return {"status": "resolved", "source_snapshot_fingerprint": root, "next_state": weather_branch["next_state"], "boundary": {"phase": "pre_end_of_turn"}}


def _projection(pre, sides=("self", "opponent")):
    state = pre["next_state"]
    return {"schema_version": "detached-weather-event-target-order-v1", "status": "known", "session_id": "weather-order", "event_family": "Weather", "source_branch_fingerprint": fingerprint_transition_preview_state(state), "ordered_active_owners": [{key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")} for side in sides], "provenance": "trusted_canonical_showdown_weather_event_target_order"}


def test_frozen_cross_owner_weather_plan_executes_in_projected_order_then_tier_nine():
    pre = _pre(); before = deepcopy(pre); order = _projection(pre, ("opponent", "self"))
    result = project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=order)
    assert result["status"] == "resolved", result
    weather = result["eot_consequence_trace"][:2]
    assert [row["owner"]["side"] for row in weather] == ["opponent", "self"]
    assert weather[1]["branch_fingerprint_consumed"] != weather[0]["branch_fingerprint_consumed"]
    assert result["eot_consequence_trace"][2]["effect"] == "poison_residual"
    assert result["eot_consequence_trace"][2]["pre_hp"] == 56
    assert result["next_state"]["active"]["self"]["current_hp"] == 44
    assert pre == before
    assert _project_bounded_eot(pre_end_of_turn=pre, weather_event_target_order=order)["resulting_branch_fingerprint"] == result["resulting_branch_fingerprint"]
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved" and handoff["next_state"]["active"]["self"]["current_hp"] == 44


def test_lethal_first_weather_target_does_not_suppress_later_target():
    pre = _pre(weather="sun", self_ability="solar-power", opponent_ability="solar-power", self_hp=12)
    result = project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=_projection(pre))
    assert result["status"] == "resolved", result
    assert result["next_state"]["active"]["self"]["fainted"] is True
    assert result["eot_consequence_trace"][1]["owner"]["side"] == "opponent"
    assert result["eot_consequence_trace"][1]["post_hp"] == 68


def test_projection_rejects_missing_stale_foreign_duplicate_and_untrusted_authority():
    pre = _pre(); order = _projection(pre)
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=None) == {"status": "incomplete", "reason": "cross_owner_weather_order_unrepresented"}
    stale = deepcopy(order); stale["source_branch_fingerprint"] = "stale"
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=stale) == {"status": "rejected", "reason": "stale_or_foreign_weather_event_target_order"}
    duplicate = deepcopy(order); duplicate["ordered_active_owners"][1] = deepcopy(duplicate["ordered_active_owners"][0])
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=duplicate) == {"status": "rejected", "reason": "invalid_weather_event_target_order_owners"}
    foreign = deepcopy(order); foreign["ordered_active_owners"][1]["pokemon_id"] = "foreign"
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=foreign) == {"status": "rejected", "reason": "invalid_weather_event_target_order_owners"}
    untrusted = deepcopy(order); untrusted["provenance"] = "hand_authored"
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=untrusted) == {"status": "incomplete", "reason": "cross_owner_weather_order_unrepresented"}
    completed = project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=order)
    reused = {"status": "resolved", "source_snapshot_fingerprint": pre["source_snapshot_fingerprint"], "next_state": completed["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=reused, weather_event_target_order=order) == {"status": "rejected", "reason": "stale_or_foreign_weather_event_target_order"}
