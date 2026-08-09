import json
from collections import Counter

from llm.advisor_candidate_contract import build_provider_recommendation_payload
from scripts.run_sanitized_multi_move_mechanics_smoke import (
    FIXED_HIT_FIXTURES,
    FIXTURES,
    PSYCHIC_TERRAIN_PRIORITY_BLOCK_FIXTURES,
    _prepared,
)


def test_single_hit_formula_retains_the_canonical_ordered_sixteen_roll_multiset():
    candidate = _prepared(FIXTURES[0])["candidates"][0]
    mechanics = candidate["mechanics_result"]
    rolls = mechanics["exact_damage_rolls"]

    assert isinstance(rolls, tuple)
    assert len(rolls) == 16
    assert len(set(rolls)) < len(rolls)
    assert min(rolls) == mechanics["damage_range"]["minimum"]
    assert max(rolls) == mechanics["damage_range"]["maximum"]
    assert Counter(rolls).most_common(1)[0][1] > 1
    assert tuple(candidate["q12_damage"]["damage_rolls"]) == rolls


def test_fixed_hit_formula_remains_outside_the_single_hit_roll_authority_slice():
    candidate = _prepared(FIXED_HIT_FIXTURES[0])["candidates"][0]
    mechanics = candidate["mechanics_result"]
    assert mechanics["hit_count"] == 2
    assert "exact_damage_rolls" not in mechanics


def test_provider_and_presentation_views_exclude_raw_rolls_while_candidates_keep_them():
    prepared = _prepared(FIXTURES[0])
    comparisons = prepared["recommendation_request"]["candidate_comparisons"]
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)

    assert all("exact_damage_rolls" in candidate["mechanics_result"] for candidate in prepared["candidates"])
    assert all("exact_damage_rolls" not in row["mechanics_result"] for row in comparisons)
    assert isinstance(payload["candidate_comparisons"], list)
    assert "exact_damage_rolls" not in json.dumps(payload, sort_keys=True)


def test_insufficient_and_blocked_candidates_do_not_receive_synthetic_rolls():
    incomplete = _prepared(FIXED_HIT_FIXTURES[1])["candidates"][1]["mechanics_result"]
    blocked = _prepared(PSYCHIC_TERRAIN_PRIORITY_BLOCK_FIXTURES[0])["candidates"][0]["mechanics_result"]

    assert incomplete["status"] != "known" and "exact_damage_rolls" not in incomplete
    assert blocked["status"] == "unavailable" and "exact_damage_rolls" not in blocked
