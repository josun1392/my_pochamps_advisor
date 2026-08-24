from copy import deepcopy

import llm.advisor_detached_strategy_orchestration as subject


OWNER = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}
SELECTION = {"status": "resolved", "session_id": "s", "decision_branch_fingerprint": "preview", "decision_owner": OWNER}
EXECUTION = {**SELECTION, "schema_version": "deterministic-current-execution-authority-v1"}


def _candidate(move):
    return {"schema_version": "deterministic-action-candidate-v1", "candidate_id": f"attack:{move}", "action_type": "attack", "decision_owner": OWNER, "source_branch_fingerprint": "preview", "execution_readiness": "complete"}


def _fact(candidate):
    return {"status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1", "candidate_id": candidate["candidate_id"], "action_type": "attack", "session_id": "s", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "horizon": "immediate_action_consequence", "guaranteed_own_fainted": False, "guaranteed_opponent_fainted": False, "exact_own_hp": 100}


def _probability_inputs(move, *, ko=(1, 2), runtime="runtime"):
    bindings = {"session_id": "s", "source_runtime_fingerprint": runtime, "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "attacker": deepcopy(OWNER), "target": {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}, "move_id": move}
    ledger = {"status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1", "horizon": "immediate_action_consequence", "candidate_id": f"attack:{move}", "action_type": "attack", "bindings": deepcopy(bindings), "terminal_probability_mass": {"numerator": 1, "denominator": 1}}
    metrics = {"status": "resolved", "schema_version": "exact-outcome-descriptive-metrics-v1", "horizon": "immediate_action_consequence", "candidate_id": f"attack:{move}", "action_type": "attack", "source_ledger_status": "evaluable", "bindings": deepcopy(bindings), "terminal_probability_mass": {"numerator": 1, "denominator": 1}, "target": {"status": "resolved", "ko_probability": {"numerator": ko[0], "denominator": ko[1]}, "survival_probability": {"numerator": ko[1] - ko[0], "denominator": ko[1]}}, "own": {"status": "resolved", "self_faint_probability": {"numerator": 0, "denominator": 1}}, "ranking_influence": "none"}
    return ledger, metrics


def _run(monkeypatch, *, ledgers=None, metrics=None):
    candidates = [_candidate("left"), _candidate("right")]
    monkeypatch.setattr(subject, "discover_candidates", lambda **_: {"status": "resolved", "candidates": deepcopy(candidates), "candidate_set_completeness": "complete"})
    monkeypatch.setattr(subject, "enrich_discovered_candidates", lambda **_: {"status": "resolved", "candidates": deepcopy(candidates)})
    monkeypatch.setattr(subject, "build_predictive_normal_formula_interval", lambda **_: {"completeness": "exact_complete"})
    monkeypatch.setattr(subject, "guaranteed_facts_from_normal_formula_interval", lambda **kwargs: _fact(kwargs["candidate"]))
    root = {"active": {"self": {"current_hp": 100}, "opponent": {"current_hp": 100}}}
    normal = {f"attack:{move}": {"target_owner": {}, "snapshot_damage_input": {}, "stat_provenance": {}, "trusted_level": 50} for move in ("left", "right")}
    return subject.run_detached_strategy_orchestration(decision_state=root, decision_owner=OWNER, selection_snapshot=SELECTION, execution_bundle=EXECUTION, normal_formula_inputs=normal, exact_outcome_ledgers=ledgers, descriptive_metrics=metrics)


def test_live_frontier_uses_exact_ko_tie_break_only_when_explicit_inputs_arrive(monkeypatch):
    left_ledger, left_metrics = _probability_inputs("left", ko=(3, 4))
    right_ledger, right_metrics = _probability_inputs("right", ko=(1, 2))
    result = _run(monkeypatch, ledgers={"attack:left": left_ledger, "attack:right": right_ledger}, metrics={"attack:left": left_metrics, "attack:right": right_metrics})
    assert result["ranking"]["status"] == "resolved"
    assert result["ranking"]["preferred_frontier"] == ["attack:left"]
    assert result["ranking"]["pairwise_matrix"][0]["preference_source"] == "target_ko_probability"


def test_missing_metrics_preserves_existing_frontier_tie_and_stale_basis_fails_closed(monkeypatch):
    left_ledger, left_metrics = _probability_inputs("left", ko=(3, 4))
    right_ledger, right_metrics = _probability_inputs("right", ko=(1, 2))
    preserved = _run(monkeypatch, ledgers={"attack:left": left_ledger, "attack:right": right_ledger}, metrics={"attack:left": left_metrics})
    assert preserved["ranking"]["preferred_frontier"] == ["attack:left", "attack:right"]
    stale_ledger, stale_metrics = _probability_inputs("right", runtime="other")
    rejected = _run(monkeypatch, ledgers={"attack:left": left_ledger, "attack:right": stale_ledger}, metrics={"attack:left": left_metrics, "attack:right": stale_metrics})
    assert rejected["ranking"]["status"] == "incomplete_comparison_set"
    assert rejected["ranking"]["pairwise_matrix"][0]["status"] == "rejected"
