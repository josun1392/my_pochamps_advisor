"""Bounded native heuristic distillation using the existing masked SB3 policy.

Supervised cross entropy and realized discounted-return MSE, then native PPO can
continue. This implements no RL update algorithm or battle mechanics.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hashlib import sha256
import argparse, json, random
from time import perf_counter
import numpy as np
import torch
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_policy import LearnedPolicy


def warmstart(
    checkout,
    catalog,
    source,
    output,
    *,
    decisions=4096,
    epochs=12,
    seed=31,
    value_only=False,
):
    if not 512 <= decisions <= 8192 or not 1 <= epochs <= 24:
        raise ValueError("bounded_distillation_required")
    path = Path(output)
    if path.with_suffix(".zip").exists() or path.with_suffix(".json").exists():
        raise ValueError("new_model_output_required")
    loaded = LearnedPolicy(source, catalog)
    model = loaded.model
    actor_parameters = list(model.policy.mlp_extractor.policy_net.parameters()) + list(
        model.policy.action_net.parameters()
    )
    actor_before = torch.cat([p.detach().flatten() for p in actor_parameters]).clone()
    torch.manual_seed(seed)
    rng = random.Random(seed)
    encoder = loaded.encoder
    started = perf_counter()
    data = []
    episode = []
    attempted = 0
    with ShowdownLearningEnv(
        checkout, encoder, index_offset=800000, max_decisions=256
    ) as env:
        teacher = VisibleBaseline("heuristic", seed)
        # Collect complete episodes; never assign fake loss/return to truncation.
        while len(data) < decisions:
            attempted += 1
            if attempted > decisions * 4:
                raise RuntimeError("distillation_completion_budget_exceeded")
            observation = env.current
            action = loaded.act(observation) if value_only else teacher.act(observation)
            episode.append(
                (
                    encoder.encode(observation),
                    np.asarray(observation["action_mask"], dtype=bool),
                    action,
                )
            )
            _, reward, ended, truncated, _ = env.step(action)
            if ended or truncated:
                if ended:
                    data.extend(
                        (
                            obs,
                            mask,
                            action,
                            reward * (model.gamma ** (len(episode) - 1 - i)),
                        )
                        for i, (obs, mask, action) in enumerate(episode)
                    )
                episode = []
                env.reset()
        episodes = len(env.completed)
    observations = torch.tensor(np.stack([r[0] for r in data]))
    masks = np.stack([r[1] for r in data])
    actions = torch.tensor([r[2] for r in data], dtype=torch.long)
    returns = torch.tensor([r[3] for r in data], dtype=torch.float32)

    def loss(indices):
        values, log_prob, _ = model.policy.evaluate_actions(
            observations[indices], actions[indices], action_masks=masks[indices]
        )
        return -log_prob.mean(), torch.nn.functional.mse_loss(
            values.flatten(), returns[indices]
        )

    with torch.no_grad():
        before_ce, before_value = loss(np.arange(len(data)))
    before = torch.cat(
        [p.detach().flatten() for p in model.policy.parameters()]
    ).clone()
    updates = 0
    for _ in range(epochs):
        order = list(range(len(data)))
        rng.shuffle(order)
        for start in range(0, len(order), 128):
            ce, v = loss(order[start : start + 128])
            objective = 0.5 * v if value_only else ce + 0.5 * v
            model.policy.optimizer.zero_grad()
            objective.backward()
            torch.nn.utils.clip_grad_norm_(model.policy.parameters(), 0.5)
            model.policy.optimizer.step()
            updates += 1
    with torch.no_grad():
        after_ce, after_value = loss(np.arange(len(data)))
    if value_only and not torch.equal(
        actor_before, torch.cat([p.detach().flatten() for p in actor_parameters])
    ):
        raise AssertionError("value_calibration_changed_policy")
    model.save(path)
    metadata = {
        **loaded.metadata,
        "model_sha256": sha256(path.with_suffix(".zip").read_bytes()).hexdigest(),
        "value_calibration" if value_only else "distillation": {
            "schema_version": "showdown-visible-return-calibration-v1"
            if value_only
            else "showdown-visible-teacher-distillation-v1",
            "source_model_id": loaded.model_id,
            "teacher": "frozen_current_policy"
            if value_only
            else "poke-env-SimpleHeuristicsPlayer",
            "policy_unchanged": bool(value_only),
            "seed": seed,
            "native_decisions": len(data),
            "completed_native_episodes": episodes,
            "epochs": epochs,
            "optimizer_steps": updates,
            "seconds": perf_counter() - started,
            "teacher_cross_entropy_before": float(before_ce),
            "teacher_cross_entropy_after": float(after_ce),
            "realized_return_mse_before": float(before_value),
            "realized_return_mse_after": float(after_value),
            "parameter_l1_change": float(
                (
                    torch.cat([p.detach().flatten() for p in model.policy.parameters()])
                    - before
                )
                .abs()
                .sum()
            ),
        },
    }
    path.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8"
    )
    return metadata["value_calibration" if value_only else "distillation"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("checkout", "catalog", "source", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--decisions", type=int, default=4096)
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--value-only", action="store_true")
    a = p.parse_args()
    print(
        json.dumps(
            warmstart(
                a.checkout,
                a.catalog,
                a.source,
                a.output,
                decisions=a.decisions,
                epochs=a.epochs,
                value_only=a.value_only,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
