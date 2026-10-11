"""Bounded offline observation -> policy -> action -> reward -> reset smoke.

This tests a simple request-mask policy, not a learned strategy model. Native
mechanics, masks, queues and checkpoint handling are the existing environment.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import random
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from advisor.showdown_environment import ShowdownEnvironment, ShowdownEnvironmentError
from advisor.showdown_worker import ShowdownWorker
from scripts.verify_showdown_integration import fixture_scenarios


class RequestMaskPolicy:
    """Policy has no access to environment, scenario, other request or seed."""
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def act(self, observation):
        allowed = [i for i, valid in enumerate(observation["action_mask"]) if valid]
        moves = [i for i in allowed if 6 <= i < 14]
        # Include voluntary switches while still completing practical episodes.
        candidates = moves if moves and self.rng.random() < .9 else allowed
        return self.rng.choice(candidates)


def record_trace(trace, actions, result):
    # Opaque transport revision restarts at zero; native episode semantics do not.
    result = {key: value for key, value in result.items() if key != "revision"}
    trace.update(json.dumps({"actions": actions, "result": result}, sort_keys=True).encode())


def _episode(env, index, *, record_checkpoint=False):
    scenario = fixture_scenarios()[index % 4]
    env.reset(scenario, seed=[31, 47, 61, index])
    policies = {side: RequestMaskPolicy(index * 2 + i + 1000) for i, side in enumerate(("self", "opponent"))}
    trace, timings, checkpoints = sha256(), [], 0
    while True:
        observations = {side: env.observation(side) for side in policies}
        actions = {side: policies[side].act(observations[side]) for side in policies}
        stamp = perf_counter()
        result = env.step(actions, revision=observations["self"]["revision"])
        timings.append((perf_counter() - stamp) * 1000)
        record_trace(trace, actions, result)
        if record_checkpoint and result["decisions"] == 3:
            # Real native save/restart, including policy RNG maintained by caller.
            checkpoint = env.save()
            env.restart(checkpoint)
            checkpoints += 1
        if result["terminated"] or result["truncated"]:
            break
    return {"index": index, "winner": result["winner"], "terminated": result["terminated"], "truncated": result["truncated"],
            "decisions": result["decisions"], "reward": result["rewards"]["self"], "trace": trace.hexdigest(),
            "checkpoints": checkpoints}, timings


def run_group(checkout, indices, lanes):
    started = perf_counter()
    results, timings = [], []
    with ShowdownWorker(checkout, timeout_s=30) as worker, ExitStack() as stack:
        environments = [stack.enter_context(ShowdownEnvironment(worker=worker)) for _ in range(lanes)]
        pending, active, peak_rss, peak_heap, phases, rejected = list(indices), {}, 0, 0, {}, 0
        resets = 0
        while pending or active:
            for env in environments:
                if env in active or not pending:
                    continue
                index = pending.pop(0)
                env.reset(fixture_scenarios()[index % 4], seed=[31, 47, 61, index])
                policies = {side: RequestMaskPolicy(index * 2 + i + 1000) for i, side in enumerate(("self", "opponent"))}
                active[env] = (index, policies, sha256())
                resets += 1
            entries, observations_by_env = [], {}
            for env, (_, policies, _) in active.items():
                observations = {side: env.observation(side) for side in policies}
                observations_by_env[env] = observations
                phase = observations["self"]["request_state"]
                phases[phase] = phases.get(phase, 0) + 1
                entries.append((env, {side: policies[side].act(observations[side]) for side in policies}, observations["self"]["revision"]))
            stamp = perf_counter()
            transitions = ShowdownEnvironment.batch_step(entries)
            timings.append((perf_counter() - stamp) * 1000 / len(entries))
            peak_rss = max(peak_rss, environments[0].resources["rss_bytes"])
            peak_heap = max(peak_heap, environments[0].resources["heap_used_bytes"])
            for (env, actions, _), result in zip(entries, transitions):
                if isinstance(result, ShowdownEnvironmentError):
                    raise result
                index, policies, trace = active[env]
                record_trace(trace, actions, result)
                rejected += int(result["action_rejected"])
                if result["terminated"] or result["truncated"]:
                    results.append({"index": index, "winner": result["winner"], "terminated": result["terminated"], "truncated": result["truncated"],
                                    "decisions": result["decisions"], "reward": result["rewards"]["self"], "trace": trace.hexdigest()})
                    del active[env]
        # Replay one completed episode through independent scalar execution.
        replay, _ = _episode(environments[0], indices[0])
        original = next(r for r in results if r["index"] == indices[0])
        assert replay["trace"] == original["trace"], (replay, original)
        # Checkpoint/restart continuity using the same untrained observation policy.
        saved_replay, _ = _episode(environments[0], indices[0], record_checkpoint=True)
        assert saved_replay["trace"] == replay["trace"]
        for env in environments:
            env.close()
        assert environments[-1].resources["episodes"] == 0
        process_id = worker._process.pid
    assert worker._process is None
    return {"results": results, "timings": timings, "elapsed_s": perf_counter() - started,
            "peak_node_rss_mib": peak_rss / 1024 ** 2, "peak_node_heap_mib": peak_heap / 1024 ** 2,
            "phases": phases, "rejected": rejected, "resets": resets, "reproducible": True,
            "checkpoint_restart": saved_replay["checkpoints"], "closed_pid": process_id}


def verify(checkout, episodes=32, workers=2, lanes=4):
    started = perf_counter()
    with ThreadPoolExecutor(workers) as pool:
        jobs = [pool.submit(run_group, checkout, list(range(i, episodes, workers)), lanes) for i in range(workers)]
        groups = [job.result() for job in jobs]
    elapsed = perf_counter() - started
    results = sorted((row for group in groups for row in group["results"]), key=lambda row: row["index"])
    timings = sorted(ms for group in groups for ms in group["timings"])
    assert len(results) == episodes and all(row["terminated"] and not row["truncated"] for row in results), results
    assert all(row["reward"] == (1 if row["winner"] == "self" else -1 if row["winner"] == "opponent" else 0) for row in results)
    decisions = sum(row["decisions"] for row in results)
    return {"status": "training_environment_ready", "policy": "untrained_request_mask_policy", "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID, "episodes": episodes, "terminal_episodes": episodes, "truncated": 0,
            "wins": sum(r["winner"] == "self" for r in results), "losses": sum(r["winner"] == "opponent" for r in results),
            "draws": sum(r["winner"] is None for r in results), "decisions": decisions,
            "workers": workers, "lanes_per_worker": lanes, "elapsed_s": elapsed,
            "throughput_episodes_s": episodes / elapsed, "throughput_decisions_s": decisions / elapsed,
            "amortized_step_p50_ms": statistics.median(timings), "amortized_step_p95_ms": timings[int((len(timings) - 1) * .95)],
            "peak_node_rss_mib_by_worker": [g["peak_node_rss_mib"] for g in groups],
            "peak_node_heap_mib_by_worker": [g["peak_node_heap_mib"] for g in groups],
            "reproducibility_checked_workers": workers, "checkpoint_restart_checked_workers": workers,
            "requests_by_phase": {p: sum(g["phases"].get(p, 0) for g in groups) for p in ("move", "switch")},
            "native_request_rejections": sum(g["rejected"] for g in groups), "processes_closed": workers,
            "trace_digest": sha256(json.dumps(results, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--showdown-checkout", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--lanes", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.episodes <= 1024 or not 1 <= args.workers <= min(8, args.episodes) or not 1 <= args.lanes <= 32:
        parser.error("bounded episode/worker/lane values required")
    print(json.dumps(verify(args.showdown_checkout, args.episodes, args.workers, args.lanes), indent=2))


if __name__ == "__main__":
    main()
