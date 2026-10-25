"""Bounded TRAIN-only frozen-policy collection, exact native replay, then branches.

No learn(), train(), optimizer step, evaluation bank or model-save path exists.
An immutable external plan is required. Existing output refuses duplicate runs.
"""
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from advisor.learned_action_signals import branch_candidate, candidate_actions
from advisor.learned_decision_snapshots import (DecisionSnapshotRecorder, digest, outside_git,
                                               read_root, replay_original, write_new)
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
from advisor.learned_policy import LearnedPolicy
from advisor.learned_regularized_ppo import checkpoint_algorithm
from advisor.learned_tactical_diagnostics import action_class
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learning_resources import WindowsJob, RuntimeLimit, enforce_local_network_only


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def validate_plan(plan):
    if (plan.get("schema_version") != "foundation-decision-snapshot-pilot-v1"
            or type(plan.get("transitions")) is not int or not 128 <= plan["transitions"] <= 2048
            or plan["transitions"] % 128 or not 1 <= plan.get("snapshots", 0) <= 32
            or plan.get("workers") != 1 or plan.get("cpu_percent") != 50
            or plan.get("memory_mib") != 12288 or plan.get("device") != "cpu"
            or not 30 <= plan.get("max_seconds", 0) <= 900
            or type(plan.get("snapshot_every")) is not int or plan["snapshot_every"] < 32
            or plan.get("new_optimizer_updates") != 0
            or not 1 <= len(plan.get("future_seeds", [])) <= 4
            or len(set(map(tuple, plan["future_seeds"]))) != len(plan["future_seeds"])
            or plan["snapshots"] * (4 + 2 * len(plan["future_seeds"])) > 256):
        raise ValueError("bounded_frozen_snapshot_plan_required")
    if (not plan.get("input_hashes") or not plan.get("source_hashes")
            or plan.get("source_training_config") not in plan["input_hashes"]
            or plan.get("model") not in plan["input_hashes"]
            or plan["input_hashes"].get(plan["model"]) != plan.get("model_sha256")):
        raise ValueError("pilot_immutable_input_binding_required")
    for seed in plan["future_seeds"]:
        if len(seed) != 4 or any(type(v) is not int or not 0 <= v <= 65535 for v in seed):
            raise ValueError("invalid_future_seed")
    for p, expected in plan["input_hashes"].items():
        if file_hash(p) != expected:
            raise ValueError("pilot_input_hash_mismatch:" + p)
    root = Path(__file__).resolve().parents[1]
    for p, expected in plan["source_hashes"].items():
        if file_hash(root / p) != expected:
            raise ValueError("pilot_source_hash_mismatch:" + p)


class FrozenCaptureCallback(BaseCallback):
    def __init__(self, native_env, recorder, limit):
        super().__init__(); self.native_env, self.recorder, self.limit = native_env, recorder, limit
        self.steps = 0; self.rollout = -1; self.collection_seconds = 0.

    def _on_rollout_start(self):
        self.rollout += 1
        self.recorder.prepare(self.native_env, step=self.steps, rollout=self.rollout, t=0)

    def _on_step(self):
        if self.limit.stopping(): return False
        if self.locals["env"].num_envs != 1:
            raise ValueError("single_worker_snapshot_contract")
        self.recorder.selected(action=int(self.locals["actions"][0]),
            value=float(self.locals["values"][0].item()), logp=float(self.locals["log_probs"][0].item()),
            features=self.model._last_obs[0], mask=self.locals["action_masks"][0])
        self.steps += 1
        if self.locals["n_steps"] + 1 < self.model.n_steps:
            self.recorder.prepare(self.native_env, step=self.steps, rollout=self.rollout,
                                  t=self.locals["n_steps"] + 1)
        return True


