"""Execute a frozen, bounded hypothetical action-signal plan; no PPO updates."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.learned_action_signals import (SCHEMA, public_identity,
    require_public_equivalence, candidate_actions, branch_candidate)
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_policy import LearnedPolicy
from advisor.learned_tactical_curriculum import reset_learning_episode
from advisor.learned_tactical_diagnostics import action_class
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only


def evaluate(plan, output, *, stopping=None):
    if (plan.get("schema_version") != SCHEMA or not 1 <= len(plan["states"]) <= 16
            or not 4 <= len(plan["future_seeds"]) <= 16
            or len({tuple(s) for s in plan["future_seeds"]}) != len(plan["future_seeds"])
            or not 1 <= len(plan["rivals"]) <= 3):
        raise ValueError("bounded_public_action_signal_plan_required")
    root = Path(__file__).resolve().parents[1]
    for name, expected in plan.get("source_hashes", {}).items():
        source = (root / name).resolve()
        if (not source.is_relative_to(root) or
                sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected):
            raise ValueError("action_signal_source_identity_mismatch")
    actor = LearnedPolicy(plan["actor"]["path"], plan["catalog"], expected_model_id=plan["actor"]["sha256"])
    actor.model.policy.set_training_mode(False)
    outputs, counts = [], {"branches": 0, "terminal": 0, "truncated": 0, "initial_rejected": 0}
    with ShowdownEnvironment(plan["checkout"], max_decisions=256) as env:
        for state in plan["states"]:
            path = output / (state["state_id"] + ".json")
            # Immutable complete-state outputs are resumable, no duplicate samples.
            if path.exists():
                saved = json.loads(path.read_text())
                if saved["state_plan"] != state: raise ValueError("resume_state_plan_mismatch")
                outputs.append(saved); continue
            checkpoints, reference, hypotheses = [], None, []
            if not 2 <= len(state["hypotheses"]) <= 4: raise ValueError("bounded_hypotheses_required")
            for hypothesis in state["hypotheses"]:
                reset_learning_episode(env, hypothesis["scenario"])
                view = env.observation(state["side"], include_history=True)
                if reference is None: reference = deepcopy(view)
                require_public_equivalence(reference, view)
                checkpoints.append(env.save())
                hypotheses.append({"id": hypothesis["id"], "public_identity": public_identity(view),
                                   "checkpoint_sha256": sha256(json.dumps(checkpoints[-1], sort_keys=True).encode()).hexdigest()})
            actions = candidate_actions(reference, limit=5)
            if len(actions) < 2: raise ValueError("insufficient_legal_action_comparison")
            rows = []
            for h, checkpoint in zip(state["hypotheses"], checkpoints):
                for rival in plan["rivals"]:
                    for seed_index, future_seed in enumerate(plan["future_seeds"]):
                        for action in actions:
                            row = branch_candidate(env, checkpoint, reference, side=state["side"], action=action,
                                future_seed=future_seed, own_policy=actor,
                                opponent_policy=VisibleBaseline(rival, 88000 + seed_index), stopping=stopping)
                            row.update(hypothesis=h["id"], rival=rival, sample=seed_index,
                                       future_seed=future_seed, action=action, category=action_class(reference, action))
                            rows.append(row)
            saved = {"schema_version": SCHEMA, "state_plan": state, "public_root": reference,
                     "hypotheses": hypotheses, "initial_inference": actor.infer(reference),
                     "actions": [{"index": a, "choice": reference["choices"][a], "category": action_class(reference, a)} for a in actions],
                     "records": rows}
            atomic_json(path, saved)
            outputs.append(saved)
            atomic_json(output / "progress.json", {"completed_states": [s["state_plan"]["state_id"] for s in outputs],
                                                       "persisted_branches": sum(len(s["records"]) for s in outputs)})
    for s in outputs:
        for r in s["records"]:
            counts["branches"] += 1
            counts["terminal"] += int(r.get("terminated", False))
            counts["truncated"] += int(r.get("truncated", False))
            counts["initial_rejected"] += int(r["status"] != "completed")
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-seconds", type=int, default=900)
    args = p.parse_args()
    if not 1 <= args.max_seconds <= 1800: p.error("bounded runtime required")
    args.output.mkdir(parents=True, exist_ok=True)
    plan_bytes = args.plan.read_bytes(); plan = json.loads(plan_bytes)
    identity = {"plan_sha256": sha256(plan_bytes).hexdigest()}
    manifest = args.output / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != identity: raise ValueError("resume_plan_mismatch")
    atomic_json(manifest, identity)
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=24)
    budget = RuntimeLimit(args.output, args.max_seconds)
    network = enforce_local_network_only(); start = perf_counter()
    try:
        result = evaluate(plan, args.output, stopping=budget.stopping)
        atomic_json(args.output / "completion.json", {**identity, **result, "elapsed_seconds": perf_counter()-start,
                                                     "resources": job.usage(), "network": network})
        print(json.dumps(result))
    finally:
        budget.finished.set()


if __name__ == "__main__": main()
