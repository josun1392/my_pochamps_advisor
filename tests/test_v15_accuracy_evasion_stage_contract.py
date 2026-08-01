from llm.advisor_candidate_contract import _comparison_facts, evaluate_move_candidate
from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_direct_mechanics import _relevant_stage_context


def _stage(side, stat, stage):
    return {"side": side, "stat": stat, "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}


def _candidate(metadata, stages=None):
    snapshot = {} if stages is None else {"stat_stage_context": {"current_stages": stages}}
    return evaluate_move_candidate(slot_index=0, move="move", battle_snapshot=snapshot, repositories={"move": metadata})


def test_accuracy_evasion_stages_use_canonical_ratio_and_preserve_base_accuracy():
    candidate = _candidate({"category": "physical", "power": 40, "type": "normal", "accuracy": 80}, [_stage("self", "accuracy", -1), _stage("opponent", "evasion", 1)])
    evidence = candidate["accuracy_evidence"]
    assert evidence["canonical_accuracy"] == 80
    assert evidence["adjusted_accuracy"] == 48
    assert evidence["accuracy_stage_evidence"] == {"self_accuracy_stage": -1, "opponent_evasion_stage": 1, "accuracy_stage_adjustment_applied": True, "resolved_accuracy_basis": "canonical_accuracy_and_stages"}


def test_accuracy_stage_omitted_is_compatible_but_explicit_unknown_fails_closed():
    metadata = {"category": "special", "power": 40, "type": "normal", "accuracy": 90}
    assert _candidate(metadata)["accuracy_evidence"] == {"status": "known_accuracy", "canonical_accuracy": 90, "outcome": "canonical_accuracy_only", "uncertainty": []}
    missing = _candidate(metadata, [_stage("self", "accuracy", 0)])["accuracy_evidence"]
    assert missing == {"status": "insufficient_context", "canonical_accuracy": 90, "outcome": None, "uncertainty": ["opponent_evasion_stage"]}


def test_always_hit_bypasses_stage_authority_and_malformed_context_fails_closed_for_ordinary_moves():
    always = _candidate({"category": "special", "power": 60, "type": "normal", "always_hit": True}, [{"side": "self", "stat": "accuracy", "stage": 8}])
    assert always["accuracy_evidence"]["status"] == "always_hits"
    malformed = _candidate({"category": "special", "power": 60, "type": "normal", "accuracy": 95}, [{"side": "self", "stat": "accuracy", "stage": 8}])
    assert malformed["accuracy_evidence"] == {"status": "unsupported_mechanic", "canonical_accuracy": 95, "outcome": None, "unsupported_reason": "accuracy_stage_context"}


def test_accuracy_evasion_only_context_does_not_require_unrelated_damage_stages():
    context = {"stat_stage_context": {"current_stages": [_stage("self", "accuracy", 1), _stage("opponent", "evasion", 0)]}}
    assert _relevant_stage_context(current=context, category="physical") == {"missing_inputs": [], "unsupported_reason": None, "applied": False, "offensive_stage_value": 0, "defensive_stage_value": 0, "evidence": None}


def test_accuracy_comparison_keeps_ranking_independent_and_presentation_uses_selected_stage_evidence():
    first = _candidate({"category": "physical", "power": 40, "type": "normal", "accuracy": 70}, [_stage("self", "accuracy", 1), _stage("opponent", "evasion", 0)])
    second = _candidate({"category": "physical", "power": 40, "type": "normal", "accuracy": 95}, [_stage("self", "accuracy", 0), _stage("opponent", "evasion", 0)])
    facts = _comparison_facts(candidate=first, comparison={"comparison_status": "rankable"}, candidates=[first, second])
    assert "known_lower_canonical_accuracy" in facts["comparison_tags"]
    model = {"status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": [], "selected_candidate": {"selected_candidate_id": 0, "selected_action": {"slot_index": 0, "move": "move"}, "explanation_code": "only_rankable_candidate", "evidence": {"mechanics_result": {"status": "known"}, "action_order": None, "accuracy_evidence": first["accuracy_evidence"], "comparison_facts": facts}, "uncertainty": {}}}
    text = format_recommendation_presentation_text(presentation_model=model)
    assert "명중률: 93%" in text and "명중 상승을 반영함" in text
    assert "canonical_accuracy_and_stages" not in text and "self_accuracy_stage" not in text
