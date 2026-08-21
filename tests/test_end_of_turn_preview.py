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


def test_stale_predicted_overlay_rejects_and_poison_heal_replaces_poison_damage():
    stale = _branch(predicted=True); stale["source_snapshot_fingerprint"] = "other"
    assert project_poison_end_of_turn(pre_end_of_turn=stale) == {"status": "rejected", "reason": "stale_predicted_condition_overlay"}
    result = project_poison_end_of_turn(pre_end_of_turn=_branch(ability="poison-heal"))
    row = result["eot_consequence_trace"][0]
    assert (row["effect"], row["recovery"], row["post_hp"]) == ("poison_heal_recovery", 20, 100)


def test_predicted_toxic_uses_stage_one_then_advances_branch_only_even_when_lethal():
    source = _branch(condition="none", hp=100, maximum=160, predicted=True)
    owner = source["next_state"]["active"]["self"]
    source["next_state"]["predicted_condition_context"]["condition_type"] = "toxic"
    source["next_state"]["predicted_toxic_lifecycle"] = {"schema_version": "hypothetical-predictive-toxic-lifecycle-v1", "source_snapshot_fingerprint": "source", "branch_state_fingerprint": "prior", "owner": {key: owner[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, "current_stage": 1, "provenance": "turn_engine_predicted_toxic_application"}
    before = deepcopy(source); result = project_poison_end_of_turn(pre_end_of_turn=source)
    assert result["status"] == "resolved"
    row = result["eot_consequence_trace"][0]
    assert (row["toxic_stage"], row["damage"], row["post_hp"], row["resulting_toxic_stage"]) == (1, 10, 90, 2)
    assert source == before and "toxic_progression" not in source["next_state"]["current_state"]
    lethal = deepcopy(source); lethal["next_state"]["active"]["self"]["current_hp"] = 5; lethal["next_state"]["current_state"]["current_hp_context"]["current_hp"][0]["current_hp"] = 5
    outcome = project_poison_end_of_turn(pre_end_of_turn=lethal)
    assert outcome["next_state"]["active"]["self"]["fainted"] is True and outcome["next_state"]["predicted_toxic_lifecycle"]["current_stage"] == 2


def test_toxic_lifecycle_mismatch_and_plain_toxic_remain_fail_closed():
    source = _branch(condition="none", predicted=True); source["next_state"]["predicted_condition_context"]["condition_type"] = "toxic"
    assert project_poison_end_of_turn(pre_end_of_turn=source) == {"status": "incomplete", "reason": "self.toxic_progression"}
    source["next_state"]["predicted_toxic_lifecycle"] = {"schema_version": "hypothetical-predictive-toxic-lifecycle-v1", "source_snapshot_fingerprint": "source", "branch_state_fingerprint": "prior", "owner": {"session_id": "bad", "side": "self", "slot_index": 0, "pokemon_id": "pikachu"}, "current_stage": 1, "provenance": "turn_engine_predicted_toxic_application"}
    assert project_poison_end_of_turn(pre_end_of_turn=source)["status"] == "rejected"


def test_poison_heal_toxic_advances_stage_without_toxic_damage_even_at_full_hp():
    source = _branch(condition="none", hp=100, maximum=160, predicted=True, ability="poison-heal")
    owner = source["next_state"]["active"]["self"]
    source["next_state"]["predicted_condition_context"]["condition_type"] = "toxic"
    source["next_state"]["predicted_toxic_lifecycle"] = {"schema_version": "hypothetical-predictive-toxic-lifecycle-v1", "source_snapshot_fingerprint": "source", "branch_state_fingerprint": "prior", "owner": {key: owner[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, "current_stage": 1, "provenance": "turn_engine_predicted_toxic_application"}
    result = project_poison_end_of_turn(pre_end_of_turn=source)
    row = result["eot_consequence_trace"][0]
    assert (row["recovery"], row["post_hp"], row["toxic_stage"], row["resulting_toxic_stage"]) == (20, 120, 1, 2)
    full = deepcopy(source); full["next_state"]["active"]["self"]["current_hp"] = 160; full["next_state"]["current_state"]["current_hp_context"]["current_hp"][0]["current_hp"] = 160
    result = project_poison_end_of_turn(pre_end_of_turn=full)
    assert result["eot_consequence_trace"][0]["recovery"] == 0 and result["next_state"]["predicted_toxic_lifecycle"]["current_stage"] == 2
