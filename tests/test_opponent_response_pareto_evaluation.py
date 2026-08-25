from copy import deepcopy

from llm.advisor_opponent_response_pareto_evaluation import (
    compare_opponent_response_wise_pareto_candidates,
)


OWNER = {"side": "self", "session_id": "policy", "slot_index": 0, "pokemon_id": "self"}
TARGET = {"side": "opponent", "session_id": "policy", "slot_index": 0, "pokemon_id": "target"}


def _fraction(value):
    return {"numerator": value[0], "denominator": value[1]}


def _record(name, *, guarantee=None, action_type="attack"):
    candidate_id = f"attack:{name}" if action_type == "attack" else f"switch:{name}"
    facts = {"status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1", "candidate_id": candidate_id, "action_type": action_type, "session_id": "policy", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "horizon": "immediate_action_consequence", "guaranteed_own_fainted": False, "guaranteed_opponent_fainted": False, "exact_own_hp": 100}
    if guarantee: facts.update(guarantee)
    bindings = {"session_id": "policy", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "attacker": deepcopy(OWNER), "target": deepcopy(TARGET), "move_id": name}
    ledger = {"status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "bindings": bindings, "terminal_probability_mass": _fraction((1, 1))}
    metrics = {"status": "resolved", "schema_version": "exact-outcome-descriptive-metrics-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "source_ledger_status": "evaluable", "bindings": deepcopy(bindings), "terminal_probability_mass": _fraction((1, 1)), "target": {"status": "resolved", "ko_probability": _fraction((1, 2)), "survival_probability": _fraction((1, 2))}, "own": {"status": "resolved", "self_faint_probability": _fraction((0, 1))}}
    return {"candidate_id": candidate_id, "action_type": action_type, "guaranteed_facts": facts, "exact_outcome_ledger": ledger, "descriptive_metrics": metrics}


def _profile(record, responses):
    entries = []
    for index, (action_id, opponent_ko, own_ko) in enumerate(responses):
        pair_id = f"pair:{record['candidate_id']}:{action_id}"
        base = {"pair_id": pair_id, "session_id": "policy", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "own_action_id": record["candidate_id"], "opponent_action_id": action_id, "own_actor": deepcopy(OWNER), "opponent_actor": deepcopy(TARGET)}
        pair = {"status": "evaluable", **base}
        ledger = {"status": "evaluable", "schema_version": "exact-immediate-action-pair-outcome-ledger-v1", "horizon": "immediate_action_pair", **base, "terminal_probability_mass": _fraction((1, 1))}
        metrics = {"status": "resolved", "schema_version": "exact-immediate-action-pair-descriptive-metrics-v1", "horizon": "immediate_action_pair", "source_ledger_status": "evaluable", **base, "terminal_probability_mass": _fraction((1, 1)), "own": {"status": "resolved", "ko_probability": _fraction(own_ko), "survival_probability": _fraction((own_ko[1] - own_ko[0], own_ko[1]))}, "opponent": {"status": "resolved", "ko_probability": _fraction(opponent_ko), "survival_probability": _fraction((opponent_ko[1] - opponent_ko[0], opponent_ko[1]))}}
        entries.append({"opponent_response_action_id": action_id, "pair": pair, "exact_pair_outcome_ledger": ledger, "descriptive_metrics": metrics})
    return {"status": "evaluable", "schema_version": "detached-opponent-response-profile-v1", "horizon": "immediate_action_pair", "own_action_id": record["candidate_id"], "session_id": "policy", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "opponent_actor": deepcopy(TARGET), "target_owner": deepcopy(OWNER), "selectable_response_action_ids": tuple(item[0] for item in responses), "response_entries": tuple(entries), "response_probability": "not_modeled", "ranking_influence": "none"}


def _paired(left_rows, right_rows):
    left, right = _record("left"), _record("right")
    left["opponent_response_profile"] = _profile(left, left_rows)
    right["opponent_response_profile"] = _profile(right, right_rows)
    return left, right


def test_left_and_right_response_wise_pareto_dominance_are_exact():
    left, right = _paired((("opponent_attack:a", (3, 4), (0, 1)), ("opponent_attack:b", (1, 2), (1, 8))), (("opponent_attack:a", (1, 2), (0, 1)), ("opponent_attack:b", (1, 2), (1, 4))))
    result = compare_opponent_response_wise_pareto_candidates(left=left, right=right)
    assert result["status"] == "resolved" and result["comparison"] == "left_preferred"
    assert result["preference_source"] == "opponent_response_wise_pareto"
    reverse = compare_opponent_response_wise_pareto_candidates(left=right, right=left)
    assert reverse["comparison"] == "right_preferred"


def test_cross_response_tradeoff_and_exact_equality_preserve_ties():
    left, right = _paired((("opponent_attack:a", (3, 4), (0, 1)), ("opponent_attack:b", (1, 4), (0, 1))), (("opponent_attack:a", (1, 2), (0, 1)), ("opponent_attack:b", (1, 2), (0, 1))))
    assert compare_opponent_response_wise_pareto_candidates(left=left, right=right)["comparison"] == "tied"
    equal_left, equal_right = _paired((("opponent_attack:a", (1, 2), (0, 1)),), (("opponent_attack:a", (8, 16), (0, 3)),))
    assert compare_opponent_response_wise_pareto_candidates(left=equal_left, right=equal_right)["comparison"] == "tied"


def test_one_strict_improvement_dominates_and_profiles_remain_immutable():
    left, right = _paired((("opponent_attack:a", (1, 2), (0, 1)),), (("opponent_attack:a", (1, 2), (1, 8)),))
    original = deepcopy(left["opponent_response_profile"])
    result = compare_opponent_response_wise_pareto_candidates(left=left, right=right)
    assert result["comparison"] == "left_preferred"
    assert left["opponent_response_profile"] == original
    assert result["response_policy"]["response_probability"] == "not_modeled"


def test_mismatched_or_rejected_profiles_fail_closed_and_unavailable_preserves_base_tie():
    left, right = _paired((("opponent_attack:a", (1, 2), (0, 1)),), (("opponent_attack:a", (1, 2), (0, 1)),))
    wrong = deepcopy(right); wrong["opponent_response_profile"]["selectable_response_action_ids"] = ("opponent_attack:b",)
    assert compare_opponent_response_wise_pareto_candidates(left=left, right=wrong)["status"] == "rejected"
    rejected = deepcopy(right); rejected["opponent_response_profile"]["source_runtime_fingerprint"] = "stale"
    assert compare_opponent_response_wise_pareto_candidates(left=left, right=rejected)["status"] == "rejected"
    incomplete = deepcopy(right); incomplete["opponent_response_profile"] = {"status": "incomplete", "reason": "partial_response_set"}
    result = compare_opponent_response_wise_pareto_candidates(left=left, right=incomplete)
    assert result["status"] == "resolved" and result["comparison"] == "tied" and result["reason"] == "opponent_response_profile_not_applicable"
    unsupported = deepcopy(right); unsupported["opponent_response_profile"] = {"status": "unsupported", "reason": "unsupported_response_pair"}
    assert compare_opponent_response_wise_pareto_candidates(left=left, right=unsupported)["comparison"] == "tied"


def test_decisive_own_comparison_and_attack_switch_never_use_response_policy():
    left, right = _paired((("opponent_attack:a", (0, 1), (1, 1)),), (("opponent_attack:a", (1, 1), (0, 1)),))
    left["guaranteed_facts"]["guaranteed_opponent_fainted"] = True
    result = compare_opponent_response_wise_pareto_candidates(left=left, right=right)
    assert result["comparison"] == "left_preferred" and result["preference_source"] == "guaranteed_facts"
    switch = _record("switch", action_type="manual_switch")
    switched = compare_opponent_response_wise_pareto_candidates(left=left, right=switch)
    assert switched["comparison"] == "left_preferred" and switched["preference_source"] == "guaranteed_facts"
    neutral_left, neutral_right = _paired((("opponent_attack:a", (1, 1), (0, 1)),), (("opponent_attack:a", (0, 1), (1, 1)),))
    neutral_switch = _record("neutral-switch", action_type="manual_switch")
    neutral = compare_opponent_response_wise_pareto_candidates(left=neutral_left, right=neutral_switch)
    assert neutral["comparison"] == "tied" and neutral["preference_source"] == "stable_guaranteed_tie"
