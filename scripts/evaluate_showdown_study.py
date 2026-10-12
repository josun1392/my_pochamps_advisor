"""Bounded paired policy comparison across separately named curriculum scopes."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import gzip
import json
import logging
import re
from time import perf_counter
import torch
from advisor.learned_policy import LearnedPolicy
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    enforce_local_network_only,
)
from scripts.evaluate_showdown_policy import evaluate


def run(config, output):
    scopes = config["scopes"]
    if (
        not 1 <= len(scopes) <= 4
        or len(config["models"]) + len(config.get("baselines", [])) > 20
    ):
        raise ValueError("bounded_study_required")
    if (
        any(not 1 <= scope["cases"] <= 128 for scope in scopes)
        or not 30 <= config["max_runtime_seconds"] <= 1800
    ):
        raise ValueError("bounded_study_cases_and_runtime_required")
    if any(
        not scope["name"].isidentifier()
        or scope["split"] not in {"validation", "test", "unseen"}
        for scope in scopes
    ):
        raise ValueError("invalid_study_scope")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    job = WindowsJob(memory_mib=4096, cpu_percent=12.5)
    budget = RuntimeLimit(output, config["max_runtime_seconds"])
    network = enforce_local_network_only()
    public_effect_warnings = {}

    class EffectSummary(logging.Filter):
        def filter(self, record):
            match = re.search(r"Unexpected effect '([^']+)'", record.getMessage())
            if not match:
                return True
            effect = match.group(1)
            public_effect_warnings[effect] = public_effect_warnings.get(effect, 0) + 1
            # Keep the first warning and summarize repeats without altering parsing.
            return public_effect_warnings[effect] == 1

    logging.getLogger("poke-env").addFilter(EffectSummary())
    started = perf_counter()
    torch.set_num_threads(1)
    cache = {}

    def loaded(path):
        path = str(Path(path).resolve())
        if path not in cache:
            cache[path] = LearnedPolicy(path, config["catalog"])
        return cache[path]

    policies = {kind: kind for kind in config.get("baselines", [])}
    policies.update({name: loaded(path) for name, path in config["models"].items()})
    rivals = {
        name: loaded(value["model"]) if isinstance(value, dict) else value
        for name, value in config["rivals"].items()
    }
    atomic_json(
        output / "plan.json",
        {
            **config,
            "policy_model_ids": {
                name: player.model_id
                for name, player in policies.items()
                if hasattr(player, "model_id")
            },
            "rival_model_ids": {
                name: player.model_id
                for name, player in rivals.items()
                if hasattr(player, "model_id")
            },
        },
    )
    results = {}
    try:
        for scope in scopes:
            result = evaluate(
                config["checkout"],
                config["catalog"],
                policies,
                split=scope["split"],
                cases=scope["cases"],
                offset=scope["offset"],
                curriculum_version=scope["curriculum_version"],
                rivals=rivals,
                tactical_diagnostics=config.get("tactical_diagnostics", True),
                stopping=budget.stopping,
            )
            compressed = gzip.compress(
                json.dumps(result, separators=(",", ":"), allow_nan=False).encode(),
                mtime=0,
            )
            (output / f"{scope['name']}.json.gz").write_bytes(compressed)
            results[scope["name"]] = {k: v for k, v in result.items() if k != "records"}
            atomic_json(output / "summary.json", results)
            print(
                json.dumps(
                    {
                        "scope": scope["name"],
                        "summary": [
                            {
                                k: r[k]
                                for k in ("policy", "wins", "losses", "n", "truncated")
                            }
                            for r in result["summaries"]
                            if r["opponent"] == "all"
                        ],
                    }
                ),
                flush=True,
            )
        atomic_json(
            output / "resources.json",
            {
                "wall_seconds": perf_counter() - started,
                "network": network,
                "unsupported_public_effect_warning_counts": public_effect_warnings,
                **job.usage(),
            },
        )
        return results
    finally:
        budget.finished.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--checkout",
        type=Path,
        help="Override the pinned native engine in a portable study plan",
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.checkout:
        config["checkout"] = str(args.checkout.resolve())
    run(config, args.output)


if __name__ == "__main__":
    main()
