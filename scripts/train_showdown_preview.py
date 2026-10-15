"""Bounded local PREVIEW_V1 PPO launcher; battle V4 parameters remain frozen.

Example: python scripts/train_showdown_preview.py --config frozen.json --output OUT
Use OUT/STOP for a graceful rollout-boundary stop, then --resume CHECKPOINT.zip.
Checkpoints restore Adam, not native episodes or an interrupted rollout exactly.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from time import perf_counter
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv

from advisor.learned_encoder import fingerprint
from advisor.learned_preview import PreviewEncoder, VERSION, ACTION_VERSION
from advisor.learned_preview_policy import PreviewPolicy, LearnedPreviewPolicy
from advisor.learned_preview_env import PreviewLearningEnv
from advisor.learned_training_subset import NativeTrainingSubset
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID


def tensor_identity(state):
    result = {}
    for name, value in state.items():
        if isinstance(value, torch.Tensor):
            a = value.detach().cpu().contiguous()
            result[str(name)] = {"shape": list(a.shape), "dtype": str(a.dtype),
                "sha256": sha256(a.numpy().tobytes()).hexdigest()}
        elif isinstance(value, dict):
            result[str(name)] = tensor_identity(value)
        else:
            result[str(name)] = value
    return fingerprint(result)


def optimizer_identity(model):
    state = model.policy.optimizer.state_dict()
    steps = [int(v["step"]) for v in state["state"].values() if "step" in v]
    return {"state_sha256": tensor_identity(state["state"]), "parameters_with_state": len(steps),
            "steps_min": min(steps, default=0), "steps_max": max(steps, default=0)}


def save_preview_checkpoint(model, encoder, destination, config, **extra):
    path = Path(destination).with_suffix(".zip")
    if path.exists() or path.with_suffix(".json").exists():
        raise ValueError("preview_checkpoint_overwrite_forbidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    model.save(path)
    identity = sha256(path.read_bytes()).hexdigest()
    meta = {"schema_version": "showdown-preview-model-v1", "encoder_version": VERSION,
        "feature_fingerprint": encoder.fingerprint, "feature_contract": encoder.feature_contract,
        "action_schema_version": ACTION_VERSION, "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
        "model_sha256": identity, "model_parameter_sha256": tensor_identity(model.policy.state_dict()),
        "gamma": model.gamma, "gae_lambda": model.gae_lambda,
        "objective": "native_terminal_win_loss_draw_preview_bandit_v1",
        "value_scope": "learned_return_not_exact_win_probability", "optimizer": optimizer_identity(model),
        "trained_preview_episodes": model.num_timesteps, "config_sha256": fingerprint(config),
        "frozen_battle_sha256": config["battle_model_sha256"],
        "resume_scope": "Adam_and_policy_restored_fresh_native_episodes_not_bit_exact_rollout_replay", **extra}
    atomic_json(path.with_suffix(".json"), meta)
    return {"path": str(path), "sha256": identity, **meta}


def validate(config):
    for key in ("checkout", "catalog", "battle_model", "subset"):
        if not isinstance(config.get(key), str) or not Path(config[key]).exists():
            raise ValueError("missing_preview_runtime_path_" + key)
    if (config.get("schema_version") != "showdown-preview-training-v1"
            or config.get("engine_commit") != SHOWDOWN_COMMIT or config.get("format_id") != FORMAT_ID
            or config.get("opponents") != ["tactical_heuristic", "champions_heuristic"]
            or type(config.get("seed")) is not int or not 1 <= config["seed"] <= 1000000
            or type(config.get("workers")) is not int or not 1 <= config["workers"] <= 8
            or not 1 <= config.get("cpu_percent", 0) <= 50
            or not 1024 <= config.get("memory_mib", 0) <= 12288
            or not 60 <= config.get("runtime_seconds", 0) <= 5400
            or type(config.get("episodes")) is not int or not 8 <= config["episodes"] <= 65536
            or config["episodes"] % (128 * config["workers"])):
        raise ValueError("invalid_or_unbounded_preview_training")
    if sha256(Path(config["battle_model"]).read_bytes()).hexdigest() != config["battle_model_sha256"]:
        raise ValueError("frozen_battle_model_hash_mismatch")
    encoder = PreviewEncoder(config["catalog"])
    if config["feature_fingerprint"] != encoder.fingerprint:
        raise ValueError("preview_feature_contract_mismatch")
    for name, identity in config["source_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != identity:
            raise ValueError("preview_frozen_source_mismatch")
    NativeTrainingSubset(config["subset"], config["subset_sha256"])
    from advisor.showdown_bridge import ShowdownBridge
    ShowdownBridge(config["checkout"])._verify_checkout()
    return encoder


class EnvFactory:
    def __init__(self, config, rank, start_episode):
        self.config, self.rank, self.start = config, rank, start_episode

    def __call__(self):
        enforce_local_network_only()
        c = self.config
        provider = NativeTrainingSubset(c["subset"], c["subset_sha256"])
        return PreviewLearningEnv(c["checkout"], c["catalog"], c["battle_model"], c["battle_model_sha256"], provider,
            index_offset=self.start + self.rank, stride=c["workers"], opponents=c["opponents"])


class Records(BaseCallback):
    def __init__(self, output):
        super().__init__()
        self.output, self.counts, self.actions, self.native = Path(output), Counter(), Counter(), Counter()
        self.episodes = 0

    def _on_step(self):
        with (self.output / "episodes.jsonl").open("a", encoding="utf-8") as f:
            for info in self.locals["infos"]:
                row = info.get("preview_episode")
                if row:
                    self.episodes += 1
                    self.counts[f'{row["opponent"]}:{row["outcome"]}'] += 1
                    self.actions[str(row["preview_action"])] += 1
                    self.native["decisions"] += row["native_decisions"]
                    self.native["rejections"] += row["native_rejections"]
                    f.write(json.dumps(row, separators=(",", ":")) + "\n")
        return True


def run(config, output, *, resume=None, stop_after_rollouts=None):
    output = Path(output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("preview_training_artifacts_must_be_outside_repository")
    output.mkdir(parents=True, exist_ok=True)
    encoder = validate(config)
    previous = output / "config.json"
    if previous.exists() and json.loads(previous.read_text()) != config:
        raise ValueError("preview_run_configuration_changed")
    if not resume and (output / "initial.zip").exists():
        raise ValueError("existing_preview_run_requires_explicit_resume")
    if (output / "STOP").exists():
        raise ValueError("acknowledge_previous_STOP_before_explicit_resume")
    atomic_json(previous, config)
    job = WindowsJob(memory_mib=config["memory_mib"], cpu_percent=config["cpu_percent"], active_process_limit=40)
    limit = RuntimeLimit(output, config["runtime_seconds"])
    enforce_local_network_only()
    torch.set_num_threads(1)
    start = perf_counter()
    model, env = None, None
    try:
        if resume:
            loaded = LearnedPreviewPolicy(resume, config["catalog"])
            if loaded.metadata["config_sha256"] != fingerprint(config):
                raise ValueError("incompatible_preview_resume_configuration")
            model = loaded.model
            if optimizer_identity(model) != loaded.metadata["optimizer"]:
                raise ValueError("preview_optimizer_restoration_mismatch")
        start_episode = model.num_timesteps if model is not None else 0
        env = SubprocVecEnv([EnvFactory(config, rank, start_episode) for rank in range(config["workers"])], start_method="spawn")
        if model is None:
            model = MaskablePPO(PreviewPolicy, env, seed=config["seed"], device="cpu", gamma=1., gae_lambda=.95,
                learning_rate=1e-4, ent_coef=.005, n_steps=128, batch_size=128, n_epochs=4, target_kl=.03)
            initial = save_preview_checkpoint(model, encoder, output / "initial", config)
        else:
            model.set_env(env)
            # Explicit fresh native case namespace after durable restart. Preserve Adam.
            env.seed(config["seed"])
            initial = {"path": str(resume), "sha256": sha256(Path(resume).read_bytes()).hexdigest()}
        parent = initial
        callback = Records(output)
        progress = {"trained_preview_episodes": start_episode, "checkpoint": parent,
            "elapsed_seconds": perf_counter() - start, "launch_completed_battles": 0,
            "collected_preview_episodes": start_episode, "resources": job.usage()}
        rollouts = 0
        rollout_size = model.n_steps * config["workers"]
        with (output / "learning.jsonl").open("a", encoding="utf-8") as learning:
            while model.num_timesteps < config["episodes"] and not limit.stopping():
                before = model.num_timesteps
                model.learn(rollout_size, reset_num_timesteps=False, callback=callback, progress_bar=False)
                rollouts += 1
                metrics = {k: float(v) for k, v in model.logger.name_to_value.items()
                           if isinstance(v, (int, float, np.number))}
                if not all(np.isfinite(v) for v in metrics.values()) or any(not torch.isfinite(p).all() for p in model.policy.parameters()):
                    raise ValueError("nonfinite_preview_learning")
                checkpoint = save_preview_checkpoint(model, encoder, output / f"checkpoint_{model.num_timesteps:08d}", config,
                    parent_checkpoint=parent, ppo_metrics=metrics)
                parent = {"path": checkpoint["path"], "sha256": checkpoint["sha256"]}
                progress = {"status": "running", "trained_preview_episodes": model.num_timesteps,
                    "collected_preview_episodes": model.num_timesteps, "launch_start_episodes": start_episode,
                    "launch_completed_battles": callback.episodes, "elapsed_seconds": perf_counter() - start,
                    "episodes_per_second": (model.num_timesteps - start_episode) / (perf_counter() - start),
                    "outcomes": dict(callback.counts), "actions": dict(callback.actions),
                    "native": dict(callback.native), "checkpoint": parent, "metrics": metrics,
                    "resources": job.usage(), "optimizer": optimizer_identity(model)}
                learning.write(json.dumps(progress, allow_nan=False) + "\n"); learning.flush()
                atomic_json(output / "progress.json", progress)
                if stop_after_rollouts and rollouts >= stop_after_rollouts:
                    (output / "STOP").write_text("intentional durable stop/resume test", encoding="utf-8")
            complete = model.num_timesteps == config["episodes"]
            progress.update(status="completed" if complete else "stopped", stop_resume_requested=not complete,
                battle_model_sha256_after=sha256(Path(config["battle_model"]).read_bytes()).hexdigest())
            if progress["battle_model_sha256_after"] != config["battle_model_sha256"]:
                raise ValueError("frozen_battle_model_mutated")
            atomic_json(output / "completion.json", progress)
            return progress
    except BaseException as error:
        atomic_json(output / "failure.json", {"exception": type(error).__name__, "reason": str(error),
            "durable_steps": model.num_timesteps if model else 0, "resources": job.usage()})
        raise
    finally:
        if env is not None:
            env.close()
        limit.finished.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume")
    parser.add_argument("--stop-after-rollouts", type=int)
    args = parser.parse_args()
    result = run(json.loads(Path(args.config).read_text(encoding="utf-8")), args.output,
                 resume=args.resume, stop_after_rollouts=args.stop_after_rollouts)
    print(json.dumps({k: result[k] for k in ("status", "trained_preview_episodes", "elapsed_seconds")}))
