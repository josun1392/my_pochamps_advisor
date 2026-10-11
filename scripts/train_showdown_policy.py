"""Bounded CPU MaskablePPO training, real native episodes and versioned artifacts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from hashlib import sha256
import importlib.metadata
import json
import math
from time import perf_counter
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv
from advisor.learned_encoder import PartialObservationEncoder, ENCODER_VERSION
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID


def train(checkout, catalog, output, *, steps=2048, seed=17, envs=4, resume=None):
    if not 1 <= envs <= 8 or not 256 <= steps <= 65536 or steps % (128 * envs):
        raise ValueError("bounded_steps_must_be_divisible_by_rollout_size")
    output = Path(output)
    if output.with_suffix(".zip").exists() or output.with_suffix(".json").exists():
        raise ValueError("new_model_output_required")
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    encoder = PartialObservationEncoder(catalog)
    instances = []
    try:
        for i in range(envs):
            instances.append(
                ShowdownLearningEnv(checkout, encoder, index_offset=i * 100000)
            )
        vector = DummyVecEnv([lambda env=env: env for env in instances])
    except BaseException:
        for env in instances:
            env.close()
        raise
    started = perf_counter()
    try:
        kwargs = dict(
            n_steps=128,
            batch_size=128,
            n_epochs=4,
            gamma=0.99,
            ent_coef=0.02,
            learning_rate=3e-4,
            target_kl=0.03,
            seed=seed,
            device="cpu",
            policy_kwargs={"net_arch": {"pi": [64, 64], "vf": [64, 64]}},
            verbose=0,
        )
        source = LearnedPolicy(resume, catalog) if resume else None
        model = source.model if source else MaskablePPO("MlpPolicy", vector, **kwargs)
        if source:
            model.set_env(vector)
        before = torch.cat(
            [p.detach().flatten() for p in model.policy.parameters()]
        ).clone()
        prior_steps, prior_updates = model.num_timesteps, model._n_updates
        prior_optimizer_steps = max(
            (
                int(s["step"])
                for s in model.policy.optimizer.state.values()
                if "step" in s
            ),
            default=0,
        )
        vector.seed(seed + prior_steps)
        model.save(str(output) + "-before")
        model.learn(total_timesteps=steps, reset_num_timesteps=not bool(resume))
        after = torch.cat([p.detach().flatten() for p in model.policy.parameters()])
        delta = float((after - before).abs().sum())
        if delta <= 0 or not torch.isfinite(after).all():
            raise AssertionError("learning_did_not_update_finite_parameters")
        model.save(output)
        completed = [row for env in vector.envs for row in env.completed]
        metrics = {
            key: float(value) if math.isfinite(value) else None
            for key, value in model.logger.name_to_value.items()
            if key.startswith("train/") and isinstance(value, (float, int))
        }
        metadata = {
            "schema_version": "showdown-learned-model-v1",
            "evidence_class": "learned_policy_value",
            "interpretation": "experimental_policy_distribution_and_discounted_return_not_exact_win_probability",
            "encoder_version": ENCODER_VERSION,
            "catalog_fingerprint": encoder.catalog_fingerprint,
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
            "action_schema_version": "showdown-policy-actions-v1",
            "algorithm": "sb3-contrib-MaskablePPO",
            "architecture": {"policy": [64, 64], "value": [64, 64]},
            "versions": {
                p: importlib.metadata.version(p)
                for p in (
                    "torch",
                    "sb3-contrib",
                    "stable-baselines3",
                    "gymnasium",
                    "poke-env",
                    "numpy",
                )
            },
            "seed": seed,
            "device": "cpu",
            "torch_threads": 1,
            "envs": envs,
            "steps_this_run": model.num_timesteps - prior_steps,
            "total_steps": model.num_timesteps,
            "ppo_update_epochs_this_run": model._n_updates - prior_updates,
            "optimizer_steps_this_run": max(
                (
                    int(s["step"])
                    for s in model.policy.optimizer.state.values()
                    if "step" in s
                ),
                default=0,
            )
            - prior_optimizer_steps,
            "parameter_l1_change": delta,
            "parameter_count": sum(p.numel() for p in model.policy.parameters()),
            "observation_dim": int(model.observation_space.shape[0]),
            "model_sha256": sha256(output.with_suffix(".zip").read_bytes()).hexdigest(),
            "training_seconds": perf_counter() - started,
            "gamma": model.gamma,
            "reward": "native_sparse_win_1_loss_minus1_draw0_truncation0",
            "opponents": [
                "random",
                "poke-env-MaxBasePowerPlayer",
                "poke-env-SimpleHeuristicsPlayer",
            ],
            "training_species": [
                x[0]
                for x in __import__(
                    "advisor.learned_scenarios", fromlist=["TRAIN"]
                ).TRAIN
            ],
            "completed_episodes": len(completed),
            "wins": sum(r["winner"] == "self" for r in completed),
            "losses": sum(r["winner"] == "opponent" for r in completed),
            "draws": sum(r["winner"] is None and not r["truncated"] for r in completed),
            "truncated": sum(r["truncated"] for r in completed),
            "resume_source_sha256": sha256(
                Path(resume).with_suffix(".zip").read_bytes()
            ).hexdigest()
            if resume
            else None,
            "training_metrics": metrics,
        }
        for stage in ("distillation", "value_calibration"):
            if source and stage in source.metadata:
                metadata[stage] = source.metadata[stage]
        output.with_suffix(".json").write_text(
            json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8"
        )
        # Reload without optimizer/trainer state supplied by this process.
        reloaded = MaskablePPO.load(output, device="cpu")
        obs = encoder.encode(vector.envs[0].current)
        mask = vector.envs[0].action_masks()
        if not mask.any():
            raise AssertionError("reload_test_requires_actionable_observation")
        if mask.any():
            original = model.predict(obs, action_masks=mask, deterministic=True)[0]
            restored = reloaded.predict(obs, action_masks=mask, deterministic=True)[0]
            assert int(original) == int(restored)
            with torch.no_grad():
                a = model.policy.predict_values(torch.tensor(obs)[None, :])
                b = reloaded.policy.predict_values(torch.tensor(obs)[None, :])
                assert torch.equal(a, b)
        return {**metadata, "reload_inference_equal": True}
    finally:
        vector.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=2048)
    parser.add_argument("--envs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            train(
                args.checkout,
                args.catalog,
                args.output,
                steps=args.steps,
                envs=args.envs,
                seed=args.seed,
                resume=args.resume,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
