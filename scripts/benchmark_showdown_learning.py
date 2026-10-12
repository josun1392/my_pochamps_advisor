"""Bounded local sampling/PPO benchmarks; discarded weights are not strength evidence."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import cProfile
import pstats
from time import perf_counter
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_action_policy import TacticalActionConditionedPolicy
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    enforce_local_network_only,
)


class TimedPPO(MaskablePPO):
    update_seconds = 0

    def train(self):
        started = perf_counter()
        try:
            return super().train()
        finally:
            self.update_seconds += perf_counter() - started


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument(
        "--catalog", type=Path, default=Path("models/showdown_initial_v1/catalog.json")
    )
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mode", choices=("sampling", "ppo"), default="sampling")
    p.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8])
    p.add_argument(
        "--backend",
        nargs="+",
        choices=("dummy", "subproc"),
        default=["dummy", "subproc"],
    )
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--cpu-threads", type=int, default=1)
    p.add_argument("--steps", type=int, default=1024)
    p.add_argument("--max-runtime-seconds", type=int, default=300)
    args = p.parse_args()
    if not (
        30 <= args.max_runtime_seconds <= 600
        and 128 <= args.steps <= 8192
        and 1 <= args.cpu_threads <= 8
        and args.workers
        and set(args.workers) <= {1, 2, 4, 8}
    ):
        p.error("bounded workers/steps/threads/runtime required")
    if any(args.steps % (128 * n) for n in args.workers):
        p.error("steps must be divisible by every worker rollout size")
    args.output.mkdir(parents=True, exist_ok=False)
    budget = RuntimeLimit(args.output, args.max_runtime_seconds)
    job = WindowsJob(
        memory_mib=12288, cpu_percent=50, active_process_limit=4 * max(args.workers) + 8
    )
    network = enforce_local_network_only()
    if args.device == "cuda":
        import os

        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        if not torch.cuda.is_available():
            raise RuntimeError("configured_cuda_unavailable")
        torch.cuda.set_per_process_memory_fraction(0.15)
    torch.use_deterministic_algorithms(True)
    results = []
    try:
        for backend in args.backend:
            for workers in args.workers:
                if budget.stopping():
                    raise TimeoutError("benchmark_budget_exhausted")
                factories = [
                    LearningEnvFactory(
                        str(args.checkout.resolve()),
                        str(args.catalog.resolve()),
                        "showdown-learned-observation-v3",
                        i * 100000,
                        "showdown-learning-curriculum-v3",
                        ("max_power", "heuristic"),
                        {},
                    )
                    for i in range(workers)
                ]
                started = perf_counter()
                vector = (
                    DummyVecEnv(factories)
                    if backend == "dummy"
                    else SubprocVecEnv(factories, start_method="spawn")
                )
                startup = perf_counter() - started
                try:
                    torch.set_num_threads(args.cpu_threads)
                    vector.seed(2201)
                    vector.reset()
                    started = perf_counter()
                    update = 0
                    if args.mode == "sampling":
                        rng = np.random.default_rng(2201)
                        for _ in range(args.steps // workers):
                            if budget.stopping():
                                raise TimeoutError("benchmark_budget_exhausted")
                            masks = vector.env_method("action_masks")
                            vector.step_async(
                                [int(rng.choice(np.flatnonzero(m))) for m in masks]
                            )
                            vector.step_wait()
                    else:
                        model = TimedPPO(
                            TacticalActionConditionedPolicy,
                            vector,
                            n_steps=128,
                            batch_size=128,
                            n_epochs=4,
                            seed=2201,
                            device=args.device,
                            verbose=0,
                        )
                        started = perf_counter()
                        model.learn(args.steps)
                        update = model.update_seconds
                    elapsed = perf_counter() - started
                    episodes = [
                        r for rows in vector.env_method("drain_completed") for r in rows
                    ]
                    profile = []
                    if args.mode == "sampling" and backend == "dummy" and workers == 1:
                        prof = cProfile.Profile()
                        prof.enable()
                        for _ in range(128):
                            masks = vector.env_method("action_masks")
                            vector.step([int(np.flatnonzero(m)[-1]) for m in masks])
                        prof.disable()
                        profile = [
                            {
                                "file": k[0],
                                "line": k[1],
                                "function": k[2],
                                "calls": s[1],
                                "self_seconds": s[2],
                                "cumulative_seconds": s[3],
                            }
                            for k, s in sorted(
                                pstats.Stats(prof).stats.items(),
                                key=lambda x: x[1][3],
                                reverse=True,
                            )[:25]
                        ]
                    results.append(
                        {
                            "backend": backend,
                            "workers": workers,
                            "startup_seconds": startup,
                            "transitions": args.steps,
                            "completed_battles": len(episodes),
                            "truncated": sum(r["truncated"] for r in episodes),
                            "seconds": elapsed,
                            "transitions_per_second": args.steps / elapsed,
                            "update_seconds": update,
                            "sampling_and_other_seconds": elapsed - update,
                            "profile_top": profile,
                        }
                    )
                    atomic_json(args.output / "progress.json", {"results": results})
                finally:
                    vector.close()
        atomic_json(
            args.output / "results.json",
            {
                "schema_version": "showdown-learning-benchmark-v1",
                "configuration": {
                    k: str(v) if isinstance(v, Path) else v
                    for k, v in vars(args).items()
                },
                "torch_version": torch.__version__,
                "device": args.device,
                "cpu_threads": args.cpu_threads,
                "gpu_name": torch.cuda.get_device_name()
                if args.device == "cuda"
                else None,
                "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                if args.device == "cuda"
                else 0,
                "weights_discarded": True,
                "results": results,
                "resources": job.usage(),
                "network": network,
            },
        )
    finally:
        budget.finished.set()


if __name__ == "__main__":
    main()
