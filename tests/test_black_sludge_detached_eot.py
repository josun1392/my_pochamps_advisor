"""Detached Black Sludge tier-five item residual coverage."""
from copy import deepcopy

from llm.advisor_black_sludge_end_of_turn import apply_owner_black_sludge_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_cross_owner_weather_end_of_turn, project_per_owner_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_leftovers_end_of_turn import _owner_id, _pre, _projection


def _types(state, self_types=("poison",), opponent_types=("normal",)):
    row = lambda side, values: {"side": side, "state": "known", "types": list(values), "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current"}
    state["current_state"]["current_type_context"] = {"current_types": [row("self", self_types), row("opponent", opponent_types)]}


def _weather_projection(pre):
    state = pre["next_state"]
    return {"schema_version": "detached-weather-event-target-order-v1", "status": "known", "session_id": "leftovers-eot", "event_family": "Weather", "source_branch_fingerprint": fingerprint_transition_preview_state(state), "ordered_active_owners": [_owner_id(state, side) for side in ("self", "opponent")], "provenance": "trusted_canonical_showdown_weather_event_target_order"}


def test_poison_type_recovers_and_current_type_not_species_selects_branch():
    pre = _pre(self_hp=95, self_item="black-sludge", self_condition="none")
    _types(pre["next_state"], self_types=("poison",))
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner=_owner_id(pre["next_state"], "self"))
    assert result["status"] == "resolved", result
    row = result["eot_consequence_trace"][0]
    assert (row["effect"], row["current_type"], row["recovery"], row["post_hp"]) == ("black_sludge_recovery", ["poison"], 6, 100)
    # The fixture identity supplies no type: changing only branch current type
    # must choose damage rather than any species-derived Poison assumption.
    non_poison = _pre(self_hp=50, self_item="black-sludge", self_condition="none")
    _types(non_poison["next_state"], self_types=("electric",))
    result = project_per_owner_end_of_turn(pre_end_of_turn=non_poison, owner=_owner_id(non_poison["next_state"], "self"))
    assert result["eot_consequence_trace"][0]["effect"] == "black_sludge_damage"
    assert result["next_state"]["active"]["self"]["current_hp"] == 38


def test_non_poison_lethal_and_unknown_or_foreign_authority_fail_closed():
    pre = _pre(self_hp=12, self_item="black-sludge", self_condition="none")
    _types(pre["next_state"], self_types=("normal",))
    state = deepcopy(pre["next_state"]); owner = _owner_id(state, "self")
    result = apply_owner_black_sludge_end_of_turn(state=state, side="self", owner=owner, source_branch_fingerprint=fingerprint_transition_preview_state(state))
    assert result["status"] == "resolved" and result["trace"]["damage"] == 12 and state["active"]["self"]["current_hp"] == 0 and state["active"]["self"]["fainted"] is True
    unknown = _pre(self_item="black-sludge", self_condition="none")
    assert apply_owner_black_sludge_end_of_turn(state=unknown["next_state"], side="self", owner=_owner_id(unknown["next_state"], "self"), source_branch_fingerprint=fingerprint_transition_preview_state(unknown["next_state"])) == {"status": "incomplete", "reason": "black_sludge_current_type_authority"}
    wrong = _pre(self_item="leftovers", self_condition="none"); _types(wrong["next_state"])
    assert apply_owner_black_sludge_end_of_turn(state=wrong["next_state"], side="self", owner=_owner_id(wrong["next_state"], "self"), source_branch_fingerprint=fingerprint_transition_preview_state(wrong["next_state"])) == {"status": "rejected", "reason": "black_sludge_item_required"}
    assert apply_owner_black_sludge_end_of_turn(state=pre["next_state"], side="self", owner={**_owner_id(pre["next_state"], "self"), "pokemon_id": "foreign"}, source_branch_fingerprint=fingerprint_transition_preview_state(pre["next_state"])) == {"status": "rejected", "reason": "stale_or_foreign_black_sludge_owner"}


def test_black_sludge_between_weather_and_poison_rebinds_hp_and_handoff():
    pre = _pre(self_hp=50, self_item="black-sludge", weather="snow", self_ability="ice-body", self_condition="poison")
    _types(pre["next_state"], self_types=("poison",))
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner=_owner_id(pre["next_state"], "self"))
    assert result["status"] == "resolved", result
    weather, sludge, poison = result["eot_consequence_trace"]
    assert [(row["tier"], row["effect"]) for row in result["eot_consequence_trace"]] == [(1, "ice_body_recovery"), (5, "black_sludge_recovery"), (9, "poison_residual")]
    assert (weather["post_hp"], sludge["pre_hp"], sludge["post_hp"], poison["pre_hp"], poison["post_hp"]) == (56, 56, 62, 62, 50)
    assert poison["branch_fingerprint_consumed"] != sludge["branch_fingerprint_consumed"]
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved" and handoff["next_state"]["active"]["self"]["current_hp"] == 50


def test_cross_owner_item_projection_orders_black_sludge_and_rejects_untrusted_plan():
    pre = _pre(self_item="black-sludge", opponent_item="black-sludge", self_condition="none", opponent_condition="none")
    _types(pre["next_state"], self_types=("poison",), opponent_types=("normal",))
    order = _projection(pre, ("opponent", "self"))
    result = project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=_weather_projection(pre), leftovers_event_target_order=order)
    assert result["status"] == "resolved", result
    rows = [row for row in result["eot_consequence_trace"] if row["item"] == "black-sludge"]
    assert [row["owner"]["side"] for row in rows] == ["opponent", "self"]
    assert rows[1]["branch_fingerprint_consumed"] != rows[0]["branch_fingerprint_consumed"]
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 68 and result["next_state"]["active"]["self"]["current_hp"] == 56
    untrusted = deepcopy(order); untrusted["provenance"] = "hand_authored"
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre, weather_event_target_order=_weather_projection(pre), leftovers_event_target_order=untrusted) == {"status": "incomplete", "reason": "cross_owner_item_residual_order_unrepresented"}
