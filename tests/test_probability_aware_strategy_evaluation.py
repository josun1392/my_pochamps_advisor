from copy import deepcopy

from llm.advisor_probability_aware_strategy_evaluation import (
    compare_own_action_probability_aware_candidates,
    rank_own_action_probability_aware_candidates,
)


OWNER = {"side": "self", "session_id": "policy", "slot_index": 0, "pokemon_id": "self"}
TARGET = {"side": "opponent", "session_id": "policy", "slot_index": 0, "pokemon_id": "target"}


def _record(name, *, ko=(1, 2), faint=(0, 1), action_type="attack", guarantee=None, ledger_status="evaluable", metric_status="resolved", runtime="runtime"):
    candidate_id = f"attack:{name}" if action_type == "attack" else f"switch:{name}"
    facts = {"status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1", "candidate_id": candidate_id, "action_type": action_type, "session_id": "policy", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "horizon": "immediate_action_consequence", "guaranteed_own_fainted": False, "guaranteed_opponent_fainted": False, "exact_own_hp": 100}
    if guarantee:
        facts.update(guarantee)
    bindings = {"session_id": "policy", "source_runtime_fingerprint": runtime, "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER)}
    if action_type == "attack":
        bindings.update({"attacker": deepcopy(OWNER), "target": deepcopy(TARGET), "move_id": name})
    ledger = {"status": ledger_status, "schema_version": "exact-predictive-outcome-ledger-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "bindings": deepcopy(bindings), "terminal_probability_mass": {"numerator": 1, "denominator": 1}}
    metrics = {"status": metric_status, "schema_version": "exact-outcome-descriptive-metrics-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "source_ledger_status": "evaluable", "bindings": deepcopy(bindings), "terminal_probability_mass": {"numerator": 1, "denominator": 1}, "target": {"status": "resolved", "ko_probability": {"numerator": ko[0], "denominator": ko[1]}, "survival_probability": {"numerator": ko[1] - ko[0], "denominator": ko[1]}}, "own": {"status": "resolved", "self_faint_probability": {"numerator": faint[0], "denominator": faint[1]}}, "ranking_influence": "none"}
    return {"candidate_id": candidate_id, "action_type": action_type, "guaranteed_facts": facts, "exact_outcome_ledger": ledger, "descriptive_metrics": metrics}


def test_guaranteed_preference_is_preserved_even_when_probability_would_favor_other_side():
    left = _record("left", ko=(0, 1), guarantee={"guaranteed_opponent_fainted": True})
    right = _record("right", ko=(1, 1), guarantee={"guaranteed_opponent_fainted": False})
    result = compare_own_action_probability_aware_candidates(left=left, right=right)
    assert result["status"] == "resolved"
    assert result["comparison"] == "left_preferred"
    assert result["preference_source"] == "guaranteed_facts"


def test_higher_exact_ko_then_lower_exact_self_faint_breaks_only_guaranteed_ties():
    ko = compare_own_action_probability_aware_candidates(left=_record("left", ko=(3, 4)), right=_record("right", ko=(1, 2)))
    assert ko["comparison"] == "left_preferred" and ko["preference_source"] == "target_ko_probability"
    faint = compare_own_action_probability_aware_candidates(left=_record("left", ko=(1, 2), faint=(1, 8)), right=_record("right", ko=(1, 2), faint=(1, 4)))
    assert faint["comparison"] == "left_preferred" and faint["preference_source"] == "self_faint_probability"


def test_equivalent_fractions_and_ignored_status_stage_or_expected_fields_remain_tied():
    left, right = _record("left", ko=(1, 2), faint=(0, 1)), _record("right", ko=(8, 16), faint=(0, 3))
    left["descriptive_metrics"].update({"hypothetical_stage_outcomes": {"status": "resolved", "outcomes": ({"probability": {"numerator": 1, "denominator": 1}},)}, "expected_damage": 999})
    right["descriptive_metrics"].update({"hypothetical_target_conditions": {"status": "resolved", "outcomes": ({"probability": {"numerator": 1, "denominator": 1}},)}, "expected_damage": 0})
    result = compare_own_action_probability_aware_candidates(left=left, right=right)
    assert result["comparison"] == "tied" and result["reason"] == "exact_probability_metrics_tie"


def test_switch_pairs_and_incomplete_or_unsupported_ledgers_preserve_safe_base_tie():
    attack, switch = _record("attack"), _record("switch", action_type="manual_switch")
    result = compare_own_action_probability_aware_candidates(left=attack, right=switch)
    assert result["status"] == "resolved" and result["comparison"] == "tied" and result["preference_source"] == "stable_guaranteed_tie"
    incomplete = compare_own_action_probability_aware_candidates(left=_record("left", ledger_status="incomplete"), right=_record("right"))
    unsupported = compare_own_action_probability_aware_candidates(left=_record("left", ledger_status="unsupported"), right=_record("right"))
    assert incomplete["comparison"] == unsupported["comparison"] == "tied"
    assert incomplete["reason"] == unsupported["reason"] == "probability_tie_break_not_applicable"


def test_rejected_or_mismatched_probability_authority_fails_closed():
    rejected = compare_own_action_probability_aware_candidates(left=_record("left", ledger_status="rejected"), right=_record("right"))
    assert rejected["status"] == "rejected"
    mismatched = compare_own_action_probability_aware_candidates(left=_record("left", runtime="runtime-a"), right=_record("right", runtime="runtime-b"))
    assert mismatched["status"] == "rejected" and mismatched["reason"] == "probability_comparison_basis_mismatch"


def test_frontier_uses_wrapper_and_keeps_stable_ties_without_mutation():
    left, right = _record("left", ko=(3, 4)), _record("right", ko=(1, 2))
    ranked = rank_own_action_probability_aware_candidates(candidates=[left, right])
    assert ranked["status"] == "resolved" and ranked["preferred_frontier"] == ["attack:left"]
    tied = rank_own_action_probability_aware_candidates(candidates=[_record("left"), _record("right")])
    assert tied["preferred_frontier"] == ["attack:left", "attack:right"]
    assert left["descriptive_metrics"]["ranking_influence"] == "none"
