"""Native request-driven multi-turn play: policies are hypothetical, not truth."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import simulate_detached_showdown
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, semantic_result, snapshot_from_state


def policy(horizon=64):
    return {"schema_version": "showdown-rollout-policy-v1", "policy": "showdown-random-player", "max_decisions": horizon,
        "self": {"move_probability": 1, "mega_probability": 0}, "opponent": {"move_probability": 1, "mega_probability": 0}}


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def evaluate(worker, *, horizon=64, pivot=False, include_traces=False, seed_count=8):
    snapshot, scenario = fixture_snapshot(), fixture_scenarios()[0]
    if pivot:
        scenario["teams"]["self"][0], scenario["teams"]["self"][2] = scenario["teams"]["self"][2], scenario["teams"]["self"][0]
        scenario["teams"]["self"][0]["moves"] = ["Volt Switch", "Protect"]
        snapshot["state"]["self_side"]["pokemon"][0] = {"pokemon_id": "rotom-wash", "current_hp": 127, "max_hp": 127, "fainted": False}
        snapshot = snapshot_from_state(snapshot["state"])
    scenario["evaluation"] = {"rollout_policy": policy(horizon), "include_traces": include_traces,
        "seeds": [[7, 11, 17, n] for n in range(seed_count)], "candidates": [{"candidate_id": "attack", "choices": [
            {"self": "move voltswitch" if pivot else "move flamethrower", "opponent": "move swordsdance" if pivot else "move bulletpunch"}]}]}
    before = deepcopy((snapshot, scenario))
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    assert (snapshot, scenario) == before
    return result


def candidate(result):
    assert result["status"] == "simulated", result
    row = result["scenarios"][0]["evaluation"]["candidates"][0]
    assert row["status"] == "evaluated", row
    return row


def test_reuses_upstream_policy_through_native_faint_replacements_and_terminal_results(worker):
    result = evaluate(worker, horizon=128, include_traces=True)
    row = candidate(result)
    assert row["ended_samples"] == 8, row
    assert row["truncated_samples"] == 0
    assert row["self_win_samples"] + row["opponent_win_samples"] + row["draw_samples"] == 8
    assert row["forced_replacement_samples"] == 8
    assert all(any(t["request_state"] == "switch" for t in s["trace"]) for s in row["samples"])
    assert semantic_result(evaluate(worker, horizon=128, include_traces=True)) == semantic_result(result)


def test_pivot_request_is_answered_without_losing_pending_opponent_action(worker):
    row = candidate(evaluate(worker, horizon=4, pivot=True, include_traces=True, seed_count=1))
    trace = row["samples"][0]["trace"]
    assert trace[0]["next_request_state"] == "switch"
    assert trace[1]["choices"]["self"].startswith("switch ")
    assert trace[1]["choices"]["opponent"] == ""
    assert trace[1]["turn"] == 2  # native queued Swords Dance executes before nextTurn
    assert row["mean_decisions"] == 4
    assert row["immediate"]["request_counts"] == {"move": 0, "switch": 1, "ended": 0}
    assert row["immediate"]["pending_action_samples"] == 1


def test_horizon_unfinished_samples_are_not_reported_as_losses(worker):
    row = candidate(evaluate(worker, horizon=1))
    assert row["truncated_samples"] == 8 and row["ended_samples"] == 0
    assert row["self_win_samples"] == row["opponent_win_samples"] == row["draw_samples"] == 0


def test_first_request_evidence_is_independent_of_rollout_horizon(worker):
    short = candidate(evaluate(worker, horizon=1))
    long = candidate(evaluate(worker, horizon=64))
    assert short["immediate"] == long["immediate"]
    assert short["immediate"]["opponent_new_faint_samples"] == 8
    assert short["immediate"]["request_counts"]["switch"] == 8


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(policy="custom-unverified-ai"), lambda p: p.update(max_decisions=129),
    lambda p: p["self"].update(move_probability=0), lambda p: p["self"].update(mega_probability=2),
])
def test_policy_contract_fail_closed(worker, mutate):
    scenario = fixture_scenarios()[0]
    rollout = policy()
    mutate(rollout)
    scenario["evaluation"] = {"rollout_policy": rollout, "seeds": [[1, 2, 3, 4]],
        "candidates": [{"candidate_id": "attack", "choices": [scenario["choices"]]}]}
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)
    assert result["status"] == "rejected"
    assert result["scenarios"][0]["reason"] == "invalid_rollout_policy"
