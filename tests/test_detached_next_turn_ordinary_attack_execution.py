from llm.advisor_detached_next_turn_ordinary_attack_execution import _move, execute_detached_next_turn_ordinary_attack


def _metadata(**changes):
    value = {"status": "resolved", "move_id": "tackle", "category": "physical", "power": 40, "accuracy": 100, "priority": 0, "type": "normal"}
    value.update(changes)
    return value


def test_tackle_is_a_supported_single_hit_normal_formula_descriptor():
    assert _move(_metadata(), "tackle") == {"move_id": "tackle", "power": 40, "accuracy": 100, "category": "physical", "type": "normal", "priority": 0}


def test_special_families_and_unknown_secondaries_fail_closed():
    assert _move(_metadata(min_hits=2, max_hits=2), "tackle") == "ordinary_attack_special_family_unsupported"
    assert _move(_metadata(secondary="unknown"), "tackle") == "ordinary_attack_secondary_unowned"
    assert execute_detached_next_turn_ordinary_attack(execution_authority={"status": "resolved"})["status"] == "rejected"
