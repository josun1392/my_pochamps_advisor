"""Bounded generation chaining over the existing resource-controlled trainer.

Each generation is independently resumable. Frozen completed snapshots are
immutable; no worker hot swapping, privileged policy inputs or model promotion.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from time import time

from advisor.learned_snapshot_league import (
    checkpoint_identity, generation_mixture, validate_child, append_generation_event,
)
from advisor.learned_regularized_ppo import regularizer_contract
from advisor.learning_resources import atomic_json, WindowsJob
from scripts.train_showdown_autonomous import run, validate_config, training_config_fingerprint

VERSION = "showdown-matched-snapshot-continuation-study-v1"


def generation_config(plan, chain, generation, parent, completed):
    config = deepcopy(plan["base_config"])
    config["transition_budget_scope"] = "trained_rollouts_v1"
    experiment = config["experiments"][0]
    experiment.update(name=f"{chain}_g{generation}",
                      seed=plan["continuation_seeds"][chain.split("-")[1]] + 1000 * generation,
                      steps=plan["generation_transitions"], initial_model=parent["path"],
                      initial_model_id=parent["sha256"], fresh_optimizer=False,
                      zero_avoiding_beta=plan["beta"])
    if chain.startswith("L-"):
        mix = generation_mixture(plan["fixed_opponents"], [plan["B0"], *completed])
        experiment.update({k: mix[k] for k in ("opponents", "frozen_opponents", "frozen_opponent_ids")})
    else:
        experiment.update(opponents=plan["fixed_opponents"], frozen_opponents={}, frozen_opponent_ids={})
    validate_config(config)
    return config


def run_chain(plan_path, output, chain, *, resume=False, stop_at_first_checkpoint=False):
    raw = Path(plan_path).read_bytes()
    plan = json.loads(raw)
    if (plan.get("schema_version") != VERSION or chain not in {"F-s1", "F-s2", "L-s1", "L-s2"}
            or not 1 <= plan["generations"] <= 4 or not 1024 <= plan["generation_transitions"] <= 262144
            or plan["generation_transitions"] % 1024
            or set(plan["continuation_seeds"]) != {"s1", "s2"}):
        raise ValueError("invalid_bounded_league_plan")
    regularizer_contract(plan["beta"])
    b0 = checkpoint_identity(plan["B0"]["path"], plan["B0"]["sha256"])
    if b0 != plan["B0"]:
        raise ValueError("B0_manifest_changed")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / "chain_state.json"
    identity = sha256(raw).hexdigest()
    state = {"plan_sha256": identity, "chain": chain, "completed": []}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not resume or state["plan_sha256"] != identity or state["chain"] != chain:
            raise ValueError("league_resume_identity_mismatch")
    job = WindowsJob(memory_mib=plan["base_config"].get("memory_mib", 12288),
                     cpu_percent=plan["base_config"].get("cpu_percent", 50), active_process_limit=40)
    for generation in range(plan["generations"]):
        if generation < len(state["completed"]):
            saved = state["completed"][generation]
            if checkpoint_identity(saved["path"], saved["sha256"]) != saved:
                raise ValueError("completed_snapshot_changed")
            continue
        parent = state["completed"][-1] if state["completed"] else b0
        config = generation_config(plan, chain, generation, parent, state["completed"])
        generation_dir = output / f"generation_{generation:02d}"
        config_path = output / f"generation_{generation:02d}_config.json"
        if config_path.exists():
            if json.loads(config_path.read_text()) != config:
                raise ValueError("league_generation_config_changed")
        else:
            atomic_json(config_path, config)
        resumed = (generation_dir / "state.json").exists()
        if resumed and not resume:
            raise ValueError("existing_generation_requires_resume")
        append_generation_event(output / "generations.jsonl", {
            "event": "generation_resume" if resumed else "generation_start", "time_unix": time(),
            "generation": generation, "chain": chain, "parent": parent,
            "config_sha256": sha256(config_path.read_bytes()).hexdigest(),
            "config_fingerprint": training_config_fingerprint(config)[0],
            "opponents": config["experiments"][0]["opponents"],
            "snapshot_pool": config["experiments"][0]["frozen_opponent_ids"],
            "training_subset_sha256": config["training_subset_sha256"],
            "continuation_seed": config["experiments"][0]["seed"],
            "optimizer_scope": "compatible_Adam_restored_native_episodes_and_rollout_reset"})
        def event_callback(event):
            if stop_at_first_checkpoint and event.get("phase") == "evaluating" and event.get("transitions", 0) >= config["checkpoint_steps"]:
                (generation_dir / "STOP").write_text("intentional_checkpoint_boundary_smoke", encoding="utf-8")
        existing = json.loads((generation_dir / "state.json").read_text()) if resumed else None
        result = (existing if existing and existing["status"] == "complete"
                  else run(config, generation_dir, resume=resumed, resource_job=job,
                           event_callback=event_callback if stop_at_first_checkpoint else None))
        if result["status"] != "complete":
            state["status"] = result["status"]
            atomic_json(state_path, state)
            append_generation_event(output / "generations.jsonl", {
                "event": "generation_stopped", "time_unix": time(), "generation": generation,
                "collected_transitions": result["transitions"],
                "trained_transitions": result["trained_rollout_transitions"], "latest": result.get("latest")})
            return state
        if result["trained_rollout_transitions"] != plan["generation_transitions"]:
            raise ValueError("generation_trained_budget_mismatch_no_partial_rollout_promotion")
        endpoints = [e for e in result["evaluations"] if e["stage"] == "ppo"]
        child = checkpoint_identity(endpoints[-1]["checkpoint"])
        validate_child(parent, child, plan["generation_transitions"], result["transitions"])
        if child["training_regularizer"] != regularizer_contract(plan["beta"]):
            raise ValueError("generation_regularizer_missing")
        state["completed"].append(child)
        atomic_json(state_path, state)
        append_generation_event(output / "generations.jsonl", {
            "event": "generation_complete", "time_unix": time(), "generation": generation,
            "parent": parent, "child": child, "collected_transitions": result["transitions"],
            "trained_transitions": result["trained_rollout_transitions"],
            "ended_battles": result["completed_battles"], "outcomes": result.get("episode_outcomes"),
            "resources": result.get("resources"), "launches": result["launches"]})
    state["status"] = "complete"
    atomic_json(state_path, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chain", choices=["F-s1", "F-s2", "L-s1", "L-s2"], required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-at-first-checkpoint", action="store_true", help="native smoke only; does not alter policy/reward")
    args = parser.parse_args()
    state = run_chain(args.plan, args.output, args.chain, resume=args.resume,
                      stop_at_first_checkpoint=args.stop_at_first_checkpoint)
    print(json.dumps({"status": state["status"], "completed_generations": len(state["completed"])}))


if __name__ == "__main__":
    main()
