"""Bounded independent broad-roster evaluation with frozen learned rivals."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
import json
from time import perf_counter, process_time
import torch
from advisor.learned_policy import LearnedPolicy
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    enforce_local_network_only,
)
from scripts.evaluate_showdown_policy import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument(
        "--catalog", type=Path, default=Path("models/showdown_initial_v1/catalog.json")
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="label=trusted_local_checkpoint.zip",
    )
    parser.add_argument("--frozen-opponent", type=Path, required=True)
    parser.add_argument(
        "--split",
        nargs="+",
        choices=["validation", "test", "unseen"],
        default=["test", "unseen"],
    )
    parser.add_argument("--cases", type=int, default=96)
    parser.add_argument("--offset", type=int, default=90000)
    parser.add_argument(
        "--curriculum-version",
        default="showdown-learning-curriculum-v3",
        choices=[
            "showdown-learning-curriculum-v3",
            "showdown-learning-curriculum-v4",
            "showdown-learning-curriculum-v5",
            "showdown-learning-curriculum-v6",
        ],
    )
    parser.add_argument("--tactical-diagnostics", action="store_true")
    parser.add_argument("--tactical-baseline", action="store_true")
    parser.add_argument("--max-runtime-seconds", type=int, default=900)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 30 <= args.max_runtime_seconds <= 1800 or not 1 <= args.cases <= 128:
        parser.error("bounded runtime/case count required")
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    started = perf_counter()
    budget = RuntimeLimit(args.output, args.max_runtime_seconds)
    job = WindowsJob(memory_mib=3072, cpu_percent=12.5)
    network = enforce_local_network_only()
    policies = {kind: kind for kind in ("random", "heuristic", "champions_heuristic")}
    if args.tactical_baseline:
        policies.update(max_power="max_power", tactical_heuristic="tactical_heuristic")
    for entry in args.model:
        label, path = entry.split("=", 1)
        if not label or label in policies:
            raise ValueError("unique_model_labels_required")
        policies[label] = LearnedPolicy(path, args.catalog)
    frozen = LearnedPolicy(args.frozen_opponent, args.catalog)
    rivals = {kind: kind for kind in ("max_power", "heuristic", "champions_heuristic")}
    rivals["previous"] = frozen
    if args.tactical_baseline:
        rivals["tactical_heuristic"] = "tactical_heuristic"
    try:
        for split in args.split:

            def progress(records):
                atomic_json(
                    args.output / "progress.json",
                    {
                        "split": split,
                        "completed_battles": len(records),
                        "wall_seconds": perf_counter() - started,
                        "outcomes": dict(
                            Counter(
                                "truncated" if r["truncated"] else r["winner"] or "draw"
                                for r in records
                            )
                        ),
                        "resources": job.usage(),
                    },
                )

            result = evaluate(
                args.checkout,
                args.catalog,
                policies,
                split=split,
                cases=args.cases,
                offset=args.offset,
                curriculum_version=args.curriculum_version,
                tactical_diagnostics=args.tactical_diagnostics,
                rivals=rivals,
                stopping=budget.stopping,
                progress=progress,
            )
            atomic_json(args.output / f"{split}.json", result)
            print(
                json.dumps(
                    {
                        "split": split,
                        "summary": [
                            r for r in result["summaries"] if r["opponent"] == "all"
                        ],
                        "comparisons": result["paired_comparisons"],
                    }
                ),
                flush=True,
            )
        atomic_json(
            args.output / "resources.json",
            {
                "wall_seconds": perf_counter() - started,
                "python_cpu_seconds": process_time(),
                "network": network,
                **job.usage(),
            },
        )
    finally:
        budget.finished.set()


if __name__ == "__main__":
    main()
