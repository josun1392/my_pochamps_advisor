"""Narrow masked BC/Monte Carlo AWR adapter on existing SB3 policy/optimizer.

Only executed public-view trajectories are used. This is empirical offline
return weighting, not a Q-learning engine, exact probability or optimal label.
The AWR exponential weighting follows Peng et al. (2019), MIT reference;
maintained RLlib MARWIL independently implements the same weighted likelihood
family. Existing MaskablePPO remains the online learner and checkpoint format.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import numpy as np
import torch
from advisor.learning_resources import atomic_json
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT

SCHEMA = "showdown-public-trajectory-dataset-v1"
FIELDS = {
    "observations": np.float32,
    "masks": np.bool_,
    "actions": np.int64,
    "returns": np.float32,
    "episodes": np.int32,
}


def file_hash(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class TrajectoryWriter:
    """Disk-backed arrays; publish a manifest only after complete episode targets."""

    def __init__(self, path, capacity, dimension, metadata):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.metadata = metadata
        self.count = self.episodes = 0
        self.outcomes, self.behaviors, self.classes = Counter(), Counter(), Counter()
        self.arrays = {
            name: np.lib.format.open_memmap(
                self.path / f"{name}.npy",
                mode="w+",
                dtype=dtype,
                shape=(capacity, dimension)
                if name == "observations"
                else (capacity, 35)
                if name == "masks"
                else (capacity,),
            )
            for name, dtype in FIELDS.items()
        }

    def add_episode(self, rows, reward, behavior):
        if not rows or reward not in (-1.0, 0.0, 1.0):
            raise ValueError("complete_terminal_episode_required")
        if self.count + len(rows) > len(self.arrays["actions"]):
            raise ValueError("offline_capacity_exceeded")
        gamma = self.metadata["gamma"]
        for i, (x, mask, action, category) in enumerate(rows):
            if not np.isfinite(x).all() or not mask[action]:
                raise ValueError("invalid_public_trajectory_row")
            n = self.count
            for name, value in (
                ("observations", x),
                ("masks", mask),
                ("actions", action),
                ("returns", reward * gamma ** (len(rows) - i - 1)),
                ("episodes", self.episodes),
            ):
                self.arrays[name][n] = value
            self.classes[category] += 1
            self.count += 1
        self.episodes += 1
        self.outcomes[str(reward)] += 1
        self.behaviors[behavior] += len(rows)

    def finish(self, details):
        if not self.count:
            raise ValueError("empty_complete_trajectory_dataset")
        for array in self.arrays.values():
            array.flush()
        manifest = {
            **self.metadata,
            **details,
            "schema_version": SCHEMA,
            "evidence_scope": "actually_executed_partial_observation_episode_returns_not_optimal_action_labels",
            "rows": self.count,
            "completed_episodes": self.episodes,
            "terminal_outcomes": dict(self.outcomes),
            "behavior_rows": dict(self.behaviors),
            "action_classes": dict(self.classes),
            "files": {name: file_hash(self.path / f"{name}.npy") for name in FIELDS},
        }
        atomic_json(self.path / "manifest.json", manifest)
        return manifest


def load_dataset(path, encoder, *, expected_id=None, gamma=0.99):
    path = Path(path)
    manifest_path = path / "manifest.json"
    identity = file_hash(manifest_path)
    if expected_id and expected_id != identity:
        raise ValueError("offline_dataset_identity_changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "schema_version": SCHEMA,
        "engine_commit": SHOWDOWN_COMMIT,
        "format_id": FORMAT_ID,
        "encoder_version": encoder.version,
        "catalog_fingerprint": encoder.catalog_fingerprint,
        "gamma": gamma,
        "split": "train",
    }
    required["observation_dimension"] = encoder.dimension
    if any(manifest.get(k) != v for k, v in required.items()) or set(
        manifest.get("files", {})
    ) != set(FIELDS):
        raise ValueError("offline_dataset_contract_mismatch")
    n = manifest.get("rows")
    if type(n) is not int or not 1 <= n <= 264192:
        raise ValueError("bounded_offline_dataset_required")
    arrays = {}
    for name, dtype in FIELDS.items():
        file = path / f"{name}.npy"
        if file_hash(file) != manifest["files"][name]:
            raise ValueError("offline_dataset_file_hash_mismatch")
        values = np.load(file, mmap_mode="r", allow_pickle=False)
        trailing = (
            (manifest["observation_dimension"],)
            if name == "observations"
            else (35,)
            if name == "masks"
            else ()
        )
        if values.dtype != dtype or values.shape[1:] != trailing or len(values) < n:
            raise ValueError("offline_dataset_array_mismatch")
        arrays[name] = values[:n]
    for start in range(0, n, 2048):
        end = min(n, start + 2048)
        action = arrays["actions"][start:end]
        mask = arrays["masks"][start:end]
        if (
            np.any(action < 0)
            or np.any(action >= 35)
            or not np.isfinite(arrays["observations"][start:end]).all()
            or not np.isfinite(arrays["returns"][start:end]).all()
            or np.any(np.abs(arrays["returns"][start:end]) > 1)
            or not mask[np.arange(end - start), action].all()
        ):
            raise ValueError("offline_dataset_integrity_failure")
    return arrays, manifest, identity


def advantage_weights(returns, values, temperature=1.0, cap=20.0):
    if not 0.1 <= temperature <= 5 or not 1 <= cap <= 20:
        raise ValueError("bounded_advantage_weighting_required")
    # Stop gradients through weights: policy/value do not game their own labels.
    return torch.exp(
        ((returns - values.detach()) / temperature).clamp(-20, np.log(cap))
    ).detach()


def fit_offline(
    model, encoder, config, seed, budget, *, completed_epochs=0, on_epoch=None
):
    """Reuse masked policy evaluation and Adam; no bootstrapping of illegal actions."""
    arrays, manifest, identity = load_dataset(
        config["dataset"],
        encoder,
        expected_id=config.get("dataset_id"),
        gamma=model.gamma,
    )
    mode = config.get("mode", "awr")
    epochs = config.get("epochs", 8)
    if mode not in {"bc", "awr"} or not 1 <= epochs <= 32:
        raise ValueError("invalid_offline_learning_mode")
    n = len(arrays["actions"])
    started, updates = perf_counter(), 0
    old_rates = [g["lr"] for g in model.policy.optimizer.param_groups]
    for g in model.policy.optimizer.param_groups:
        g["lr"] = config.get("learning_rate", 5e-5)
    model.policy.set_training_mode(True)
    records = []
    before = torch.cat(
        [p.detach().flatten() for p in model.policy.parameters()]
    ).clone()
    try:
        for epoch in range(completed_epochs, epochs):
            if budget.stopping():
                break
            totals = np.zeros(5)
            seen = 0
            # Epoch-addressed permutation makes checkpoint/restart deterministic.
            rng = np.random.default_rng(np.random.SeedSequence([seed, epoch, 1987]))
            indices = rng.permutation(n)
            for start in range(0, n, 128):
                if budget.stopping():
                    break
                batch = indices[start : start + 128]
                x = torch.tensor(arrays["observations"][batch], device=model.device)
                actions = torch.tensor(arrays["actions"][batch], device=model.device)
                targets = torch.tensor(arrays["returns"][batch], device=model.device)
                values, logp, entropy = model.policy.evaluate_actions(
                    x, actions, action_masks=arrays["masks"][batch]
                )
                values = values.flatten()
                weights = (
                    advantage_weights(targets, values, config.get("temperature", 1.0))
                    if mode == "awr"
                    else torch.ones_like(targets)
                )
                loss = (
                    -(weights * logp).mean()
                    + 0.5 * (values - targets).square().mean()
                    - config.get("entropy", 0.01) * entropy.mean()
                )
                if not torch.isfinite(loss):
                    raise ValueError("nonfinite_offline_loss")
                model.policy.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.policy.parameters(), 0.5)
                model.policy.optimizer.step()
                updates += 1
                seen += len(batch)
                totals += len(batch) * np.array(
                    [
                        float(loss.detach()),
                        float((values - targets).square().mean().detach()),
                        float(weights.mean()),
                        float((weights * targets).mean()),
                        float(targets.mean()),
                    ]
                )
            if seen != n:
                # A saved partial epoch is never claimed as an exactly resumed epoch.
                break
            records.append(
                dict(
                    zip(
                        (
                            "loss",
                            "value_mse",
                            "mean_weight",
                            "weighted_return",
                            "return",
                        ),
                        (totals / seen).tolist(),
                    )
                )
            )
            completed_epochs = epoch + 1
            progress = {
                "dataset_id": identity,
                "mode": mode,
                "completed_epochs": completed_epochs,
                "rows": n,
                "optimizer_updates_this_launch": updates,
                "metrics": records[-1],
            }
            if on_epoch:
                on_epoch(progress)
                model.policy.set_training_mode(True)
    finally:
        for group, rate in zip(model.policy.optimizer.param_groups, old_rates):
            group["lr"] = rate
    model._last_obs = None
    after = torch.cat([p.detach().flatten() for p in model.policy.parameters()])
    return {
        "dataset_id": identity,
        "mode": mode,
        "rows": n,
        "dataset_completed_episodes": manifest["completed_episodes"],
        "completed_epochs": completed_epochs,
        "optimizer_updates_this_launch": updates,
        "epoch_metrics": records,
        "parameter_l1_change": float((after - before).abs().sum()),
        "wall_seconds": perf_counter() - started,
        "partial_epoch_discarded_on_exact_resume": budget.stopping()
        and completed_epochs < epochs,
    }
