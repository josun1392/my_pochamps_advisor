"""Detached Rain-side Dry Skin EOT authority and lifecycle coverage."""
from copy import deepcopy

from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_dry_skin_end_of_turn import project_dry_skin_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import _project_bounded_eot


def _owner(side, pokemon, hp=50):
    return {"session_id": "dry-eot", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": hp, "max_hp": 100, "fainted": hp == 0}


def _branch(*, self_hp=50, self_ability="dry-skin", opponent_ability="pressure", condition="none"):
    return {"schema_version": "deterministic-transition-preview-v1", "active": {"self": _owner("self", "dry-user", self_hp), "opponent": _owner("opponent", "target", 80)}, "current_state": {"current_state_session_id": "dry-eot", "field_state_context": {"current_field": {"weather": "none", "side_effects": []}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": 80, "maximum_hp": 100}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": self_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": opponent_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "direct_mechanics_context": {"attacker": {"current_hp": self_hp, "max_hp": 100}, "defender": {"current_hp": 80, "max_hp": 100}}}}


def _pre_rain(**kwargs):
    branch = _branch(**kwargs)
    source = fingerprint_transition_preview_state(branch)
    projected = project_field_weather(branch_state=branch, source_fingerprint=source, frozen_field_state={"current_field": {"weather": "sun", "side_effects": []}})
    # Existing Drizzle field mutation is consumed later by this distinct Dry Skin owner.
    rain = apply_supported_switch_entry_weather(branch_state=projected["next_state"], source_fingerprint=projected["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "sun", "weather_after": "rain"})
    return branch, {"status": "resolved", "source_snapshot_fingerprint": source, "next_state": rain["next_state"], "boundary": {"phase": "pre_end_of_turn"}}


def _self_trace(result):
    return next(row for row in result["eot_consequence_trace"] if row["owner"]["side"] == "self")


def test_detached_dry_skin_consumes_exact_rain_uses_canonical_eighth_and_handoff_preserves_state():
    branch, pre = _pre_rain()
    frozen = deepcopy(pre["next_state"])
    result = project_dry_skin_end_of_turn(pre_end_of_turn=pre)
    assert result["status"] == "resolved", result
    assert pre["next_state"] == frozen and branch["active"]["self"]["current_hp"] == 50
    row = _self_trace(result)
    assert row["recovery"] == 12 and row["post_hp"] == 62 and row["weather"] == "rain"
    assert result["resulting_branch_fingerprint"] != fingerprint_transition_preview_state(pre["next_state"])
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved"
    assert handoff["next_state"]["active"]["self"]["current_hp"] == 62
    assert handoff["next_state"]["branch_field_weather_context"]["weather"] == "rain"

    _, cap_pre = _pre_rain(self_hp=95)
    assert _self_trace(project_dry_skin_end_of_turn(pre_end_of_turn=cap_pre))["post_hp"] == 100
    _, full_pre = _pre_rain(self_hp=100)
    full = _self_trace(project_dry_skin_end_of_turn(pre_end_of_turn=full_pre))
    assert full["outcome"] == "already_full_hp" and full["recovery"] == 0


def test_dry_skin_rejects_wrong_or_foreign_rain_and_preserves_ordering_fail_closed():
    _, pre = _pre_rain()
    foreign_weather = deepcopy(pre)
    foreign_weather["next_state"]["branch_field_weather_context"]["session_id"] = "foreign"
    assert project_dry_skin_end_of_turn(pre_end_of_turn=foreign_weather) == {"status": "rejected", "reason": "stale_or_invalid_branch_rain_authority"}
    wrong_weather = deepcopy(pre)
    wrong_weather["next_state"]["current_state"]["field_state_context"]["current_field"]["weather"] = "sun"
    assert project_dry_skin_end_of_turn(pre_end_of_turn=wrong_weather) == {"status": "rejected", "reason": "stale_or_invalid_branch_rain_authority"}
    unknown = deepcopy(pre)
    unknown["next_state"]["current_state"]["ability_context"]["current_abilities"] = unknown["next_state"]["current_state"]["ability_context"]["current_abilities"][:1]
    assert project_dry_skin_end_of_turn(pre_end_of_turn=unknown) == {"status": "incomplete", "reason": "dry_skin_current_ability_authority"}
    _, poison_pre = _pre_rain(condition="poison")
    assert project_dry_skin_end_of_turn(pre_end_of_turn=poison_pre) == {"status": "incomplete", "reason": "dry_skin_residual_ordering_unresolved"}
    _, toxic_pre = _pre_rain(condition="toxic")
    assert project_dry_skin_end_of_turn(pre_end_of_turn=toxic_pre) == {"status": "incomplete", "reason": "dry_skin_residual_ordering_unresolved"}
    _, mixed_pre = _pre_rain(opponent_ability="rain-dish")
    assert project_dry_skin_end_of_turn(pre_end_of_turn=mixed_pre) == {"status": "incomplete", "reason": "dry_skin_residual_ordering_unresolved"}
    assert _project_bounded_eot(pre_end_of_turn=mixed_pre) == {"status": "incomplete", "reason": "rain_dish_residual_ordering_unresolved"}


def test_dry_skin_uses_post_direct_hp_never_revives_and_dispatches_only_for_exact_rain_authority():
    _, post_direct = _pre_rain(self_hp=20)
    result = project_dry_skin_end_of_turn(pre_end_of_turn=post_direct)
    assert _self_trace(result)["pre_hp"] == 20 and _self_trace(result)["post_hp"] == 32
    _, knocked_out = _pre_rain(self_hp=0)
    result = project_dry_skin_end_of_turn(pre_end_of_turn=knocked_out)
    assert _self_trace(result)["outcome"] == "fainted_before_eot" and result["next_state"]["active"]["self"]["current_hp"] == 0
    _, dispatch_pre = _pre_rain()
    assert _self_trace(_project_bounded_eot(pre_end_of_turn=dispatch_pre))["effect"] == "dry_skin_recovery"
    _, no_dry_skin = _pre_rain(self_ability="pressure")
    assert _project_bounded_eot(pre_end_of_turn=no_dry_skin)["eot_consequence_trace"] == []
