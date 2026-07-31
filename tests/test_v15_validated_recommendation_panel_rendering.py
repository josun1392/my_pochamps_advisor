from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_candidate_contract import build_recommendation_presentation_model, complete_recommendation_cycle
from scripts.run_sanitized_multi_move_mechanics_smoke import GROUNDING_FIXTURES, _prepared


def _presentation():
    prepared = _prepared(GROUNDING_FIXTURES[0])
    winner = prepared["recommendation_request"]["candidate_comparisons"][1]
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": winner["slot_index"], "explanation_code": "clear_ranked_winner"})
    return build_recommendation_presentation_model(completed_cycle=completed)


def test_panel_text_renders_only_validated_selected_candidate_summary():
    text = format_recommendation_presentation_text(presentation_model=_presentation())
    assert "선택 행동: slam" in text
    assert "선택 근거: 결정적 비교에서 가장 높은 후보입니다." in text
    assert "피해 범위:" in text and "피해 비율:" in text and "1회 KO 확률:" in text
    assert "candidate_comparisons" not in text and "raw_response" not in text


def test_panel_text_hides_unknown_order_and_numeric_mechanics_for_incomplete_or_unsupported_evidence():
    base = {"status": "resolved", "recommended_move": "move", "recommended_slot_index": 3, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}
    incomplete = {"selected_candidate_id": 3, "selected_action": {"slot_index": 3, "move": "move"}, "explanation_code": "only_rankable_candidate", "evidence": {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["hidden"]}, "action_order": {"status": "insufficient_context"}, "comparison_facts": {"comparison_tags": ["insufficient_mechanics_context"]}}, "uncertainty": {}}
    text = format_recommendation_presentation_text(presentation_model={**base, "selected_candidate": incomplete})
    assert "추가 전투 정보" in text and "피해 범위:" not in text and "행동 순서:" not in text and "hidden" not in text
    unsupported = {**incomplete, "evidence": {**incomplete["evidence"], "mechanics_result": {"status": "unsupported_mechanic"}, "comparison_facts": {"comparison_tags": ["unsupported_mechanic"]}}}
    assert "지원 범위 밖" in format_recommendation_presentation_text(presentation_model={**base, "selected_candidate": unsupported})


def test_failure_or_next_analyzing_presentation_has_no_selected_candidate_summary():
    failure = {"status": "validation_failed", "selected_candidate": _presentation()["selected_candidate"]}
    text = format_recommendation_presentation_text(presentation_model=failure)
    assert "선택 행동:" not in text
