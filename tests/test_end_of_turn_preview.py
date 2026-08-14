from copy import deepcopy

from llm.advisor_end_of_turn_preview import project_poison_end_of_turn


def _branch(*, condition="poison", hp=80, maximum=160, ability="blaze", predicted=False):
    owner = lambda side, pokemon, slot: {"session_id": "eot-session", "side": side, "slot_index": slot, "pokemon_id": pokemon}
    active = {"self": {**owner("self", "pikachu", 0), "current_hp": hp, "max_hp": maximum, "fainted": False}, "opponent": {**owner("opponent", "arcanine", 1), "current_hp": 100, "max_hp": 100, "fainted": False}}
    current = {"current_hp_context": {"current_hp": [{"side": "self", "current_hp": hp, "maximum_hp": maximum}, {"side": "opponent", "current_hp": 100, "maximum_hp": 100}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": "blaze", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}}
    state = {"schema_version": "deterministic-transition-preview-v1", "active": active, "current_state": current}
    if predicted:
        state["predicted_condition_context"] = {"schema_version": "hypothetical-move-poison-condition-v1", "source_snapshot_fingerprint": "source", "branch_state_fingerprint": "prior", "owner": owner("self", "pikachu", 0), "condition_type": "poison", "provenance": "turn_engine_predicted_move_poison"}
    return {"source_snapshot_fingerprint": "source", "next_state": state, "boundary": {"phase": "pre_end_of_turn"}}


def test_ordinary_poison_projects_detached_end_of_turn_damage_and_faint():
    source = _branch(); before = deepcopy(source)
    result = project_poison_end_of_turn(pre_end_of_turn=source)
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["self"]["current_hp"] == 60
    assert result["eot_consequence_trace"][0]["effect"] == "poison_residual"
    assert source == before and result["boundary"] == {"phase": "end_of_turn"}
    lethal = project_poison_end_of_turn(pre_end_of_turn=_branch(hp=20))
    assert lethal["next_state"]["active"]["self"]["current_hp"] == 0 and lethal["next_state"]["active"]["self"]["fainted"] is True


def test_predicted_poison_is_branch_only_and_toxic_or_unknown_authority_fails_closed():
    predicted = _branch(condition="none", predicted=True); before = deepcopy(predicted)
    result = project_poison_end_of_turn(pre_end_of_turn=predicted)
    assert result["status"] == "resolved" and result["next_state"]["active"]["self"]["current_hp"] == 60
    assert predicted == before and predicted["next_state"]["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] == "none"
    assert project_poison_end_of_turn(pre_end_of_turn=_branch(condition="toxic")) == {"status": "incomplete", "reason": "self.toxic_progression"}
    unknown = _branch(); unknown["next_state"]["current_state"].pop("ability_context")
    assert project_poison_end_of_turn(pre_end_of_turn=unknown) == {"status": "incomplete", "reason": "self.ability"}


def test_stale_predicted_overlay_and_unsupported_poison_heal_do_not_project():
    stale = _branch(predicted=True); stale["source_snapshot_fingerprint"] = "other"
    assert project_poison_end_of_turn(pre_end_of_turn=stale) == {"status": "rejected", "reason": "stale_predicted_condition_overlay"}
    assert project_poison_end_of_turn(pre_end_of_turn=_branch(ability="poison-heal")) == {"status": "unsupported", "reason": "poison_heal_end_of_turn_not_in_slice"}
