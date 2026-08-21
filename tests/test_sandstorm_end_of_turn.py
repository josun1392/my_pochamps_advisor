from copy import deepcopy

from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_sandstorm_end_of_turn import project_sandstorm_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _owner(side, pokemon, hp=80):
    return {"session_id": "sand-eot", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": hp, "max_hp": 100, "fainted": hp == 0}


def _type(side, types):
    return {"side": side, "state": "known", "types": list(types), "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current", "confidence": "known"}


def _branch(*, self_hp=80, self_type=("normal",), self_ability="pressure", self_item=None, condition="none"):
    item = lambda value: {"status": "known_absent"} if value is None else {"status": "known", "value": value}
    return {"schema_version": "deterministic-transition-preview-v1", "active": {"self": _owner("self", "setter", self_hp), "opponent": _owner("opponent", "target")}, "current_state": {"current_state_session_id": "sand-eot", "field_state_context": {"current_field": {"weather": "none", "side_effects": []}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": 80, "maximum_hp": 100}]}, "current_type_context": {"current_types": [_type("self", self_type), _type("opponent", ("normal",))]}, "ability_context": {"current_abilities": [{"side": "self", "ability": self_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": "pressure", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "direct_mechanics_context": {"attacker": {"current_hp": self_hp, "max_hp": 100, "item": item(self_item)}, "defender": {"current_hp": 80, "max_hp": 100, "item": item(None)}}}}


def _pre_sandstorm(**kwargs):
    branch = _branch(**kwargs); source = fingerprint_transition_preview_state(branch)
    projected = project_field_weather(branch_state=branch, source_fingerprint=source, frozen_field_state={"current_field": {"weather": "sun", "side_effects": []}})
    sand = apply_supported_switch_entry_weather(branch_state=projected["next_state"], source_fingerprint=projected["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "sun", "weather_after": "sandstorm"})
    return branch, {"status": "resolved", "source_snapshot_fingerprint": source, "next_state": sand["next_state"], "boundary": {"phase": "pre_end_of_turn"}}


def test_detached_sandstorm_eot_damages_exact_actives_and_handoff_preserves_field_and_hp():
    branch, pre = _pre_sandstorm(); before = deepcopy(pre["next_state"])
    result = project_sandstorm_end_of_turn(pre_end_of_turn=pre)
    assert result["status"] == "resolved", result
    assert pre["next_state"] == before and branch["active"]["self"]["current_hp"] == 80
    self_row = next(row for row in result["eot_consequence_trace"] if row["owner"]["side"] == "self")
    assert self_row["residual_damage"] == 6 and self_row["post_hp"] == 74
    assert result["resulting_branch_fingerprint"] != fingerprint_transition_preview_state(pre["next_state"])
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved"
    assert handoff["next_state"]["active"]["self"]["current_hp"] == 74
    assert handoff["next_state"]["branch_field_weather_context"]["weather"] == "sandstorm"


def test_sandstorm_canonical_immunity_lethal_and_ordering_fail_closed():
    _, immune_pre = _pre_sandstorm(self_type=("rock",))
    immune = project_sandstorm_end_of_turn(pre_end_of_turn=immune_pre)
    self_row = next(row for row in immune["eot_consequence_trace"] if row["owner"]["side"] == "self")
    assert self_row["outcome"] == "immune_by_type" and self_row["residual_damage"] == 0
    _, lethal_pre = _pre_sandstorm(self_hp=6)
    lethal = project_sandstorm_end_of_turn(pre_end_of_turn=lethal_pre)
    assert lethal["next_state"]["active"]["self"]["current_hp"] == 0
    assert lethal["next_state"]["active"]["self"]["fainted"] is True
    _, poison_pre = _pre_sandstorm(condition="poison")
    assert project_sandstorm_end_of_turn(pre_end_of_turn=poison_pre) == {"status": "incomplete", "reason": "sandstorm_residual_ordering_unresolved"}
    _, toxic_pre = _pre_sandstorm(condition="toxic")
    assert project_sandstorm_end_of_turn(pre_end_of_turn=toxic_pre) == {"status": "incomplete", "reason": "sandstorm_residual_ordering_unresolved"}


def test_sandstorm_rejects_foreign_weather_or_active_authority():
    _, pre = _pre_sandstorm()
    foreign_weather = deepcopy(pre); foreign_weather["next_state"]["branch_field_weather_context"]["session_id"] = "foreign"
    assert project_sandstorm_end_of_turn(pre_end_of_turn=foreign_weather) == {"status": "rejected", "reason": "stale_or_invalid_branch_sandstorm_authority"}
    foreign_active = deepcopy(pre); foreign_active["next_state"]["active"]["opponent"]["session_id"] = "foreign"
    assert project_sandstorm_end_of_turn(pre_end_of_turn=foreign_active) == {"status": "rejected", "reason": "invalid_active_owner"}
    unknown_type = deepcopy(pre); unknown_type["next_state"]["current_state"].pop("current_type_context")
    assert project_sandstorm_end_of_turn(pre_end_of_turn=unknown_type) == {"status": "incomplete", "reason": "sandstorm_current_type_authority"}
    unknown_item = deepcopy(pre); unknown_item["next_state"]["current_state"]["direct_mechanics_context"]["attacker"]["item"] = {"status": "unknown"}
    assert project_sandstorm_end_of_turn(pre_end_of_turn=unknown_item) == {"status": "incomplete", "reason": "sandstorm_current_item_authority"}
