from llm.advisor_detached_next_turn_ordinary_attack_execution import _move, _secondary, execute_detached_next_turn_ordinary_attack


def _metadata(**changes):
    value = {"status": "resolved", "move_id": "tackle", "category": "physical", "power": 40, "accuracy": 100, "priority": 0, "type": "normal"}
    value.update(changes)
    return value


def test_tackle_is_a_supported_single_hit_normal_formula_descriptor():
    move = _move(_metadata(), "tackle")
    assert {key: move[key] for key in ("move_id", "power", "accuracy", "category", "type", "priority")} == {"move_id": "tackle", "power": 40, "accuracy": 100, "category": "physical", "type": "normal", "priority": 0}


def test_special_families_and_unknown_secondaries_fail_closed():
    assert _move(_metadata(min_hits=2, max_hits=2), "tackle") == "ordinary_attack_special_family_unsupported"
    assert _secondary(_move(_metadata(ailment="poison", effect_chance=30), "tackle")) == "ordinary_attack_secondary_unowned"
    assert _secondary(_move(_metadata(ailment="flinch", effect_chance=30), "tackle")) == {"kind": "flinch", "chance": 30}
    assert execute_detached_next_turn_ordinary_attack(execution_authority={"status": "resolved"})["status"] == "rejected"
