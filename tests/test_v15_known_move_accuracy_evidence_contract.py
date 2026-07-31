from llm.advisor_candidate_contract import _comparison_facts, evaluate_move_candidate


def _candidate(slot, move, metadata):
    return evaluate_move_candidate(slot_index=slot, move=move, battle_snapshot={}, repositories={move: metadata})


def test_canonical_accuracy_distinguishes_100_from_always_hits_and_preserves_unknowns():
    hundred = _candidate(0, "thunderbolt", {"category": "special", "power": 90, "type": "electric", "accuracy": 100})
    always = _candidate(1, "swift", {"category": "special", "power": 60, "type": "normal", "always_hit": True})
    missing = _candidate(2, "unknown", {"category": "physical", "power": 40, "type": "normal"})
    dynamic = _candidate(3, "dynamic", {"category": "special", "power": 1, "type": "normal", "dynamic_accuracy": True})
    assert hundred["accuracy_evidence"] == {"status": "known_accuracy", "canonical_accuracy": 100, "outcome": "canonical_accuracy_only", "uncertainty": []}
    assert always["accuracy_evidence"]["status"] == "always_hits"
    assert missing["accuracy_evidence"]["status"] == "insufficient_context"
    assert dynamic["accuracy_evidence"]["status"] == "unsupported_mechanic"


def test_accuracy_facts_are_candidate_local_and_do_not_change_damage_ranks():
    candidates = [
        _candidate(0, "low", {"category": "physical", "power": 40, "type": "normal", "accuracy": 70}),
        _candidate(1, "high", {"category": "physical", "power": 40, "type": "normal", "accuracy": 100}),
    ]
    low = _comparison_facts(candidate=candidates[0], comparison={"comparison_status": "rankable"}, candidates=candidates)
    high = _comparison_facts(candidate=candidates[1], comparison={"comparison_status": "rankable"}, candidates=candidates)
    assert low["candidate_id"] == {"slot_index": 0, "move": "low"}
    assert "known_lower_canonical_accuracy" in low["comparison_tags"]
    assert "known_higher_canonical_accuracy" in high["comparison_tags"]
