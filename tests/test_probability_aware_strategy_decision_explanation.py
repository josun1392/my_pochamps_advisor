from copy import deepcopy

from llm.advisor_probability_aware_strategy_evaluation import rank_own_action_probability_aware_candidates
from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import present_strategy_explanation, render_strategy_explanation


OWNER = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}
TARGET = {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}


def _record(move, *, ko=(1, 2), faint=(0, 1), action_type="attack", guaranteed_ko=False):
    candidate_id = f"{action_type}:{move}"
    facts = {"status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1", "candidate_id": candidate_id, "action_type": action_type, "session_id": "s", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "horizon": "immediate_action_consequence", "guaranteed_own_fainted": False, "guaranteed_opponent_fainted": guaranteed_ko, "exact_own_hp": 100}
    bindings = {"session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "attacker": deepcopy(OWNER), "target": deepcopy(TARGET), "move_id": move}
    ledger = {"status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "bindings": deepcopy(bindings), "terminal_probability_mass": {"numerator": 1, "denominator": 1}}
    metrics = {"status": "resolved", "schema_version": "exact-outcome-descriptive-metrics-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "source_ledger_status": "evaluable", "bindings": deepcopy(bindings), "terminal_probability_mass": {"numerator": 1, "denominator": 1}, "target": {"status": "resolved", "ko_probability": {"numerator": ko[0], "denominator": ko[1]}, "survival_probability": {"numerator": ko[1] - ko[0], "denominator": ko[1]}}, "own": {"status": "resolved", "self_faint_probability": {"numerator": faint[0], "denominator": faint[1]}}}
    return {"candidate_id": candidate_id, "action_type": action_type, "guaranteed_facts": facts, "exact_outcome_ledger": ledger, "descriptive_metrics": metrics}


def _explanation(*, left, right):
    ranking = rank_own_action_probability_aware_candidates(candidates=[left, right])
    orchestration = {"schema_version": "deterministic-strategy-orchestration-result-v1", "status": ranking["status"], "session_id": "s", "decision_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "selection_completeness": "complete", "candidates": [{"candidate_id": record["candidate_id"], "action_type": record["action_type"], "evidence_class": "guaranteed_facts", "facts": record["guaranteed_facts"]} for record in (left, right)], "ranking": ranking}
    return explain_detached_strategy(orchestration=orchestration)


def test_ko_probability_decision_survives_without_policy_recomputation():
    explanation = _explanation(left=_record("left", ko=(3, 4)), right=_record("right", ko=(1, 2)))
    presentation = present_strategy_explanation(explanation=explanation)
    decision = explanation["probability_aware_decisions"][0]

    assert decision["rule"] == "higher_target_ko_probability"
    assert decision["selected_candidate_id"] == "attack:left" and decision["compared_candidate_id"] == "attack:right"
    assert decision["selected_metric"] == {"numerator": 3, "denominator": 4}
    assert decision["alternative_metric"] == {"numerator": 1, "denominator": 2}
    assert decision["guaranteed_comparison_tied"] is True
    row = next(value for value in presentation["candidates"] if value["candidate_id"] == "attack:left")
    assert row["probability_aware_decisions"] == [decision]
    assert "KO 확률이 더 높음 (3/4 대 1/2)" in render_strategy_explanation(presentation=presentation)


def test_self_faint_decision_survives_and_non_probability_cases_surface_nothing():
    faint = _explanation(left=_record("left", faint=(1, 8)), right=_record("right", faint=(1, 4)))
    assert faint["probability_aware_decisions"][0]["rule"] == "lower_self_faint_probability"
    assert faint["probability_aware_decisions"][0]["selected_metric"] == {"numerator": 1, "denominator": 8}
    assert "자기 기절 확률이 더 낮음 (1/8 대 1/4)" in render_strategy_explanation(presentation=present_strategy_explanation(explanation=faint))

    guaranteed = _explanation(left=_record("left"), right=_record("right"))
    assert guaranteed["probability_aware_decisions"] == ()
    decisive = _explanation(left=_record("left", guaranteed_ko=True), right=_record("right"))
    assert decisive["probability_aware_decisions"] == ()
    attack_switch = _explanation(left=_record("left"), right=_record("bench", action_type="manual_switch"))
    assert attack_switch["probability_aware_decisions"] == ()
