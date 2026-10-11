"""Repeated native branching, explicit plans, local worker recovery and identity."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import evaluate_detached_showdown, simulate_detached_showdown
from scripts.verify_showdown_integration import fixture_scenarios, fixture_snapshot, semantic_result


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def evaluate(worker, candidates=None, seeds=None):
    return evaluate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=fixture_scenarios()[1:2],
        candidates=candidates or [
            {"candidate_id": "attack:air-slash", "choices": [{"self": "move 2", "opponent": "move 2"}]},
            {"candidate_id": "attack:protect", "choices": [{"self": "move 3", "opponent": "move 2"}]},
            {"candidate_id": "manual-switch:garchomp", "choices": [{"self": "switch 2", "opponent": "move 1"}]},
        ], seeds=seeds or [[7, 11, 17, n] for n in range(64)], bridge=worker)


def test_seeded_samples_reproduce_and_preserve_live_inputs(worker):
    first = evaluate(worker)
    assert first["status"] == "simulated", first
    result = first["scenarios"][0]["evaluation"]
    assert result["interpretation"] == "conditional_monte_carlo_estimate_not_exact_probability"
    attack, protect, switch = result["candidates"]
    assert all(row["sample_count"] == 64 for row in result["candidates"])
    assert len({s["opponent_hp"] for s in attack["samples"]}) > 2
    assert protect["mean_opponent_team_hp"] > attack["mean_opponent_team_hp"]
    assert switch["mean_self_team_hp"] < protect["mean_self_team_hp"]
    pid = worker._process.pid
    assert semantic_result(evaluate(worker)) == semantic_result(first)
    assert worker._process.pid == pid


def test_multiturn_plan_uses_native_pp_and_switch_boundaries(worker):
    candidates = [{"candidate_id": "plan:protect-twice", "choices": [
        {"self": "move 3", "opponent": "move 2"}, {"self": "move 2", "opponent": "move 3"}]}]
    result = evaluate(worker, candidates, [[1, 2, 3, 4]])["scenarios"][0]["evaluation"]["candidates"][0]
    assert result["status"] == "evaluated"
    assert result["samples"][0]["turn"] == 3
    assert result["samples"][0]["decisions"] == 2
    invalid = deepcopy(candidates)
    invalid[0]["choices"][1]["self"] = "move 99"
    row = evaluate(worker, invalid)["scenarios"][0]["evaluation"]["candidates"][0]
    assert row == {"status": "rejected", "candidate_id": "plan:protect-twice", "reason": "illegal_choice"}
    assert evaluate(worker)["status"] == "simulated"


def test_duplicate_seeds_and_oversized_plans_are_rejected(worker):
    result = evaluate(worker, seeds=[[1, 2, 3, 4]] * 2)
    assert result["scenarios"][0]["reason"] == "invalid_sample_seeds"
    result = evaluate(worker, candidates=[{"candidate_id": "bad", "choices": [{"self": "move 3", "opponent": "move 2"}] * 9}])
    assert result["scenarios"][0]["reason"] == "invalid_sample_candidates"


def test_complete_native_ko_switch_and_next_turn_plan(worker):
    plans = [{"candidate_id": "attack:flamethrower", "choices": [
        {"self": "move 1", "opponent": "move 1"},
        {"self": "", "opponent": "switch 2"},
        {"self": "move 3", "opponent": "move 1"}]}]
    result = evaluate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=fixture_scenarios()[:1],
        candidates=plans, seeds=[[1, 2, 3, 4]], bridge=worker)["scenarios"][0]["evaluation"]["candidates"][0]
    assert result["status"] == "evaluated", result
    assert result["opponent_new_faint_samples"] == 1
    assert result["samples"][0]["decisions"] == 3
    assert result["samples"][0]["turn"] == 3


def test_worker_serializes_sessions_and_recovers_from_exit(worker):
    def run(session):
        return simulate_detached_showdown(runtime_snapshot=fixture_snapshot(session_id=session), scenarios=fixture_scenarios()[1:2], bridge=worker)
    with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, ["session-one", "session-two"]))
    assert [r["session_id"] for r in results] == ["session-one", "session-two"]
    process = worker._process
    process.kill()
    process.wait(timeout=2)
    assert run("new-session")["status"] == "simulated"
    assert worker._process.pid != process.pid


def test_timeout_discards_worker_and_can_restart(worker):
    worker.timeout_s = .000001
    assert evaluate(worker)["reason"] == "showdown_timeout"
    assert worker._process is None
    worker.timeout_s = 10
    assert evaluate(worker)["status"] == "simulated"
    worker.close()
    assert worker._process is None
