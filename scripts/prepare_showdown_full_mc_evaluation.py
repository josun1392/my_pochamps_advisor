"""Freeze validation-selected seed checkpoints and create the predeclared tests.

Run after both autonomous studies finish. This never reads final results and
never changes production configuration. Original and intermediate models remain.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from hashlib import sha256
import json
import shutil

from advisor.learning_resources import atomic_json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "models/showdown_full_mc_study_v1"


def prepare(run_root):
    plan = json.loads((ARTIFACT / "plan.json").read_text())
    models = {
        name: str(ARTIFACT / "catalog_bindings" / source / "model.zip")
        for name, source in {
            "previous_action": "v2",
            "previous_generalization": "v3",
            "previous_tactical": "v4",
            "control": "control",
            "previous": "ppo2477",
        }.items()
    }
    evidence = {"selection_rule": plan["selection"], "studies": {}, "selected": {}}
    for study in ("disjoint", "roster"):
        state = json.loads((Path(run_root) / study / "state.json").read_text())
        config = json.loads((Path(run_root) / study / "config.json").read_text())
        if state["status"] != "complete":
            raise ValueError("completed_training_studies_required")
        evidence["studies"][study] = state
        for index, experiment in enumerate(config["experiments"]):
            rows = [
                e
                for e in state["evaluations"]
                if e["experiment"] == index and not e["truncated"]
            ]
            if not rows:
                evidence["selected"][experiment["name"]] = {
                    "excluded": "all validation checkpoints included truncated battles"
                }
                continue
            best = max(rows, key=lambda e: e["score"])  # stable earliest tie
            source = Path(best["checkpoint"])
            name = experiment["name"]
            target = ARTIFACT / "selected" / name
            target.mkdir(parents=True, exist_ok=False)
            for suffix in (".zip", ".json"):
                shutil.copyfile(source.with_suffix(suffix), target / ("model" + suffix))
            shutil.copyfile(
                source.parent / "validation.json", target / "validation.json"
            )
            models[name] = str(target / "model.zip")
            experiment_rows = [
                row for row in state["evaluations"] if row["experiment"] == index
            ]
            retained_rows = experiment_rows[: experiment_rows.index(best) + 1]

            def transitions(entries):
                return sum(
                    json.loads(
                        Path(row["checkpoint"]).with_suffix(".json").read_text()
                    )["training_metrics"].get("collected_transitions", 0)
                    for row in entries
                )

            evidence["selected"][name] = {
                **best,
                "model_sha256": sha256((target / "model.zip").read_bytes()).hexdigest(),
                "new_training_transitions_spent": transitions(experiment_rows),
                "selected_new_training_transitions": transitions(retained_rows),
                "initialization": "warm historical policy"
                if experiment.get("initial_model")
                else "fresh independent actor/critic",
                "species_disjoint_claim": study == "disjoint"
                and not experiment.get("initial_model"),
            }
    atomic_json(ARTIFACT / "training.json", evidence)
    output = Path(run_root) / "evaluation_configs"
    output.mkdir(exist_ok=False)
    for scope in plan["final"]["scopes"]:
        config = {
            "catalog": str(ROOT / "models/showdown_mc_domain_v1/catalog.json"),
            "max_runtime_seconds": 1800,
            "models": models,
            "baselines": [
                "random",
                "max_power",
                "heuristic",
                "champions_heuristic",
                "tactical_heuristic",
            ],
            "rivals": {
                name: (
                    {"model": models["previous_tactical"]}
                    if name == "v4"
                    else {"model": models["previous"]}
                    if name == "ppo2477"
                    else name
                )
                for name in plan["final"]["rivals"]
            },
            "tactical_diagnostics": True,
            "scopes": [{**scope, "cases": plan["final"]["cases"]}],
        }
        atomic_json(output / f"{scope['name']}.json", config)
    print(
        json.dumps(
            {
                "models": len(models),
                "selected": {
                    k: v.get("score", v.get("excluded"))
                    for k, v in evidence["selected"].items()
                },
                "config_directory": str(output),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.run_root)
