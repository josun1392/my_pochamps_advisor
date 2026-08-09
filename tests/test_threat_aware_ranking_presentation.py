from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_presentation_model, complete_recommendation_cycle
from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_threat_presentation import project_selected_threat_presentation
from scripts.run_sanitized_threat_ranking_smoke import FIXTURES, _prepared


def _summary(candidate_id="self:0:slam", **changes):
    row = {
        "self_candidate_id": candidate_id,
        "opponent_known_move_state": "partially_known",
        "known_candidate_count": 1,
        "unknown_slots_remaining": 3,
        "candidate_set_complete": False,
        "known_guaranteed_ohko_capability_exists": False,
        "known_executed_guaranteed_ohko_threat_exists": False,
        "known_executed_possible_ohko_threat_exists": False,
        "known_threat_evaluation_complete": True,
        "global_threat_complete": False,
        "all_known_actions_preempted": "false",
        "no_known_guaranteed_ohko": "true",
    }
    row.update(changes)
    return row


def _pair(candidate_id, move_id, ohko, *, order="insufficient_context", preemption="executable"):
    return {
        "self_candidate_id": candidate_id,
        "opponent_candidate_id": f"opponent-action:session:opponent:{move_id}:0",
        "pair_mechanical_completeness": True,
        "opponent_move_success": {"status": "allowed"},
        "opponent_action_preemption_status": preemption,
        "opponent_ohko_result": ohko,
        "action_order_result": {"status": order},
    }


def _bundle(summary, pairs=()):
    return {
        "known_opponent_threat_summaries": {"threat_summaries": [summary]},
        "self_opponent_pairs": {"pairs": list(pairs)},
    }


def test_projector_uses_first_frozen_danger_witness_and_partial_scope_once():
    bundle = _prepared(FIXTURES[0])["evidence_bundle"]
    dto = project_selected_threat_presentation(selected_candidate_id="self:0:slam", evidence_bundle=bundle)
    assert dto == {
        "presentation_status": "available",
        "selected_candidate_id": "self:0:slam",
        "threat_tier": "executed_guaranteed_ohko",
        "adjustment_kind": "penalty",
        "reason_code": "opponent_executed_guaranteed_ohko",
        "witness_move_id": "earthquake",
        "text": "상대가 먼저 행동하는 것으로 계산되는 earthquake의 확정 1타 위험 때문에 우선순위가 낮아졌습니다.",
        "scope_note": "아직 확인되지 않은 상대 기술은 이 판단에 포함되지 않습니다.",
    }


def test_projector_maps_unresolved_possible_and_complete_safety_without_probability_input():
    candidate = "self:0:slam"
    unresolved = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate, known_guaranteed_ohko_capability_exists=True), [_pair(candidate, "earthquake", "guaranteed")]))
    possible = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate, known_executed_possible_ohko_threat_exists=True), [_pair(candidate, "ice-beam", "possible", order="acts_second")]))
    complete_common = {"opponent_known_move_state": "complete", "known_candidate_count": 4, "unknown_slots_remaining": 0, "candidate_set_complete": True, "known_threat_evaluation_complete": True, "global_threat_complete": True}
    no_ohko = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate, **complete_common)))
    preempted = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate, **complete_common, all_known_actions_preempted="true")))
    assert unresolved["reason_code"] == "opponent_unresolved_guaranteed_ohko"
    assert "행동 순서가 확정되지 않아" in unresolved["text"] and "상대가 먼저" not in unresolved["text"]
    assert possible["reason_code"] == "opponent_executed_possible_ohko" and "확정 1타" not in possible["text"]
    assert no_ohko["reason_code"] == "complete_set_no_guaranteed_ohko" and no_ohko["scope_note"] is None
    assert preempted["reason_code"] == "complete_set_all_actions_preempted" and "확정 승리" not in preempted["text"]


def test_neutral_preempted_raw_and_malformed_evidence_are_suppressed():
    candidate = "self:0:slam"
    neutral = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate)))
    preempted_raw = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(_summary(candidate, known_guaranteed_ohko_capability_exists=True, all_known_actions_preempted="true"), [_pair(candidate, "earthquake", "guaranteed", preemption="preempted")]))
    malformed_summary = _summary(candidate)
    malformed_summary.pop("global_threat_complete")
    malformed = project_selected_threat_presentation(selected_candidate_id=candidate, evidence_bundle=_bundle(malformed_summary))
    assert neutral["presentation_status"] == preempted_raw["presentation_status"] == malformed["presentation_status"] == "unavailable"


def test_selected_formatter_only_attaches_selected_available_threat_note_and_preserves_neutral_candidate():
    prepared = _prepared(FIXTURES[0])
    winner = prepared["recommendation_request"]["candidate_comparisons"][1]
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": winner["slot_index"], "explanation_code": "clear_ranked_winner"})
    model = build_recommendation_presentation_model(completed_cycle=completed)
    text = format_recommendation_presentation_text(presentation_model=model)
    assert model["recommended_move"] == "quick"
    assert "threat_ranking" not in model["selected_candidate"]
    assert "earthquake" not in text and "아직 확인되지 않은 상대 기술" not in text
    mutated = deepcopy(model)
    assert format_recommendation_presentation_text(presentation_model=mutated) == text
