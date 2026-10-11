"""Paired, held-out native battle evaluations. No training or hidden policy input."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
import json
from math import sqrt
from time import perf_counter
import numpy as np
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.showdown_environment import ShowdownEnvironment


def wilson(wins, n):
    if not n:
        return [0, 1]
    z = 1.959963984540054
    p = wins / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [center - margin, center + margin]


def paired_comparisons(records, policies):
    """Resample case clusters, retaining their three rival strata together."""
    cases = sorted({r["case"] for r in records})
    scores = {
        kind: np.asarray(
            [
                sum(
                    r["winner"] == "self" and not r["truncated"]
                    for r in records
                    if r["policy"] == kind and r["case"] == case
                )
                / 3
                for case in cases
            ]
        )
        for kind in policies
    }
    rng = np.random.default_rng(20261012)
    draws = rng.integers(0, len(cases), size=(2000, len(cases)))
    result = []
    for kind in policies:
        if kind in {"random", "max_power", "heuristic", "untrained"}:
            continue
        for base in ("random", "heuristic", "untrained"):
            if base not in scores:
                continue
            difference = scores[kind] - scores[base]
            interval = np.quantile(difference[draws].mean(axis=1), [0.025, 0.975])
            result.append(
                {
                    "policy": kind,
                    "baseline": base,
                    "paired_win_fraction_difference": float(difference.mean()),
                    "case_cluster_bootstrap_95": [float(x) for x in interval],
                    "independent_case_clusters": len(cases),
                    "resamples": 2000,
                }
            )
    return result


def evaluate(checkout, catalog, policies, *, split="validation", cases=24, offset=0):
    if not 1 <= cases <= 256 or split not in {"validation", "test", "unseen"}:
        raise ValueError("bounded_held_out_evaluation_required")
    started = perf_counter()
    records = []
    with ShowdownEnvironment(checkout, max_decisions=256) as env:
        for kind, policy in policies.items():
            for opponent in ("random", "max_power", "heuristic"):
                for index in range(offset, offset + cases):
                    env.reset(scenario(split, index))
                    rival = VisibleBaseline(opponent, index + 919)
                    player = (
                        VisibleBaseline(policy, index + 191)
                        if isinstance(policy, str)
                        else policy
                    )
                    values = []
                    steps = 0
                    while True:
                        own, other = (
                            env.observation("self"),
                            env.observation("opponent"),
                        )
                        if isinstance(player, LearnedPolicy):
                            proof = player.infer(own)
                            action = proof["action_index"]
                            if not own["action_mask"][26]:
                                values.append(proof["discounted_return_estimate"])
                        else:
                            action = player.act(own)
                        result = env.step(
                            {"self": action, "opponent": rival.act(other)},
                            revision=own["revision"],
                        )
                        steps += 1
                        if result["terminated"] or result["truncated"]:
                            break
                    reward = result["rewards"]["self"]
                    error = (
                        float(
                            np.mean(
                                [
                                    (v - (0.99 ** (len(values) - 1 - i)) * reward) ** 2
                                    for i, v in enumerate(values)
                                ]
                            )
                        )
                        if values and not result["truncated"]
                        else None
                    )
                    records.append(
                        {
                            "policy": kind,
                            "opponent": opponent,
                            "case": index,
                            "winner": result["winner"],
                            "truncated": result["truncated"],
                            "decisions": steps,
                            "return": reward,
                            "value_discounted_return_mse": error,
                        }
                    )
    summaries = []
    for kind in policies:
        for opponent in ("random", "max_power", "heuristic", "all"):
            rows = [
                r
                for r in records
                if r["policy"] == kind
                and (opponent == "all" or r["opponent"] == opponent)
            ]
            counts = Counter(
                "truncated" if r["truncated"] else r["winner"] or "draw" for r in rows
            )
            n = len(rows)
            wins = counts["self"]
            valid = [
                r["value_discounted_return_mse"]
                for r in rows
                if r["value_discounted_return_mse"] is not None
            ]
            summaries.append(
                {
                    "policy": kind,
                    "opponent": opponent,
                    "n": n,
                    "wins": wins,
                    "losses": counts["opponent"],
                    "draws": counts["draw"],
                    "truncated": counts["truncated"],
                    "win_fraction": wins / n,
                    "wilson_95": wilson(wins, n),
                    "mean_return": sum(r["return"] for r in rows) / n,
                    "mean_decisions": sum(r["decisions"] for r in rows) / n,
                    "value_discounted_return_mse": sum(valid) / len(valid)
                    if valid
                    else None,
                }
            )
    return {
        "schema_version": "showdown-learned-evaluation-v1",
        "split": split,
        "cases_per_opponent": cases,
        "offset": offset,
        "interpretation": "held_out_sampled_win_frequencies_not_exact_probabilities",
        "elapsed_s": perf_counter() - started,
        "policies": {
            k: (v if isinstance(v, str) else v.model_id) for k, v in policies.items()
        },
        "summaries": summaries,
        "paired_comparisons": paired_comparisons(records, policies),
        "uncertainty_scope": "per_stratum_Wilson_and_paired_case_cluster_bootstrap; pooled_Wilson_is_descriptive",
        "records": records,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--model", type=Path, action="append", default=[])
    p.add_argument("--untrained", type=Path)
    p.add_argument("--cases", type=int, default=24)
    p.add_argument(
        "--split", default="validation", choices=["validation", "test", "unseen"]
    )
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("new_evaluation_output_required")
    policies = {kind: kind for kind in ("random", "max_power", "heuristic")}
    if a.untrained:
        policies["untrained"] = LearnedPolicy(
            a.untrained, a.catalog, require_manifest=False
        )
    for path in a.model:
        policies[path.stem] = LearnedPolicy(path, a.catalog)
    report = evaluate(
        a.checkout, a.catalog, policies, split=a.split, cases=a.cases, offset=a.offset
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
