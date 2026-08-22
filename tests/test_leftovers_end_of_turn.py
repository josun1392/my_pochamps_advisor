"""Detached Leftovers tier-five adapter and ordering coverage."""
from copy import deepcopy

from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_leftovers_end_of_turn import apply_owner_leftovers_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_cross_owner_weather_end_of_turn, project_per_owner_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import _project_bounded_eot
from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority


def _owner(side, pokemon, hp=50):
    return {"session_id": "leftovers-eot", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": hp, "max_hp": 100, "fainted": hp == 0}


def _pre(*, self_hp=50, opponent_hp=80, self_item="leftovers", opponent_item=None, weather="none", self_ability="pressure", opponent_ability="pressure", self_condition="poison", opponent_condition="none"):
    item = lambda value: {"status": "known", "value": value} if value is not None else {"status": "known_absent"}
    state = {"schema_version": "deterministic-transition-preview-v1", "active": {"self": _owner("self", "holder", self_hp), "opponent": _owner("opponent", "other", opponent_hp)}, "current_state": {"current_state_session_id": "leftovers-eot", "field_state_context": {"current_field": {"weather": "none", "side_effects": []}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": opponent_hp, "maximum_hp": 100}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": self_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": opponent_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": self_condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": opponent_condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "direct_mechanics_context": {"attacker": {"current_hp": self_hp, "max_hp": 100, "item": item(self_item)}, "defender": {"current_hp": opponent_hp, "max_hp": 100, "item": item(opponent_item)}}}}
    root = fingerprint_transition_preview_state(state)
    field = project_field_weather(branch_state=state, source_fingerprint=root, frozen_field_state={"current_field": {"weather": "none", "side_effects": []}})
    if weather != "none":
        field = apply_supported_switch_entry_weather(branch_state=field["next_state"], source_fingerprint=field["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "none", "weather_after": weather})
    owners={side:{key:field["next_state"]["active"][side][key] for key in ("session_id","side","slot_index","pokemon_id")} for side in ("self","opponent")}
    field["next_state"]["branch_persistent_effect_authority"]=materialize_persistent_effect_authority(owners=owners,source_branch_fingerprint="trusted-explicit-inactive",states={side:{family:{"state":"known_inactive"} for family in ("aqua_ring","ingrain","leech_seed")} for side in ("self","opponent")})
    return {"status": "resolved", "source_snapshot_fingerprint": root, "next_state": field["next_state"], "boundary": {"phase": "pre_end_of_turn"}}


def _owner_id(state, side):
    return {key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}


def _projection(pre, sides=("self", "opponent")):
    state = pre["next_state"]
    return {"schema_version": "detached-item-residual-target-order-v1", "status": "known", "session_id": "leftovers-eot", "event_family": "ResidualItemTier5", "source_branch_fingerprint": fingerprint_transition_preview_state(state), "ordered_active_owners": [_owner_id(state, side) for side in sides], "provenance": "trusted_canonical_showdown_item_residual_target_order"}


def test_leftovers_recovery_cap_full_hp_and_strict_item_owner_binding():
    pre = _pre(self_hp=94, self_condition="none")
    state = deepcopy(pre["next_state"]); owner = _owner_id(state, "self"); fp = fingerprint_transition_preview_state(state)
    result = apply_owner_leftovers_end_of_turn(state=state, side="self", owner=owner, source_branch_fingerprint=fp)
    assert result["status"] == "resolved" and result["trace"]["recovery"] == 6 and result["trace"]["post_hp"] == 100
    full = _pre(self_hp=100, self_condition="none"); result = project_per_owner_end_of_turn(pre_end_of_turn=full, owner=_owner_id(full["next_state"], "self"))
    assert result["status"] == "resolved" and result["eot_consequence_trace"][0]["outcome"] == "already_full_hp"
    unknown = deepcopy(pre); unknown["next_state"]["current_state"]["direct_mechanics_context"]["attacker"]["item"] = {"status": "unknown"}
    assert apply_owner_leftovers_end_of_turn(state=unknown["next_state"], side="self", owner=owner, source_branch_fingerprint=fingerprint_transition_preview_state(unknown["next_state"])) == {"status": "incomplete", "reason": "leftovers_current_item_authority"}
    assert apply_owner_leftovers_end_of_turn(state=pre["next_state"], side="self", owner={**owner, "pokemon_id": "foreign"}, source_branch_fingerprint=fingerprint_transition_preview_state(pre["next_state"])) == {"status": "rejected", "reason": "stale_or_foreign_leftovers_owner"}
    fainted = _pre(self_hp=0, self_condition="none")
    assert apply_owner_leftovers_end_of_turn(state=fainted["next_state"], side="self", owner=_owner_id(fainted["next_state"], "self"), source_branch_fingerprint=fingerprint_transition_preview_state(fainted["next_state"])) == {"status": "rejected", "reason": "leftovers_fainted_owner"}


def test_weather_leftovers_then_poison_is_sequential_and_handoffs_final_hp():
    pre = _pre(self_hp=50, weather="snow", self_ability="ice-body")
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner=_owner_id(pre["next_state"], "self"))
    assert result["status"] == "resolved", result
    assert [(row["tier"], row["effect"]) for row in result["eot_consequence_trace"]] == [(1, "ice_body_recovery"), (5, "leftovers_recovery"), (9, "poison_residual")]
    weather, leftovers, poison = result["eot_consequence_trace"]
    assert (weather["post_hp"], leftovers["pre_hp"], leftovers["post_hp"], poison["pre_hp"], poison["post_hp"]) == (56, 56, 62, 62, 50)
    assert leftovers["branch_fingerprint_consumed"] != weather["branch_fingerprint_consumed"] and poison["branch_fingerprint_consumed"] != leftovers["branch_fingerprint_consumed"]
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved" and handoff["next_state"]["active"]["self"]["current_hp"] == 50


def test_cross_owner_leftovers_uses_frozen_order_and_invalid_authority_fails_closed():
    pre = _pre(self_item="leftovers", opponent_item="leftovers", self_condition="none", opponent_condition="none")
    order = _projection(pre, ("opponent", "self"))
    result = project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order={"schema_version": "detached-weather-event-target-order-v1", "status": "known", "session_id": "leftovers-eot", "event_family": "Weather", "source_branch_fingerprint": fingerprint_transition_preview_state(pre["next_state"]), "ordered_active_owners": [_owner_id(pre["next_state"], side) for side in ("self", "opponent")], "provenance": "trusted_canonical_showdown_weather_event_target_order"}, leftovers_event_target_order=order)
    assert result["status"] == "resolved", result
    leftovers = [row for row in result["eot_consequence_trace"] if row["effect"] == "leftovers_recovery"]
    assert [row["owner"]["side"] for row in leftovers] == ["opponent", "self"]
    assert leftovers[1]["branch_fingerprint_consumed"] != leftovers[0]["branch_fingerprint_consumed"]
    assert _project_bounded_eot(pre_end_of_turn=pre, weather_event_target_order={"schema_version": "detached-weather-event-target-order-v1", "status": "known", "session_id": "leftovers-eot", "event_family": "Weather", "source_branch_fingerprint": fingerprint_transition_preview_state(pre["next_state"]), "ordered_active_owners": [_owner_id(pre["next_state"], side) for side in ("self", "opponent")], "provenance": "trusted_canonical_showdown_weather_event_target_order"}, leftovers_event_target_order=None) == {"status": "incomplete", "reason": "cross_owner_item_residual_order_unrepresented"}
    stale = deepcopy(order); stale["source_branch_fingerprint"] = "stale"
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order={"schema_version": "detached-weather-event-target-order-v1", "status": "known", "session_id": "leftovers-eot", "event_family": "Weather", "source_branch_fingerprint": fingerprint_transition_preview_state(pre["next_state"]), "ordered_active_owners": [_owner_id(pre["next_state"], side) for side in ("self", "opponent")], "provenance": "trusted_canonical_showdown_weather_event_target_order"}, leftovers_event_target_order=stale) == {"status": "rejected", "reason": "stale_or_foreign_item_residual_target_order"}
