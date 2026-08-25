from copy import deepcopy

from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import present_strategy_explanation, render_strategy_explanation


OWNER = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}


def _fraction(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator}


def _comparison(*, selected="left"):
    return {
        "status": "resolved", "schema_version": "opponent-response-wise-pareto-evaluation-v1",
        "reason": "response_wise_pareto_dominance", "comparison": f"{selected}_preferred",
        "preference_source": "opponent_response_wise_pareto", "left_candidate_id": "attack:left", "right_candidate_id": "attack:right",
        "base_comparison": {"status": "resolved", "comparison": "tied", "reason": "exact_probability_metrics_tie"},
        "response_policy": {"status": "eligible", "response_action_ids": ("opponent_attack:a", "opponent_attack:b"), "bindings": {"session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER)}, "response_probability": "not_modeled", "ranking_influence": "none", "response_comparisons": (
            {"opponent_response_action_id": "opponent_attack:a", "left_opponent_ko_probability": _fraction(3, 4), "right_opponent_ko_probability": _fraction(1, 2), "left_own_ko_probability": _fraction(0, 1), "right_own_ko_probability": _fraction(0, 1), "left_weakly_dominates": True, "right_weakly_dominates": False},
            {"opponent_response_action_id": "opponent_attack:b", "left_opponent_ko_probability": _fraction(1, 2), "right_opponent_ko_probability": _fraction(1, 2), "left_own_ko_probability": _fraction(1, 8), "right_own_ko_probability": _fraction(1, 4), "left_weakly_dominates": True, "right_weakly_dominates": False},
        )},
    }


def _orchestration(comparison):
    selected = "attack:left" if comparison.get("comparison") == "left_preferred" else "attack:right"
    return {"schema_version": "deterministic-strategy-orchestration-result-v1", "status": "resolved", "session_id": "s", "decision_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "selection_completeness": "complete", "candidates": [{"candidate_id": "attack:left", "action_type": "attack", "evidence_class": "guaranteed_facts", "facts": {}}, {"candidate_id": "attack:right", "action_type": "attack", "evidence_class": "guaranteed_facts", "facts": {}}], "ranking": {"status": "resolved", "preferred_frontier": [selected], "pairwise_matrix": [comparison]}}


def test_pareto_decision_preserves_exact_response_evidence_through_presentation():
    explanation = explain_detached_strategy(orchestration=_orchestration(_comparison()))
    assert explanation["status"] == "resolved"
    decision = explanation["probability_aware_decisions"][0]
    assert decision["rule"] == "response_wise_pareto_dominance"
    assert decision["selected_candidate_id"] == "attack:left" and decision["compared_candidate_id"] == "attack:right"
    assert decision["shared_response_action_ids"] == ("opponent_attack:a", "opponent_attack:b")
    assert decision["response_evidence"][0]["selected_opponent_ko_probability"] == _fraction(3, 4)
    assert decision["response_evidence"][1]["selected_own_ko_probability"] == _fraction(1, 8)
    presentation = present_strategy_explanation(explanation=explanation)
    row = next(value for value in presentation["candidates"] if value["candidate_id"] == "attack:left")
    assert row["probability_aware_decisions"] == [decision]
    assert "모든 확인된 상대 응답에서 Pareto 우세" in render_strategy_explanation(presentation=presentation)


def test_reverse_dominance_is_explained_and_ties_or_non_pareto_sources_do_not_fabricate_a_decision():
    reverse = _comparison(selected="right")
    for row in reverse["response_policy"]["response_comparisons"]:
        for left_key, right_key in (("left_opponent_ko_probability", "right_opponent_ko_probability"), ("left_own_ko_probability", "right_own_ko_probability")):
            row[left_key], row[right_key] = row[right_key], row[left_key]
        row["right_weakly_dominates"] = True; row["left_weakly_dominates"] = False
    explanation = explain_detached_strategy(orchestration=_orchestration(reverse))
    assert explanation["probability_aware_decisions"][0]["selected_candidate_id"] == "attack:right"
    tied = _comparison(); tied["comparison"] = "tied"; tied["preference_source"] = "stable_own_action_tie"; tied["reason"] = "response_wise_pareto_tradeoff_or_exact_tie"
    assert explain_detached_strategy(orchestration=_orchestration(tied))["probability_aware_decisions"] == ()
    existing = _comparison(); existing["preference_source"] = "target_ko_probability"; existing["reason"] = "higher_exact_target_ko_probability"
    assert explain_detached_strategy(orchestration=_orchestration(existing))["status"] == "rejected"


def test_mismatched_or_incomplete_pareto_provenance_fails_closed_without_policy_recomputation():
    stale = _comparison(); stale["response_policy"]["bindings"]["source_runtime_fingerprint"] = ""
    assert explain_detached_strategy(orchestration=_orchestration(stale))["status"] == "rejected"
    mismatch = _comparison(); mismatch["response_policy"]["bindings"]["decision_owner"] = {"session_id": "other"}
    assert explain_detached_strategy(orchestration=_orchestration(mismatch))["status"] == "rejected"
    incomplete = _comparison(); incomplete["response_policy"]["status"] = "incomplete"
    assert explain_detached_strategy(orchestration=_orchestration(incomplete))["status"] == "rejected"