def verify_GAE(model, output, rollout):
    """Independent check, not a replacement of SB3's actual GAE buffer."""
    b = model.rollout_buffer
    with torch.no_grad():
        last = model.policy.predict_values(torch.as_tensor(model._last_obs, device=model.device)).flatten().cpu().numpy()
    dones = model._last_episode_starts.copy()
    advantage = np.zeros_like(b.advantages); carry = np.zeros(1, dtype=np.float32)
    for t in reversed(range(model.n_steps)):
        next_value = last if t == model.n_steps - 1 else b.values[t + 1]
        nonterminal = 1 - (dones if t == model.n_steps - 1 else b.episode_starts[t + 1])
        carry = b.rewards[t] + model.gamma * next_value * nonterminal - b.values[t] + model.gamma * model.gae_lambda * nonterminal * carry
        advantage[t] = carry
    error = float(np.max(abs(advantage - b.advantages)))
    return_error = float(np.max(abs(b.returns - (b.advantages + b.values))))
    if error > 2e-6 or return_error > 2e-6:
        raise ValueError("pilot_GAE_reproduction_failed")
    arrays = {name: getattr(b, name).copy() for name in ("actions", "values", "log_probs", "rewards",
                "advantages", "returns", "episode_starts", "action_masks")}
    arrays.update(last_values=last, last_dones=dones)
    with (output / f"rollout_{rollout:03d}.npz").open("xb") as f:
        np.savez_compressed(f, **arrays)
    return {"rollout": rollout, "GAE_max_error": error, "return_max_error": return_error}


