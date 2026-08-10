"""End-to-end closure matrix for application-owned threat presentation."""
from __future__ import annotations

import json
from copy import deepcopy

from llm.advisor_candidate_contract import build_provider_recommendation_payload
from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_threat_presentation import project_selected_threat_presentation
from scripts.run_sanitized_threat_ranking_smoke import FIXTURES, _prepared
from tests.test_threat_aware_ranking_presentation import _bundle, _pair, _summary


def test_dto_is_bounded_and_first_matching_frozen_witness_wins_without_probability():
    candidate = "self:0:slam"
    bundle = _bundle(
        _summary(candidate, known_executed_guaranteed_ohko_threat_exists=True),
        [
            _pair(candidate, "first-move", "guaranteed", order="acts_second"),
            _pair(candidate, "later-move", "guaranteed", order="acts_second"),
        ],
    )
    dto = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=bundle)
    assert dto["witness_move_id"] == "first-move"
    assert dto["reason_code"] == "opponent_executed_guaranteed_ohko"
    assert set(dto) == {
        "presentation_status", "selected_candidate_id", "threat_tier", "adjustment_kind",
        "reason_code", "witness_move_id", "text", "scope_note",
    }
    assert not ({"pair_id", "session_id", "exact_damage_rolls", "ko_by_1", "provenance"} & set(dto))


def test_selected_candidate_isolation_and_output_bound_hold_in_actual_frozen_fixture():
    bundle = _prepared(FIXTURES[0])["evidence_bundle"]
    danger = project_selected_threat_presentation(selected_candidate_id="self:0:slam", evidence_bundle=bundle)
    neutral = project_selected_threat_presentation(selected_candidate_id="self:1:quick", evidence_bundle=bundle)
    assert danger["presentation_status"] == "available"
    assert neutral["presentation_status"] == "unavailable"
    selected = {
        "selected_action": {"slot_index": 0, "move": "slam"},
        "explanation_code": "clear_ranked_winner",
        "evidence": {},
        "threat_ranking": danger,
    }
    lines = format_recommendation_presentation_text(
        presentation_model={"status": "resolved", "recommended_move": "slam", "recommended_slot_index": 0, "selected_candidate": selected}
    ).splitlines()
    assert sum("earthquake" in line for line in lines) == 1
    assert sum("아직 확인되지 않은 상대 기술" in line for line in lines) == 1


def test_partial_unknown_and_incomplete_scope_never_emit_safety_copy():
    candidate = "self:0:slam"
    partial_preempted = project_selected_threat_presentation(
        selected_candidate_id=candidate,
        evidence_bundle=_bundle(_summary(candidate, all_known_actions_preempted="true")),
    )
    unknown = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate, opponent_known_move_state="unknown", known_candidate_count=0, unknown_slots_remaining=4, known_threat_evaluation_complete=False, all_known_actions_preempted="unresolved")))
    incomplete_complete = project_selected_threat_presentation(
        selected_candidate_id=candidate,
        evidence_bundle=_bundle(_summary(candidate, opponent_known_move_state="complete", known_candidate_count=4, unknown_slots_remaining=0, candidate_set_complete=True, known_threat_evaluation_complete=False, global_threat_complete=False)),
    )
    assert all(row["presentation_status"] == "unavailable" for row in (partial_preempted, unknown, incomplete_complete))


def test_unresolved_and_possible_copy_preserve_order_and_ko_uncertainty():
    candidate = "self:0:slam"
    unresolved = project_selected_threat_presentation(
        selected_candidate_id=candidate,
        evidence_bundle=_bundle(_summary(candidate, known_guaranteed_ohko_capability_exists=True), [_pair(candidate, "earthquake", "guaranteed", order="speed_tie")]),
    )
    possible = project_selected_threat_presentation(
        selected_candidate_id=candidate,
        evidence_bundle=_bundle(_summary(candidate, known_executed_possible_ohko_threat_exists=True), [_pair(candidate, "ice-beam", "possible", order="acts_second")]),
    )
    assert "행동 순서가 확정되지 않아" in unresolved["text"]
    assert "상대가 먼저" not in unresolved["text"] and "50/50" not in unresolved["text"]
    assert "1타 가능성" in possible["text"] and "확정 1타" not in possible["text"]


def test_raw_preempted_and_missing_or_malformed_evidence_leave_presentation_silent():
    candidate = "self:0:slam"
    preempted = project_selected_threat_presentation(
        selected_candidate_id=candidate,
        evidence_bundle=_bundle(_summary(candidate, known_guaranteed_ohko_capability_exists=True, all_known_actions_preempted="true"), [_pair(candidate, "earthquake", "guaranteed", preemption="preempted")]),
    )
    malformed = _summary(candidate)
    malformed.pop("known_threat_evaluation_complete")
    assert preempted["presentation_status"] == "unavailable"
    assert project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=None)["presentation_status"] == "unavailable"
    assert project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(malformed))["presentation_status"] == "unavailable"


def test_projection_is_detached_and_provider_payload_excludes_all_presentation_authority():
    prepared = _prepared(FIXTURES[0])
    bundle = prepared["evidence_bundle"]
    dto = project_selected_threat_presentation(selected_candidate_id="self:0:slam", evidence_bundle=bundle)
    frozen = deepcopy(dto)
    bundle["self_opponent_pairs"]["pairs"][0]["opponent_candidate_id"] = "opponent-action:changed:changed:changed:0"
    assert dto == frozen
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    serialized = json.dumps(payload, sort_keys=True)
    assert not any(key in serialized for key in (
        "threat_ranking", "threat_tier", "threat_summaries", "witness_move_id",
        "scope_note", "opponent_action_candidates", "self_opponent_pairs",
    ))


def test_formatter_suppresses_malformed_dto_without_changing_rank_or_selectability():
    prepared = _prepared(FIXTURES[0])
    before = deepcopy(prepared["recommendation_request"]["candidate_comparisons"])
    malformed = {
        "presentation_status": "available",
        "selected_candidate_id": "self:0:slam",
        "threat_tier": "executed_guaranteed_ohko",
        "adjustment_kind": "bounded_reward",
        "reason_code": "complete_set_no_guaranteed_ohko",
        "witness_move_id": "earthquake",
        "text": "forged safety text",
        "scope_note": None,
    }
    text = format_recommendation_presentation_text(
        presentation_model={
            "status": "resolved", "recommended_move": "slam", "recommended_slot_index": 0,
            "selected_candidate": {
                "selected_action": {"slot_index": 0, "move": "slam"},
                "explanation_code": "clear_ranked_winner", "evidence": {}, "threat_ranking": malformed,
            },
        }
    )
    assert "forged safety text" not in text
    assert prepared["recommendation_request"]["candidate_comparisons"] == before
