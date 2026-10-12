"""Bounded native counterfactual audit of public decisions; no optimal labels."""

import sys
import json
import argparse
from pathlib import Path
from hashlib import sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_tactical_diagnostics import action_class
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    enforce_local_network_only,
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--model", type=Path, default=Path("models/showdown_tactical_v4/model.zip")
    )
    p.add_argument("--offset", type=int, default=48000)
    p.add_argument("--states", type=int, default=24)
    p.add_argument("--cases", type=int, default=48)
    p.add_argument(
        "--curriculum-version",
        default="showdown-learning-curriculum-v5",
        choices=[
            "showdown-learning-curriculum-v3",
            "showdown-learning-curriculum-v4",
            "showdown-learning-curriculum-v5",
            "showdown-learning-curriculum-v6",
        ],
    )
    args = p.parse_args()
    if not 1 <= args.states <= 64 or not 1 <= args.cases <= 128:
        p.error("bounded diagnostic states/cases required")
    w = Path(__file__).resolve().parents[1]
    e = args.checkout
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    budget = RuntimeLimit(out, 180)
    job = WindowsJob(memory_mib=4096, cpu_percent=12.5)
    network = enforce_local_network_only()
    model = LearnedPolicy(args.model, w / "models/showdown_initial_v1/catalog.json")
    records = []
    states = 0
    try:
        with ShowdownEnvironment(e) as env:
            for index in range(args.offset, args.offset + args.cases):
                if states >= args.states or budget.stopping():
                    break
                env.reset(
                    scenario("validation", index, version=args.curriculum_version)
                )
                rival = VisibleBaseline("tactical_heuristic", index + 919)
                seen = set()
                for step in range(96):
                    v = env.observation("self", include_history=True)
                    a = model.act(v)
                    category = action_class(v, a)
                    teacher = VisibleBaseline("tactical_heuristic", index).act(v)
                    tc = action_class(v, teacher)
                    interest = (
                        category
                        if category in {"recovery", "switch", "setup", "defense"}
                        else tc
                        if tc in {"recovery", "switch", "setup", "defense"}
                        else None
                    )
                    if (
                        v["request_state"] == "move"
                        and interest
                        and interest not in seen
                        and states < args.states
                    ):
                        choices = {
                            "selected": a,
                            "tactical": teacher,
                            "max_power": VisibleBaseline("max_power", index).act(v),
                        }
                        if len(set(choices.values())) > 1:
                            seen.add(interest)
                            cp = env.save()
                            digest = sha256(
                                json.dumps(cp, sort_keys=True).encode()
                            ).hexdigest()
                            state_id = states
                            states += 1
                            for label, first in choices.items():
                                env.restart(cp)
                                continuation = model
                                other = VisibleBaseline(
                                    "tactical_heuristic", index + 919
                                )
                                for j in range(256):
                                    b = env.observation("self", include_history=True)
                                    op = env.observation(
                                        "opponent", include_history=True
                                    )
                                    result = env.step(
                                        {
                                            "self": first
                                            if j == 0
                                            else continuation.act(b),
                                            "opponent": other.act(op),
                                        },
                                        revision=b["revision"],
                                    )
                                    if result["terminated"] or result["truncated"]:
                                        break
                                records.append(
                                    {
                                        "state": state_id,
                                        "case": index,
                                        "turn": v["turn"],
                                        "category": interest,
                                        "checkpoint_sha256": digest,
                                        "source_revision": v["revision"],
                                        "branch": label,
                                        "first_action": first,
                                        "first_class": action_class(v, first),
                                        "native_choice": v["choices"][first],
                                        "winner": result["winner"],
                                        "truncated": result["truncated"],
                                    }
                                )
                            env.restart(cp)
                            # Opponent continuation restarts from the same public history and fixed seed.
                            rival = VisibleBaseline("tactical_heuristic", index + 919)
                    result = env.step(
                        {
                            "self": a,
                            "opponent": rival.act(
                                env.observation("opponent", include_history=True)
                            ),
                        },
                        revision=env.observation("self")["revision"],
                    )
                    if result["terminated"] or result["truncated"]:
                        break
        atomic_json(
            out / "results.json",
            {
                "schema_version": "general-mc-conditional-audit-v1",
                "model_id": model.model_id,
                "native_execution_evidence_class": "exact_native_execution_specific_complete_hypothesis_choice_and_restored_rng",
                "aggregate_interpretation": "diagnostic_selected_validation_states_fixed_continuations_not_optimal_action_labels_or_exact_probabilities",
                "continuation": "selected_learned_model",
                "continuation_model_id": model.model_id,
                "curriculum_version": args.curriculum_version,
                "validation_offset": args.offset,
                "rival": "tactical_heuristic_fresh_rng_at_snapshot",
                "states": states,
                "records": records,
                "resources": job.usage(),
                "network": network,
            },
        )
        print(
            json.dumps(
                {
                    "states": states,
                    "battles": len(records),
                    "truncated": sum(r["truncated"] for r in records),
                }
            )
        )
    finally:
        budget.finished.set()


if __name__ == "__main__":
    main()