class NativeBudget:
    def __init__(self, output, maximum=256):
        self.output, self.maximum, self.count = output, maximum, 0

    def run(self, key, operation):
        path = self.output / (key + ".json")
        if path.exists(): raise ValueError("duplicate_native_unit")
        if self.count >= self.maximum: raise ValueError("native_continuation_cap")
        self.count += 1
        # A failure consumes its authorized execution slot; no automatic retry.
        with (self.output / "ledger.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"status": "started", "key": key, "ordinal": self.count}) + "\n")
            f.flush()
            import os
            os.fsync(f.fileno())
        result = operation()
        write_new(path, result)
        with (self.output / "ledger.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"status": "committed", "key": key, "sha256": file_hash(path)}) + "\n")
            f.flush(); os.fsync(f.fileno())
        return result


class FirstOpponentThenFoundation:
    def __init__(self, action, foundation): self.first, self.foundation = action, foundation
    def act(self, public):
        if self.first is not None:
            action, self.first = self.first, None
            if not public["action_mask"][action]: raise ValueError("recorded_opponent_choice_no_longer_legal")
            return action
        return self.foundation.act(public)


def native_comparisons(plan, output, recorder, foundation, cfg, limit, *,
                       original_replay_repetitions=2, native_maximum=256,
                       behavior_verifier=None, alternative_by_root=None):
    valid = [r for r in recorder.roots if r["native_terminal_recorded"]
             and r["trace"][-1]["result"]["terminated"] and not r["trace"][0]["result"]["action_rejected"]]
    if (original_replay_repetitions not in (1, 2) or not 1 <= native_maximum <= 256
            or len(valid) * (2 + original_replay_repetitions + 2 * len(plan["future_seeds"])) > native_maximum):
        raise ValueError("native_comparison_execution_contract")
    path = output / "native_units"; path.mkdir(); budget = NativeBudget(path, maximum=native_maximum)
    verified_public = output / "verified_public"; verified_public.mkdir()
    before = {"weights": tensor_digest(foundation.model.policy.state_dict()), "Adam": optimizer_digest(foundation.model.policy)}
    replay, pairs, duplicate = [], [], []
    with ShowdownEnvironment(cfg["checkout"], max_decisions=cfg["max_decisions"]) as native:
        # Restore the actual public projection, preserving its mapping order.
        # This also safely recovers earlier sorted JSON without changing inputs.
        for r in valid:
            cp = read_root(recorder.directory, r)
            def bind():
                native.restart(cp)
                public = native.observation("self", include_history=True)
                features = foundation.encoder.encode(public)
                if native.save() != cp or sha256(features.tobytes()).hexdigest() != r["observation_sha256"]:
                    raise ValueError("restored_root_encoded_observation_mismatch")
                with torch.no_grad():
                    if behavior_verifier is None:
                        value, logp, _ = foundation.model.policy.evaluate_actions(torch.as_tensor(features)[None],
                            torch.tensor([r["action"]]), action_masks=np.array([r["action_mask"]], bool))
                    else:
                        value, logp = behavior_verifier(public, r)
                lp_error, v_error = abs(float(logp.item())-r["old_logp"]), abs(float(value.item())-r["value"])
                if lp_error > 2e-5 or v_error > 2e-5:
                    raise ValueError("restored_root_logp_value_mismatch")
                write_new(verified_public / (r["id"] + ".json"), public)
                return {"checkpoint_equal": True, "encoded_SHA_equal": True,
                        "logp_error": lp_error, "value_error": v_error}
            budget.run(f"bind_{r['id']}", bind)
            public = json.loads((verified_public / (r["id"] + ".json")).read_text())
            for rep in range(original_replay_repetitions):
                replay.append(budget.run(f"replay_{r['id']}_{rep}",
                    lambda: replay_original(native, cp, r, public, stopping=limit.stopping)))
        write_new(output / "replay_gate_passed.json", {"roots": len(valid), "exact_suffix_replays": len(replay),
                    "native_steps_matched": sum(x["matched_native_steps"] for x in replay)})
        for r in valid:
            cp = read_root(recorder.directory, r)
            public = json.loads((verified_public / (r["id"] + ".json")).read_text())
            family = action_class(public, r["action"])
            if alternative_by_root is not None:
                alternative = alternative_by_root[r["id"]]
                if (type(alternative) is not int or alternative == r["action"]
                        or not 0 <= alternative < 35 or not public["action_mask"][alternative]):
                    raise ValueError("predeclared_alternative_not_legal")
            else:
                options = candidate_actions(public, limit=8)
                alternatives = [a for a in options if a != r["action"]]
                if not alternatives: continue
                alternative = min(alternatives, key=lambda a: (action_class(public, a) == family, options.index(a)))
            first_other = r["trace"][0]["actions"]["opponent"]
            def branch(action, seed):
                return branch_candidate(native, cp, public, side="self", action=action, future_seed=seed,
                    own_policy=foundation, opponent_policy=FirstOpponentThenFoundation(first_other, foundation),
                    stopping=limit.stopping)
            for i, seed in enumerate(plan["future_seeds"]):
                factual = budget.run(f"factual_{r['id']}_{i}", lambda: branch(r["action"], seed))
                counter = budget.run(f"alternative_{r['id']}_{i}", lambda: branch(alternative, seed))
                if i == 0:
                    repeated = budget.run(f"repeat_{r['id']}_{i}", lambda: branch(r["action"], seed))
                    if repeated != factual: raise ValueError("frozen_terminal_continuation_not_reproducible")
                    duplicate.append(r["id"])
                pairs.append({"root": r["id"], "seed_index": i, "sampled_action": r["action"],
                    "alternative_action": alternative, "family": family,
                    "alternative_family": action_class(public, alternative), "GAE": r["advantage"],
                    "original_native_horizon": len(r["trace"]), "factual": factual, "alternative": counter})
    after = {"weights": tensor_digest(foundation.model.policy.state_dict()), "Adam": optimizer_digest(foundation.model.policy)}
    if before != after: raise ValueError("frozen_continuation_model_or_Adam_changed")
    return {"status": "PILOT_READY" if len(valid) >= 4 and pairs else "PARTIAL_DATA_LIMITED",
        "terminal_replay_roots": len(valid), "exact_original_suffix_replays": len(replay),
        "repeat_terminal_checks": len(duplicate), "counterfactual_pairs": len(pairs),
        "native_continuations": budget.count, "reference_before": before, "reference_after": after,
        "pairs": pairs}


def resume_capture(plan, output, capture_path, *, resource_job):
    """Only retained completed GAE/native records; never collects new transitions."""
    validate_plan(plan)
    if plan.get("capture_existing") != str(Path(capture_path).resolve()):
        raise ValueError("explicit_immutable_capture_resume_binding_required")
    output = outside_git(output); output.mkdir(parents=True, exist_ok=True)
    write_new(output / "execution_started.json", {"plan_digest": digest(plan), "new_transitions": 0})
    limit = RuntimeLimit(output, plan["max_seconds"]); started = perf_counter()
    try:
        from types import SimpleNamespace
        capture = Path(capture_path); manifest = json.loads((capture / "capture_manifest.json").read_text())
        roots = manifest["roots"]
        if len(roots) > plan["snapshots"]: raise ValueError("existing_capture_budget_mismatch")
        count = 0; maximum_error = 0.
        for path in sorted(capture.parent.glob("rollout_*.npz")):
            with np.load(path, allow_pickle=False) as b:
                count += b["actions"].shape[0]
                carry = np.zeros(1, dtype=np.float32); a = np.zeros_like(b["advantages"])
                for t in reversed(range(len(a))):
                    nv = b["last_values"] if t == len(a)-1 else b["values"][t+1]
                    nn = 1-(b["last_dones"] if t == len(a)-1 else b["episode_starts"][t+1])
                    carry = b["rewards"][t]+nv*nn-b["values"][t]+.95*nn*carry; a[t] = carry
                maximum_error = max(maximum_error, float(abs(a-b["advantages"]).max()),
                                    float(abs(b["returns"]-b["advantages"]-b["values"]).max()))
        if count != plan["transitions"] or maximum_error > 2e-6:
            raise ValueError("existing_capture_GAE_or_count_mismatch")
        for r in roots:
            if r["policy_id"] != plan["model_sha256"]: raise ValueError("capture_policy_identity_mismatch")
            joined = json.loads((capture / "joins" / (r["id"] + ".json")).read_text())
            for k in ("action", "value", "old_logp", "advantage", "return_target", "observation_sha256"):
                if joined[k] != r[k]: raise ValueError("capture_scalar_link_mismatch")
            r["trace"] = [json.loads(line) for line in (capture / "private" / (r["id"]+".trace.jsonl")).read_text().splitlines()]
        cfg = json.loads(Path(plan["source_training_config"]).read_text())
        foundation = LearnedPolicy(plan["model"], cfg["catalog"], expected_model_id=plan["model_sha256"])
        foundation.model.policy.set_training_mode(False)
        result = native_comparisons(plan, output, SimpleNamespace(roots=roots, directory=capture), foundation, cfg, limit)
        result.update(transitions_reused=count, new_transitions=0, trained=0, optimizer_updates=0,
            GAE_max_error=maximum_error, snapshots=len(roots), checkpoint_and_trace_bytes=manifest["checkpoint_bytes"],
            instrumentation_seconds=manifest["instrumentation_seconds"], total_seconds=perf_counter()-started,
            resources=resource_job.usage(), new_evaluation_games=0)
        write_new(output / "pilot_results.json", result)
        return result
    finally: limit.finished.set()


def run(plan, output, *, resource_job):
    validate_plan(plan)
    output = outside_git(output); output.mkdir(parents=True, exist_ok=True)
    write_new(output / "execution_started.json", {"plan_digest": digest(plan), "new_training": 0,
               "warning": "existing starts are never automatically restarted"})
    limit = RuntimeLimit(output, plan["max_seconds"])
    started = perf_counter(); vector = None; budget = None
    try:
        cfg = json.loads(Path(plan["source_training_config"]).read_text(encoding="utf-8"))
        e = cfg["experiments"][0]
        foundation = LearnedPolicy(plan["model"], cfg["catalog"], expected_model_id=plan["model_sha256"])
        foundation.model.policy.set_training_mode(False)
        references = {"previous": (cfg["previous_model"], cfg["previous_model_id"]),
                      "historical": (e["historical_model"], e["historical_model_id"])}
        references.update({k: (v, e["frozen_opponent_ids"][k]) for k, v in e["frozen_opponents"].items()})
        factory = LearningEnvFactory(cfg["checkout"], cfg["catalog"], e["encoder_version"], 0,
            cfg["curriculum_version"], tuple(e["opponents"]), references, True,
            max_decisions=cfg["max_decisions"], terminal_transport_version=cfg["terminal_transport_version"],
            training_subset_path=cfg["training_subset"], training_subset_sha256=cfg["training_subset_sha256"],
            foundation_profile=True)
        env = factory(); vector = DummyVecEnv([lambda: env]); vector.seed(plan["seed"])
        model = checkpoint_algorithm(foundation.metadata).load(plan["model"], env=vector, device="cpu")
        if model.n_steps != 128 or model.gamma != 1 or model.gae_lambda != .95:
            raise ValueError("unexpected_frozen_PPO_contract")
        if tensor_digest(model.policy.state_dict()) != tensor_digest(foundation.model.policy.state_dict()):
            raise ValueError("frozen_initial_weight_mismatch")
        if optimizer_digest(model.policy) != optimizer_digest(foundation.model.policy):
            raise ValueError("frozen_initial_Adam_mismatch")
        before = {"policy": tensor_digest(model.policy.state_dict()), "Adam": optimizer_digest(model.policy)}
        def forbidden(*_, **__): raise AssertionError("pilot_forbids_learning_and_optimizer_updates")
        model.train = forbidden; model.policy.optimizer.step = forbidden
        recorder = DecisionSnapshotRecorder(output / "capture", policy_id=foundation.model_id,
            every=plan["snapshot_every"], max_snapshots=plan["snapshots"])
        env.decision_snapshot_recorder = recorder
        callback = FrozenCaptureCallback(env, recorder, limit)
        model.seed = plan["seed"]; model.set_random_seed(plan["seed"])
        _, callback = model._setup_learn(plan["transitions"], callback, reset_num_timesteps=False)
        callback.on_training_start({}, {})
        gae = []; start_collection = perf_counter()
        for rollout in range(plan["transitions"] // model.n_steps):
            if not model.collect_rollouts(vector, callback, model.rollout_buffer, model.n_steps):
                raise RuntimeError("incomplete_rollout_no_counterfactual_results")
            gae.append(verify_GAE(model, output, rollout)); recorder.join(model.rollout_buffer, rollout)
        collection_seconds = perf_counter() - start_collection
        callback.on_training_end(); recorder.finish()
        if callback.steps != plan["transitions"]: raise ValueError("collection_count_mismatch")
        after = {"policy": tensor_digest(model.policy.state_dict()), "Adam": optimizer_digest(model.policy)}
        if before != after: raise ValueError("frozen_model_or_Adam_changed")
        logp_errors, value_errors = [], []
        for r in recorder.roots:
            public = json.loads((recorder.directory / "public" / (r["id"] + ".json")).read_text())["observation"]
            with torch.no_grad():
                value, logp, _ = model.policy.evaluate_actions(
                    torch.as_tensor(model.policy.obs_to_tensor(env.encoder.encode(public))[0]),
                    torch.as_tensor([r["action"]]), action_masks=np.array([r["action_mask"]], dtype=bool))
            logp_errors.append(abs(float(logp.item()) - r["old_logp"]))
            value_errors.append(abs(float(value.item()) - r["value"]))
        if max(logp_errors, default=0.) > 2e-5 or max(value_errors, default=0.) > 2e-5:
            raise ValueError("frozen_public_policy_logp_value_reproduction_failed")
        episodes = env.drain_completed()
        write_new(output / "collection_complete.json", {"transitions": callback.steps, "trained": 0,
            "before": before, "after": after, "GAE_checks": gae, "episodes": episodes,
            "seconds": collection_seconds, "snapshots": len(recorder.roots), "resources": resource_job.usage(),
            "public_policy_logp_max_error": max(logp_errors, default=0.),
            "public_policy_value_max_error": max(value_errors, default=0.)})
        vector.close(); vector = None
        comparisons = native_comparisons(plan, output, recorder, foundation, cfg, limit)
        summary = {**comparisons,
            "transitions": callback.steps, "trained": 0, "optimizer_updates": 0,
            "snapshots": len(recorder.roots),
            "checkpoint_and_trace_bytes": recorder.bytes, "instrumentation_seconds": recorder.seconds,
            "collection_seconds": collection_seconds, "total_seconds": perf_counter() - started,
            "resources": resource_job.usage(), "new_evaluation_games": 0,
            "new_GAE_scope": "frozen_stochastic_T1_new_TRAIN_rollouts_not_historical_training",
            "continuation_scope": "first_recorded_opponent_action_fixed_then_both_public_Foundation_argmax",
            "interpretation": "conditional_simulator_true_state_pilot_not_optimal_labels_or_strength_test",
            }
        write_new(output / "pilot_results.json", summary)
        return summary
    finally:
        if vector is not None: vector.close()
        limit.finished.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-existing", type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8")); validate_plan(plan)
    torch.set_num_threads(1)
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=12)
    network = enforce_local_network_only()
    try:
        result = (resume_capture(plan, args.output, args.capture_existing, resource_job=job)
                  if args.capture_existing else run(plan, args.output, resource_job=job))
        print(json.dumps({k: v for k, v in result.items() if k != "pairs"}))
    except BaseException as error:
        output = outside_git(args.output)
        if output.exists() and not (output / "failure.json").exists():
            write_new(output / "failure.json", {"error": repr(error), "resources": job.usage(),
                "no_automatic_restart": True, "no_learning": True, "network": network})
        raise


if __name__ == "__main__": main()
