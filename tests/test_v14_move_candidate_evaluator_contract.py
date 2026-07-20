from llm.advisor_candidate_contract import evaluate_move_candidate


def _stat(side, stat, value):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _snapshot(**extra):
    snapshot = {"final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}
    snapshot.update(extra)
    return snapshot


def test_ordinary_damaging_move_uses_actual_deterministic_damage():
    candidate = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=_snapshot(), repositories={"tackle": {"category": "physical", "power": 40, "type": "normal"}})
    assert candidate["status"] == "resolved"
    assert candidate["damage"] == {"status": "resolved", "minimum": 21, "maximum": 25}


def test_missing_damage_never_becomes_resolved_zero_damage():
    candidate = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot={}, repositories={"tackle": {"category": "physical", "power": 40, "type": "normal"}})
    assert candidate["status"] == "partial"
    assert candidate["damage"]["status"] == "unavailable"
    assert "minimum" not in candidate["damage"] and "maximum" not in candidate["damage"]


def test_non_damaging_move_remains_partial_and_not_applicable():
    candidate = evaluate_move_candidate(slot_index=0, move="protect", battle_snapshot=_snapshot(), repositories={"protect": {"category": "status"}})
    assert candidate["status"] == "partial"
    assert candidate["damage"] == {"status": "not_applicable"}
    assert candidate["warnings"] == ["unsupported_non_damage_utility_ranking"]
