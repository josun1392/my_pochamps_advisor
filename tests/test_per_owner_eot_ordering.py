"""Showdown-tiered, per-owner detached EOT composition coverage."""
from copy import deepcopy

from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn, reject_cross_owner_weather_order
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import _project_bounded_eot


def _owner(side, pokemon, hp=50):
    return {"session_id": "ordered-eot", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": hp, "max_hp": 100, "fainted": hp == 0}


def _pre(*, weather, ability, condition="poison", hp=50, predicted_toxic=False):
    state = {"schema_version": "deterministic-transition-preview-v1", "active": {"self": _owner("self", "owner", hp), "opponent": _owner("opponent", "other", 80)}, "current_state": {"current_state_session_id": "ordered-eot", "field_state_context": {"current_field": {"weather": "none", "side_effects": []}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": 80, "maximum_hp": 100}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": "pressure", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": "none" if predicted_toxic else condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "direct_mechanics_context": {"attacker": {"current_hp": hp, "max_hp": 100, "item": {"status": "known_absent"}}, "defender": {"current_hp": 80, "max_hp": 100, "item": {"status": "known_absent"}}}}}
    root = fingerprint_transition_preview_state(state)
    if predicted_toxic:
        owner = {key: state["active"]["self"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
        state["predicted_condition_context"] = {"schema_version": "hypothetical-move-poison-condition-v1", "source_snapshot_fingerprint": root, "branch_state_fingerprint": "application", "owner": owner, "condition_type": "toxic", "provenance": "turn_engine_predicted_move_poison"}
        state["predicted_toxic_lifecycle"] = {"schema_version": "hypothetical-predictive-toxic-lifecycle-v1", "source_snapshot_fingerprint": root, "branch_state_fingerprint": "application", "owner": owner, "current_stage": 1, "provenance": "turn_engine_predicted_toxic_application"}
    projected = project_field_weather(branch_state=state, source_fingerprint=fingerprint_transition_preview_state(state), frozen_field_state={"current_field": {"weather": "none", "side_effects": []}})
    field = apply_supported_switch_entry_weather(branch_state=projected["next_state"], source_fingerprint=projected["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "none", "weather_after": weather})
    return {"status": "resolved", "source_snapshot_fingerprint": root, "next_state": field["next_state"], "boundary": {"phase": "pre_end_of_turn"}}


def test_weather_tier_one_precedes_poison_and_rebinds_the_second_event():
    pre = _pre(weather="snow", ability="ice-body")
    before = deepcopy(pre)
    owner = pre["next_state"]["active"]["self"]
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner={key: owner[key] for key in ("session_id", "side", "slot_index", "pokemon_id")})
    assert result["status"] == "resolved", result
    assert [(row["tier"], row["effect"]) for row in result["eot_consequence_trace"]] == [(1, "ice_body_recovery"), (9, "poison_residual")]
    assert result["eot_consequence_trace"][0]["post_hp"] == 56
    assert result["eot_consequence_trace"][1]["pre_hp"] == 56
    assert result["next_state"]["active"]["self"]["current_hp"] == 44
    assert result["eot_consequence_trace"][1]["branch_fingerprint_consumed"] != result["source_pre_end_of_turn_fingerprint"]
    assert pre == before
    assert _project_bounded_eot(pre_end_of_turn=pre)["next_state"]["active"]["self"]["current_hp"] == 44


def test_toxic_and_poison_heal_remain_one_tier_nine_compound_after_weather():
    pre = _pre(weather="snow", ability="poison-heal", hp=50, predicted_toxic=True)
    # Snow has no tier-one effect for Poison Heal, while toxic remains exact.
    owner = {key: pre["next_state"]["active"]["self"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner=owner)
    assert result["status"] == "resolved", result
    assert len(result["eot_consequence_trace"]) == 1
    row = result["eot_consequence_trace"][0]
    assert (row["tier"], row["effect"], row["post_hp"], row["resulting_toxic_stage"]) == (9, "poison_heal_recovery", 62, 2)


def test_weather_recovery_then_toxic_consumes_recovered_hp_and_advances_lifecycle():
    pre = _pre(weather="snow", ability="ice-body", hp=50, predicted_toxic=True)
    owner = {key: pre["next_state"]["active"]["self"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner=owner)
    assert result["status"] == "resolved", result
    weather, toxic = result["eot_consequence_trace"]
    assert (weather["post_hp"], toxic["pre_hp"], toxic["post_hp"], toxic["resulting_toxic_stage"]) == (56, 56, 50, 2)


def test_terminal_weather_damage_skips_same_owner_condition_and_cross_owner_order_stays_explicitly_deferred():
    # Solar Power's canonical tier-one self damage is lethal before poison can run.
    pre = _pre(weather="sun", ability="solar-power", hp=12)
    owner = {key: pre["next_state"]["active"]["self"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
    result = project_per_owner_end_of_turn(pre_end_of_turn=pre, owner=owner)
    assert result["status"] == "resolved", result
    assert result["next_state"]["active"]["self"]["fainted"] is True
    assert result["eot_consequence_trace"][-1]["reason"] == "fainted_by_tier_one_weather"
    assert reject_cross_owner_weather_order(owners=[owner, {**owner, "side": "opponent"}]) == {"status": "incomplete", "reason": "cross_owner_weather_order_unrepresented"}


def test_foreign_owner_and_stale_weather_remain_rejected():
    pre = _pre(weather="rain", ability="rain-dish")
    owner = {key: pre["next_state"]["active"]["self"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
    assert project_per_owner_end_of_turn(pre_end_of_turn=pre, owner={**owner, "pokemon_id": "foreign"}) == {"status": "rejected", "reason": "stale_or_foreign_eot_owner"}
    stale = deepcopy(pre)
    stale["next_state"]["current_state"]["field_state_context"]["current_field"]["weather"] = "sun"
    assert project_per_owner_end_of_turn(pre_end_of_turn=stale, owner=owner) == {"status": "rejected", "reason": "stale_or_invalid_branch_sun_authority"}
