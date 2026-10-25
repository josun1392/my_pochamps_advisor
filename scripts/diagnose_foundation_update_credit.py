"""One bounded standard Foundation PPO copy; no evaluation or model promotion."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from stable_baselines3.common.vec_env import DummyVecEnv

from advisor.learned_decision_snapshots import (DecisionSnapshotRecorder, PPO_GAE_SCOPE,
                                               outside_git, write_new)
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_policy import LearnedPolicy
from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatPolicy
from advisor.learned_parent_anchor import optimizer_clock, optimizer_digest, tensor_digest
from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
from advisor.learned_training_operations import ProgressRetryMonitor
from advisor.learned_update_credit import UpdateCreditObserver, UpdateCreditCallback, score_public
from advisor.learning_resources import WindowsJob, RuntimeLimit, enforce_local_network_only, atomic_json
from scripts.pilot_foundation_decision_snapshots import native_comparisons
from scripts.train_showdown_autonomous import save_checkpoint


def file_hash(path): return sha256(Path(path).read_bytes()).hexdigest()


def validate_plan(plan):
    if (plan.get("schema_version") != "foundation-PPO-update-credit-diagnostic-v1"
            or type(plan.get("transitions")) is not int or not 512 <= plan["transitions"] <= 16384
            or plan["transitions"] % 512 or plan.get("snapshots") != plan["transitions"] // 512
            or plan.get("seed") != 117021 or plan.get("envs") != 4
            or plan.get("cpu_percent") != 50 or plan.get("memory_mib") != 12288 or plan.get("device") != "cpu"
            or not 60 <= plan.get("max_seconds", 0) <= 1800 or plan.get("native_budget") != 240
            or len(plan.get("future_seeds", [])) != 2 or plan["snapshots"] * 7 > plan["native_budget"]
            or plan.get("evaluation_games") != 0):
        raise ValueError("bounded_standard_PPO_credit_plan_required")
    for seed in plan["future_seeds"]:
        if len(seed) != 4 or any(type(v) is not int or not 0 <= v <= 65535 for v in seed): raise ValueError("invalid_future_seed")
    if len(set(map(tuple, plan["future_seeds"]))) != 2: raise ValueError("duplicate_future_seed")
    if (plan.get("model") not in plan.get("input_hashes", {})
            or plan["input_hashes"][plan["model"]] != plan.get("model_sha256")
            or plan.get("source_config") not in plan["input_hashes"] or not plan.get("source_hashes")):
        raise ValueError("credit_input_binding_required")
    root = Path(__file__).resolve().parents[1]
    for p, expected in plan["input_hashes"].items():
        if file_hash(p) != expected: raise ValueError("credit_input_hash:" + p)
    for p, expected in plan["source_hashes"].items():
        if file_hash(root / p) != expected: raise ValueError("credit_source_hash:" + p)


def verify_hyperparameters(model, plan):
    if type(model) is not FoundationCombatPPO or type(model.policy) is not FoundationCombatPolicy:
        raise ValueError("standard_original_Foundation_required")
    for k, expected in plan["PPO_hyperparameters"].items():
        if getattr(model, k) != expected: raise ValueError("credit_changed_PPO_hyperparameter:" + k)
    if any(getattr(model, k, None) is not None for k in ("masked_temperature", "parent_policy_anchor")):
        raise ValueError("credit_forbids_temperature_and_parent_KL")
    if optimizer_clock(model.policy) != plan["parent_Adam"]: raise ValueError("credit_Adam_restore_mismatch")
    if any(abs(model.clip_range(v)-.2) > 1e-12 or abs(model.lr_schedule(v)-5e-5) > 1e-12 for v in (0., 1.)):
        raise ValueError("credit_original_constant_schedules_required")


def run(plan, output, job):
    validate_plan(plan); output = outside_git(output); output.mkdir(parents=True, exist_ok=True)
    write_new(output / "started.json", {"PID": os.getpid(), "plan_SHA256": file_hash(plan["plan_file"]),
        "transitions_cap": plan["transitions"], "automatic_restart": False})
    limit = RuntimeLimit(output, plan["max_seconds"]); started = perf_counter()
    vector = None; audit = None; observer = None; callback = None; model = None
    checkpoint_paths = []
    try:
        cfg = json.loads(Path(plan["source_config"]).read_text(encoding="utf-8")); exp = cfg["experiments"][0]
        parent = LearnedPolicy(plan["model"], cfg["catalog"], expected_model_id=plan["model_sha256"])
        learner = LearnedPolicy(plan["model"], cfg["catalog"], expected_model_id=plan["model_sha256"])
        model = learner.model; verify_hyperparameters(model, plan)
        initial = {"parameters": tensor_digest(model.policy.state_dict()), "Adam": optimizer_digest(model.policy),
                   "Adam_clock": optimizer_clock(model.policy), "model_timesteps": model.num_timesteps}
        if initial["parameters"] != tensor_digest(parent.model.policy.state_dict()) or initial["Adam"] != optimizer_digest(parent.model.policy):
            raise ValueError("credit_parent_copy_initial_mismatch")
        write_new(output / "initial_identity.json", initial)
        references = {"previous": (cfg["previous_model"], cfg["previous_model_id"]),
                      "historical": (exp["historical_model"], exp["historical_model_id"])}
        references.update({k: (p, exp["frozen_opponent_ids"][k]) for k,p in exp["frozen_opponents"].items()})
        factories = [LearningEnvFactory(cfg["checkout"], cfg["catalog"], exp["encoder_version"], i*100000,
            cfg["curriculum_version"], tuple(exp["opponents"]), references, True,
            max_decisions=cfg["max_decisions"], terminal_transport_version=cfg["terminal_transport_version"],
            training_subset_path=cfg["training_subset"], training_subset_sha256=cfg["training_subset_sha256"],
            foundation_profile=True) for i in range(4)]
        vector = DummyVecEnv(factories); env0 = vector.envs[0]
        snapshots = DecisionSnapshotRecorder(output / "snapshots", policy_id=parent.model_id,
            every=128, max_snapshots=plan["snapshots"], gae_scope=PPO_GAE_SCOPE)
        env0.decision_snapshot_recorder = snapshots
        observer = UpdateCreditObserver(output / "update_credit", learner.encoder, snapshots, parent.model_id)
        audit = AuditedSignalRecorder(output / "PPO_audits", learner.encoder)
        model.set_env(vector); model.seed = plan["seed"]; model.set_random_seed(plan["seed"])
        save_meta = {"curriculum_version": cfg["curriculum_version"], "source_model_SHA256": parent.model_id,
            "diagnostic_only_no_promotion": True, "update_credit_plan_SHA256": file_hash(plan["plan_file"])}
        checkpoint_paths.append(save_checkpoint(model, learner.encoder, output / "checkpoints/initial", save_meta))
        retry_monitor = ProgressRetryMonitor(); all_episodes, all_retries = [], []
        class Callback(UpdateCreditCallback):
            def _on_step(self):
                result = super()._on_step()
                records = [r for env in vector.envs for r in env.drain_retry_diagnostics()]
                ended = [e for env in vector.envs for e in env.drain_completed()]
                all_episodes.extend(ended); all_retries.extend(records)
                alerts = retry_monitor.inspect(records, ended, plan["transitions"],
                    progress=[env.episode_cursor() for env in vector.envs])
                if records or alerts:
                    with (output / "retry_monitor.jsonl").open("a", encoding="utf-8") as f:
                        f.write(json.dumps({"collected": self.steps, "records": records,
                            "alerts": alerts, "statistics": retry_monitor.statistics()}) + "\n")
                        f.flush(); os.fsync(f.fileno())
                if alerts: raise ValueError("credit_native_progress_monitor:" + repr(alerts))
                return result

            def _on_rollout_start(self):
                super()._on_rollout_start()
                if self.steps == 8192:
                    checkpoint_paths.append(save_checkpoint(self.model, learner.encoder,
                        output / "checkpoints/trained_8192", {**save_meta, "trained_since_parent": self.steps}))
                atomic_json(output / "progress.json", {"PID": os.getpid(), "phase": "standard_PPO_training",
                    "collected": self.steps, "trained": self.completed_rollouts.transitions,
                    "Adam_clock": optimizer_clock(self.model.policy), "snapshot_count": len(snapshots.roots),
                    "elapsed_seconds": perf_counter()-started, "resources": job.usage()})
        callback = Callback(limit, env0, observer, signal_recorder=audit, transition_cap=plan["transitions"])
        train_start = perf_counter()
        model.learn(total_timesteps=plan["transitions"], reset_num_timesteps=False, callback=callback, log_interval=None)
        train_seconds = perf_counter()-train_start
        if callback.steps != plan["transitions"] or callback.completed_rollouts.transitions != plan["transitions"]:
            raise ValueError("credit_partial_collection_or_training_no_counterfactuals")
        snapshots.finish()
        checkpoint_paths.append(save_checkpoint(model, learner.encoder, output / "checkpoints/final", {
            **save_meta, "trained_since_parent": callback.completed_rollouts.transitions}))
        episodes = all_episodes + [e for env in vector.envs for e in env.drain_completed()]
        if len(all_retries) > .01 * callback.steps: raise ValueError("credit_interval_retry_rate_above_one_percent")
        profiles = [env.drain_foundation_profile() for env in vector.envs]
        write_new(output / "training_complete.json", {"collected": callback.steps,
            "trained": callback.completed_rollouts.transitions, "initial": initial,
            "final_parameters": tensor_digest(model.policy.state_dict()), "final_Adam": optimizer_digest(model.policy),
            "final_Adam_clock": optimizer_clock(model.policy), "train_seconds": train_seconds,
            "checkpoints": [{"path": p, "SHA256": file_hash(p)} for p in checkpoint_paths],
            "episodes": episodes, "retry_records": all_retries,
            "retry_monitor_statistics": retry_monitor.statistics(), "profiles": profiles, "resources": job.usage()})
        for p in checkpoint_paths:
            check = LearnedPolicy(p, cfg["catalog"], expected_model_id=file_hash(p))
            if check.model.gamma != 1 or check.model.gae_lambda != .95: raise ValueError("credit_checkpoint_objective_changed")
            if p == checkpoint_paths[-1] and (optimizer_digest(check.model.policy) != optimizer_digest(model.policy)
                    or tensor_digest(check.model.policy.state_dict()) != tensor_digest(model.policy.state_dict())):
                raise ValueError("credit_checkpoint_Adam_or_weights_reload_mismatch")
        write_new(output / "checkpoint_reload_passed.json", {"checkpoints": len(checkpoint_paths), "final_exact_Adam_weights": True})
        vector.close(); vector = None
        verifier = deepcopy(parent.model.policy); verifier.set_training_mode(False)
        # Independent deterministic replay of both recorded score boundaries.
        score_checks = []
        for r in snapshots.roots:
            credit = json.loads((observer.directory / "credits" / (r["id"]+".json")).read_text())
            public = json.loads((snapshots.directory / "public" / (r["id"]+".json")).read_text())["observation"]
            features = parent.encoder.encode(public)
            if sha256(features.tobytes()).hexdigest() != r["observation_sha256"]: raise ValueError("credit_reprobe_public_SHA")
            for which, offset in (("pre", 0), ("post", 1)):
                update = r["behavior_update"] + offset
                if update <= callback.rollout:
                    state = torch.load(observer.directory / "policies" / f"update_{update:03d}_before.pt", map_location="cpu", weights_only=True)
                else: state = model.policy.state_dict()
                expected = credit["policy_before_SHA256" if which == "pre" else "policy_after_SHA256"]
                if tensor_digest(state) != expected: raise ValueError("credit_update_parameter_lineage")
                verifier.load_state_dict(state, strict=True)
                scores = score_public(verifier, features, r["action_mask"])
                error = max(float(abs(np.asarray(scores[k])-credit[which][k]).max())
                            for k in ("raw_logits", "probabilities", "log_probabilities", "value"))
                if error > 2e-5: raise ValueError("credit_score_reinference_failed")
                score_checks.append({"root": r["id"], "boundary": which, "max_error": error, "parameters_SHA256": expected})
        write_new(output / "pre_post_reinference.json", {"checks": score_checks,
            "max_error": max((c["max_error"] for c in score_checks), default=0.)})
        loaded = None
        def verify_behavior(public, r):
            nonlocal loaded
            if loaded != r["policy_id"]:
                if file_hash(r["policy_state_file"]) != r["policy_state_file_SHA256"]: raise ValueError("credit_behavior_state_corrupt")
                state = torch.load(r["policy_state_file"], map_location="cpu", weights_only=True)
                if tensor_digest(state) != r["policy_id"]: raise ValueError("credit_behavior_identity")
                verifier.load_state_dict(state, strict=True); loaded = r["policy_id"]
            features = parent.encoder.encode(public)
            pre = score_public(verifier, features, r["action_mask"])
            if max(abs(np.array(pre["raw_logits"])-r["pre_update_scores"]["raw_logits"])) > 2e-5:
                raise ValueError("credit_behavior_prelogits_replay_mismatch")
            return torch.tensor([pre["value"]]), torch.tensor([pre["log_probabilities"][r["action"]]])
        atomic_json(output / "progress.json", {"PID": os.getpid(), "phase": "native_replay_gate_then_counterfactuals",
            "trained": callback.steps, "collected": callback.steps, "resources": job.usage()})
        native = native_comparisons(plan, output, snapshots, parent, cfg, limit,
            original_replay_repetitions=1, native_maximum=plan["native_budget"], behavior_verifier=verify_behavior,
            alternative_by_root={r["id"]: r["alternative_action"] for r in snapshots.roots})
        summary = {**native, "trained": callback.steps, "collected": callback.steps,
            "PPO_update_calls": callback.rollout+1, "optimizer_updates": optimizer_clock(model.policy)-initial["Adam_clock"],
            "snapshot_count": len(snapshots.roots), "train_seconds": train_seconds,
            "total_seconds": perf_counter()-started, "resources": job.usage(),
            "new_evaluation_games": 0, "model_promotion": False}
        credits = [json.loads(p.read_text()) for p in (observer.directory / "credits").glob("*.json")]
        changed = sum(abs(c["selected_logp_delta"]) > 1e-6 for c in credits)
        roots = {r["id"]: r for r in snapshots.roots}
        informative_episodes = {roots[p["root"]]["episode_id"] for p in native["pairs"]
            if p["factual"]["terminal_return"] is not None and p["alternative"]["terminal_return"] is not None
            and p["factual"]["terminal_return"] != p["alternative"]["terminal_return"]}
        summary.update(native_contract_status=native["status"], nontrivial_policy_shift_roots=changed,
            informative_terminal_episodes=len(informative_episodes),
            status="UPDATE_SIGNAL_LINKAGE_READY" if changed >= 8 and len(informative_episodes) >= 4 else "PARTIAL_UNDERPOWERED")
        write_new(output / "execution_complete.json", summary)
        atomic_json(output / "progress.json", {"PID": os.getpid(), "phase": "execution_complete",
                    "trained": callback.steps, "native_units": native["native_continuations"], "resources": job.usage()})
        return summary
    except BaseException as error:
        if audit is not None: audit.close()
        if observer is not None: observer.cleanup()
        write_new(output / "failure.json", {"error": repr(error), "no_automatic_restart": True,
            "collected": getattr(callback, "steps", 0),
            "trained": getattr(getattr(callback, "completed_rollouts", None), "transitions", 0),
            "Adam_clock": optimizer_clock(model.policy) if model is not None else None,
            "resources": job.usage()})
        raise
    finally:
        if vector is not None: vector.close()
        limit.finished.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); plan = json.loads(args.plan.read_text(encoding="utf-8")); plan["plan_file"] = str(args.plan)
    validate_plan(plan); torch.set_num_threads(1)
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=12); enforce_local_network_only()
    summary = run(plan, args.output, job)
    print(json.dumps({k:v for k,v in summary.items() if k != "pairs"}))


if __name__ == "__main__": main()
