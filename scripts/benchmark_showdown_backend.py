"""Reproducible offline transport and native Monte Carlo latency measurement."""
from pathlib import Path
import argparse
import json
import statistics
import sys
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.showdown_bridge import ShowdownBridge, SHOWDOWN_COMMIT, FORMAT_ID
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import simulate_detached_showdown, evaluate_detached_showdown
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, semantic_result


def benchmark(checkout, iterations=20):
    snapshot, scenarios = fixture_snapshot(), fixture_scenarios()
    candidates = [{"candidate_id": cid, "choices": [{"self": choice, "opponent": "move 2"}]} for cid, choice in (
        ("attack:air-slash", "move 2"), ("attack:protect", "move 3"), ("manual_switch:garchomp", "switch 2"))]
    seeds = [[7, 11, 17, n] for n in range(64)]
    def measure(call):
        started = perf_counter()
        result = call()
        assert result["status"] == "simulated", result
        assert all(s["status"] == "simulated" for s in result["scenarios"])
        return result, (perf_counter() - started) * 1000
    def distribution(values):
        return {"median_ms": round(statistics.median(values), 3), "p95_ms": round(sorted(values)[max(0, int(len(values) * .95) - 1)], 3), "max_ms": round(max(values), 3)}
    with ShowdownWorker(checkout) as worker:
        call = lambda: simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=scenarios, bridge=worker)
        baseline, cold = measure(call)
        warm = [measure(call)[1] for _ in range(iterations)]
        sample_call = lambda: evaluate_detached_showdown(runtime_snapshot=snapshot, scenarios=scenarios, candidates=candidates, seeds=seeds, bridge=worker)
        sampled, sample_cold = measure(sample_call)
        repeated = [measure(sample_call)[1] for _ in range(iterations)]
        assert semantic_result(sampled) == semantic_result(sample_call())
        assert semantic_result(baseline) == semantic_result(simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=scenarios, bridge=ShowdownBridge(checkout)))
    return {"engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID, "iterations": iterations,
        "four_scenario_worker_start_ms": round(cold, 3), "four_scenario_warm": distribution(warm),
        "sample_design": {"scenarios": 4, "candidates": 3, "seeds": 64, "native_branches": 768, "horizon_decisions": 1},
        "sample_first_ms": round(sample_cold, 3), "sample_warm": distribution(repeated),
        "reproducible_and_matches_one_shot": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100: parser.error("iterations must be 1..100")
    print(json.dumps(benchmark(args.checkout, args.iterations), indent=2))
