"""Compact end-to-end closure for trusted known opponents through self ranking."""
from __future__ import annotations

import json

import pytest

from llm.advisor_candidate_contract import build_provider_recommendation_payload, rank_direct_mechanics_candidates
from llm.advisor_threat_ranking import project_threat_ranking_tier
from scripts.run_sanitized_threat_ranking_smoke import FIXTURES, _prepared


def _summary(**overrides):
    return {
        "known_guaranteed_ohko_capability_exists": False,
        "known_executed_guaranteed_ohko_threat_exists": False,
        "known_executed_possible_ohko_threat_exists": False,
        "candidate_set_complete": False,
        "known_candidate_count": 0,
        "unknown_slots_remaining": 4,
        "known_threat_evaluation_complete": False,
        "global_threat_complete": False,
        "all_known_actions_preempted": "unresolved",
        "no_known_guaranteed_ohko": "unresolved",
        **overrides,
    }


def test_confirmed_partial_threat_flows_from_frozen_known_move_to_provider_redacted_rank():
    prepared = _prepared(FIXTURES[0])
    bundle = prepared["evidence_bundle"]
    opponent = bundle["opponent_action_candidates"]
    pairs = bundle["self_opponent_pairs"]
    summaries = {row["self_candidate_id"]: row for row in bundle["known_opponent_threat_summaries"]["threat_summaries"]}
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)

    assert prepared["status"] == "ready"
    assert opponent["known_move_state"] == "partially_known" and opponent["known_candidate_count"] == 1
    assert opponent["candidate_set_complete"] is False and opponent["unknown_slots_remaining"] == 3
    assert opponent["opponent_action_evaluations"][0]["candidate_id"].startswith("opponent-action:")
    assert pairs["pair_count"] == 2 and len({pair["pair_id"] for pair in pairs["pairs"]}) == 2
    assert summaries["self:0:slam"]["known_executed_guaranteed_ohko_threat_exists"] is True
    assert project_threat_ranking_tier(summaries["self:0:slam"])[0] == "executed_guaranteed_ohko"
    assert project_threat_ranking_tier(summaries["self:1:quick"])[0] == "neutral_no_positive_threat_evidence"
    assert [(row["move"], row["mechanics_comparison"]["rank"]) for row in rows] == [("slam", 2), ("quick", 1)]
    assert all(row["eligibility"] != "not_selectable" for row in rows)
    rendered = json.dumps(payload, sort_keys=True)
    assert not any(key in rendered for key in ("known_move_context", "opponent_action_candidates", "self_opponent_pairs", "known_opponent_threat_summaries", "internal_threat_summaries", "threat_ranking_tier", "exact_damage_rolls", "ko_probability"))


def test_partial_neutral_preserves_base_order_without_a_safety_tier():
    prepared = _prepared(FIXTURES[1])
    candidates = prepared["candidates"]
    base = rank_direct_mechanics_candidates(candidates=candidates)
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    summaries = prepared["evidence_bundle"]["known_opponent_threat_summaries"]["threat_summaries"]

    assert {candidate["move"]: base[(candidate["slot_index"], candidate["move"])]["rank"] for candidate in candidates} == {"slam": 1, "quick": 2}
    assert [(row["move"], row["mechanics_comparison"]["rank"]) for row in rows] == [("slam", 1), ("quick", 2)]
    assert all(project_threat_ranking_tier(summary)[0] == "neutral_no_positive_threat_evidence" for summary in summaries)
    assert all(summary["candidate_set_complete"] is False and summary["global_threat_complete"] is False for summary in summaries)


@pytest.mark.parametrize(
    ("summary", "tier"),
    [
        (_summary(known_executed_guaranteed_ohko_threat_exists=True), "executed_guaranteed_ohko"),
        (_summary(known_guaranteed_ohko_capability_exists=True), "unresolved_guaranteed_ohko_exposure"),
        (_summary(known_executed_possible_ohko_threat_exists=True), "executed_possible_ohko"),
        (_summary(), "neutral_no_positive_threat_evidence"),
        (_summary(candidate_set_complete=True, known_candidate_count=4, unknown_slots_remaining=0, known_threat_evaluation_complete=True, global_threat_complete=True, no_known_guaranteed_ohko="true"), "complete_set_no_guaranteed_ohko"),
        (_summary(candidate_set_complete=True, known_candidate_count=4, unknown_slots_remaining=0, known_threat_evaluation_complete=True, global_threat_complete=True, no_known_guaranteed_ohko="true", all_known_actions_preempted="true"), "complete_set_all_actions_preempted"),
    ],
)
def test_tier_matrix_keeps_raw_preemption_and_complete_safety_boundaries(summary, tier):
    assert project_threat_ranking_tier(summary)[0] == tier


def test_preempted_raw_ohko_is_not_penalized_but_malformed_present_evidence_fails_closed():
    assert project_threat_ranking_tier(_summary(known_guaranteed_ohko_capability_exists=True, all_known_actions_preempted="true"))[0] == "neutral_no_positive_threat_evidence"
    with pytest.raises(ValueError, match="malformed_threat_summary"):
        project_threat_ranking_tier({"candidate_set_complete": False})
