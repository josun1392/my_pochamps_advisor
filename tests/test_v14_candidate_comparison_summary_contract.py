from llm.advisor_candidate_contract import build_recommendation_request


def _candidate(slot, move, status="resolved", availability="usable"):
    return {"slot_index": slot, "move": move, "status": status, "availability": availability,
            "damage": {"status": "resolved", "minimum": 21, "maximum": 25, "ko": {"status": "possible"}},
            "hit_chance": {"status": "resolved", "hit_chance_percent": 100}, "move_order": {"status": "resolved", "result": "self_first"},
            "dynamic_move": {"family": "environment_based_move", "status": "resolved", "effective_power": 100, "effective_type": "water"},
            "self_effects": [{"kind": "direct_healing", "status": "resolved", "effect": {"amount": 1}}],
            "warnings": ["warning"], "unavailable_reasons": ["reason"]}


def test_comparison_rows_preserve_order_duplicates_and_actual_deterministic_summaries():
    first, second = _candidate(0, "weather-ball"), _candidate(2, "weather-ball")
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [first, second], "known_limitations": ["limited"]})
    assert [row["slot_index"] for row in request["candidate_comparisons"]] == [0, 2]
    assert [row["move"] for row in request["candidate_comparisons"]] == ["weather-ball", "weather-ball"]
    row = request["candidate_comparisons"][0]
    for field in ("damage", "hit_chance", "move_order", "dynamic_move", "self_effects", "warnings", "unavailable_reasons"):
        assert row[field] == first[field]
    assert request["known_limitations"] == ["limited"]
    assert "fabricated" not in row


def test_no_missing_deterministic_field_is_fabricated():
    candidate = _candidate(0, "tackle")
    del candidate["hit_chance"]; del candidate["move_order"]
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})
    row = request["candidate_comparisons"][0]
    assert "hit_chance" not in row and "move_order" not in row
