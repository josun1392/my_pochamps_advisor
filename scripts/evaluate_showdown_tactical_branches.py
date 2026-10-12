"""Small native first-action counterfactuals; sampled conditional outcomes only.

Fixed continuation/opponent heuristics do not prove optimal actions or exact
probabilities. Restore the same native checkpoint for each branch; never feed
it to either player's policy. This is diagnostic validation, not model selection.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
import json
from time import perf_counter
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario
from advisor.learned_tactical_curriculum import reset_learning_episode, VERSION
from advisor.learned_tactical_diagnostics import action_class
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learning_resources import (
    atomic_json,
    WindowsJob,
    RuntimeLimit,
    enforce_local_network_only,
)


def evaluate_branches(checkout, *, offset=18000, cycles=4, stopping=None):
    if not 1 <= cycles <= 16:
        raise ValueError("bounded_branch_cycles_required")
    records = []
    with ShowdownEnvironment(checkout, max_decisions=256) as env:
        for index in range(offset, offset + cycles * 24, 2):
            if stopping and stopping():
                raise TimeoutError("branch_budget_exhausted")
            start = reset_learning_episode(
                env, scenario("validation", index, version=VERSION)
            )
            view = env.observation("self", include_history=True)
            if view["request_state"] != "move":
                continue
            cp = env.save()
            # Prefer each reference policy's actual legal choice, then select the
            # first representative of remaining classes. Never maximize using RNG.
            representatives = {}
            for kind in ("tactical_heuristic", "heuristic", "max_power"):
                a = VisibleBaseline(kind, index).act(view)
                representatives.setdefault(action_class(view, a), a)
            for a, legal in enumerate(view["action_mask"]):
                if legal:
                    representatives.setdefault(action_class(view, a), a)
            for category, first in representatives.items():
                env.restart(cp)
                own = VisibleBaseline("champions_heuristic", index + 191)
                other = VisibleBaseline("tactical_heuristic", index + 919)
                steps = 0
                while True:
                    v = env.observation("self", include_history=True)
                    o = env.observation("opponent", include_history=True)
                    action = first if steps == 0 else own.act(v)
                    result = env.step(
                        {"self": action, "opponent": other.act(o)},
                        revision=v["revision"],
                    )
                    steps += 1
                    if result["terminated"] or result["truncated"]:
                        break
                records.append(
                    {
                        "case": index,
                        "motif": start["motif"],
                        "first_class": category,
                        "first_action": first,
                        "native_choice": view["choices"][first],
                        "winner": result["winner"],
                        "truncated": result["truncated"],
                        "decisions": steps,
                    }
                )
    summaries = []
    for motif in sorted({r["motif"] for r in records}):
        for category in sorted(
            {r["first_class"] for r in records if r["motif"] == motif}
        ):
            rows = [
                r
                for r in records
                if r["motif"] == motif and r["first_class"] == category
            ]
            summaries.append(
                {
                    "motif": motif,
                    "first_class": category,
                    "n": len(rows),
                    "outcomes": dict(
                        Counter(
                            "truncated" if r["truncated"] else r["winner"] or "draw"
                            for r in rows
                        )
                    ),
                }
            )
    return {
        "schema_version": "showdown-tactical-branches-v1",
        "interpretation": "sampled_conditional_first_action_outcomes_not_exact_or_optimal",
        "continuation": "champions_heuristic",
        "opponent": "tactical_heuristic",
        "offset": offset,
        "cycles": cycles,
        "summaries": summaries,
        "records": records,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cycles", type=int, default=4)
    p.add_argument("--offset", type=int, default=18000)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    budget = RuntimeLimit(args.output, 180)
    job = WindowsJob(memory_mib=1536, cpu_percent=12.5)
    network = enforce_local_network_only()
    started = perf_counter()
    try:
        result = evaluate_branches(
            args.checkout,
            offset=args.offset,
            cycles=args.cycles,
            stopping=budget.stopping,
        )
        atomic_json(args.output / "branches.json", result)
        atomic_json(
            args.output / "resources.json",
            {
                "wall_seconds": perf_counter() - started,
                "network": network,
                **job.usage(),
            },
        )
        print(
            json.dumps(
                {
                    "completed_battles": len(result["records"]),
                    "summaries": result["summaries"],
                }
            )
        )
    finally:
        budget.finished.set()


if __name__ == "__main__":
    main()
