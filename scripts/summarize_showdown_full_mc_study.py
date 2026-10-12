"""Preserve independent final records, training coverage and reproducible tables."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
import gzip
import json
import shutil

from advisor.learned_full_domain import load_inventory
from advisor.learning_resources import atomic_json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "models/showdown_full_mc_study_v1"


def summarize(run_root):
    root = Path(run_root)
    training = json.loads((ARTIFACT / "training.json").read_text())
    inventory = load_inventory()
    bases = {
        p["start_species"]: p["base_species"] for p in inventory["species"].values()
    }
    train_summary = {}
    for study, state in training["studies"].items():
        coverage = state["sampled_domain_coverage"]
        selection = Counter()
        for form, count in coverage["self_brought_species"].items():
            selection[bases[form]] += count
        validation_seconds = sum(
            json.loads((Path(e["checkpoint"]).parent / "validation.json").read_text())[
                "elapsed_s"
            ]
            for e in state["evaluations"]
        )
        rows = []
        for index in sorted({e["experiment"] for e in state["evaluations"]}):
            curves = []
            for e in state["evaluations"]:
                if e["experiment"] != index:
                    continue
                meta = json.loads(
                    Path(e["checkpoint"]).with_suffix(".json").read_text()
                )
                curves.append(
                    {
                        **{k: v for k, v in e.items() if k != "checkpoint"},
                        "metrics": meta["training_metrics"],
                    }
                )
            rows.append(
                {
                    "experiment": index,
                    "name": curves and meta["experiment"]["name"],
                    "seed": meta["model_seed"],
                    "curves": curves,
                }
            )
        train_summary[study] = {
            "new_transitions": state["transitions"],
            "trained_rollout_transitions": state["trained_rollout_transitions"],
            "ended_episodes": state["completed_battles"],
            "outcomes": state["episode_outcomes"],
            "program_seconds": state["wall_seconds_this_launch"],
            "periodic_validation_seconds": validation_seconds,
            "resources": state["resources"],
            "coverage_counts": {k: len(v) for k, v in coverage.items()},
            "self_brought_base_species": dict(selection),
            "independent_run_curves": rows,
            "network": state.get("network", {}),
        }
    results = {}
    for directory in sorted((root / "final").iterdir()):
        if not directory.is_dir():
            continue
        packed = directory / f"{directory.name}.json.gz"
        result = json.loads(gzip.decompress(packed.read_bytes()))
        target = ARTIFACT / "final" / directory.name
        target.mkdir(parents=True, exist_ok=False)
        for name in (packed.name, "plan.json", "resources.json", "summary.json"):
            shutil.copyfile(directory / name, target / name)
        results[directory.name] = {k: v for k, v in result.items() if k != "records"}
    atomic_json(
        ARTIFACT / "results.json",
        {
            "training": train_summary,
            "final": results,
            "no_final_results_used_for_selection": True,
            "production_default_changed": False,
            "interpretation": "sampled paired battle outcomes, not exact probabilities; four scopes do not prove competitive usage strength or preview-policy strength",
        },
    )
    print(
        json.dumps(
            {
                "training": {
                    s: {
                        k: v[k]
                        for k in (
                            "new_transitions",
                            "ended_episodes",
                            "program_seconds",
                            "coverage_counts",
                        )
                    }
                    for s, v in train_summary.items()
                },
                "final": {
                    scope: [
                        {k: r[k] for k in ("policy", "wins", "n", "truncated")}
                        for r in data["summaries"]
                        if r["opponent"] == "all"
                    ]
                    for scope, data in results.items()
                },
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    summarize(parser.parse_args().run_root)
