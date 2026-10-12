"""Resumable, validation-selected CPU training with a hard process-tree budget."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
from hashlib import sha256
import json
import importlib.metadata
import os
import random
import subprocess
from time import perf_counter, time
from uuid import uuid4
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from advisor.learned_action_encoder import make_encoder, VERSION
from advisor.learned_action_policy import (
    ActionConditionedPolicy,
    TacticalActionConditionedPolicy,
    transfer_v2_weights,
    PublicInteractionPolicy,
    transfer_v3_weights,
)
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_policy import LearnedPolicy
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    process_alive,
    enforce_local_network_only,
)
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from scripts.evaluate_showdown_policy import evaluate

CURRICULUM = "showdown-learning-curriculum-v2"


def validate_config(config):
    if config.get("schema_version") != "showdown-autonomous-training-v1":
        raise ValueError("unsupported_trainer_config")
    if config.get("curriculum_version", CURRICULUM) not in {
        "showdown-learning-curriculum-v1",
        CURRICULUM,
        "showdown-learning-curriculum-v3",
        "showdown-learning-curriculum-v4",
        "showdown-learning-curriculum-v5",
        "showdown-learning-curriculum-v6",
        "showdown-learning-curriculum-v7",
        "showdown-learning-curriculum-v8",
    }:
        raise ValueError("unsupported_learning_curriculum")
    rivals = config.get("evaluation_opponents", ["random", "max_power", "heuristic"])
    if (
        not rivals
        or len(rivals) > 6
        or len(set(rivals)) != len(rivals)
        or set(rivals)
        - {
            "random",
            "max_power",
            "heuristic",
            "champions_heuristic",
            "tactical_heuristic",
            "previous",
        }
    ):
        raise ValueError("invalid_evaluation_opponents")
    if "previous" in rivals and not config.get("previous_model"):
        raise ValueError("previous_opponent_requires_model")
    if not 30 <= config.get("max_runtime_seconds", 0) <= 21600:
        raise ValueError("runtime_must_be_bounded_30_to_21600_seconds")
    if (
        not 1 <= config.get("envs", 4) <= 8
        or not 1024 <= config.get("memory_mib", 3072) <= 16384
    ):
        raise ValueError("unsafe_worker_or_memory_budget")
    if not 1 <= config.get("cpu_percent", 12.5) <= 75:
        raise ValueError("unsafe_cpu_budget")
    if config.get("vector_backend", "dummy") not in {"dummy", "subproc"} or config.get(
        "device", "cpu"
    ) not in {"cpu", "cuda"}:
        raise ValueError("unsupported_vector_or_device")
    if (
        not 1 <= config.get("cpu_threads", 1) <= 8
        or not 0.05 <= config.get("gpu_memory_fraction", 0.25) <= 0.5
    ):
        raise ValueError("unsafe_tensor_resource_budget")
    if config.get("vector_backend") == "subproc" and config.get(
        "memory_mib", 3072
    ) < 1024 + 768 * config.get("envs", 4):
        raise ValueError("insufficient_spawn_memory_budget")
    if not 1 <= config.get("validation_cases", 24) <= 64:
        raise ValueError("bounded_validation_required")
    if (
        not 0 <= config.get("final_test_cases", 0) <= 128
        or not 1 <= config.get("plateau_patience", 4) <= 12
    ):
        raise ValueError("invalid_test_or_plateau_budget")
    if not config.get("experiments") or len(config["experiments"]) > 12:
        raise ValueError("one_to_twelve_experiments_required")
    references = config.get("reference_models", {})
    if (
        not isinstance(references, dict)
        or len(references) > 3
        or set(references) & {"best", "random", "heuristic", "previous"}
    ):
        raise ValueError("invalid_reference_models")
    rollout = 128 * config.get("envs", 4)
    for experiment in config["experiments"]:
        frozen = experiment.get("frozen_opponents", {})
        if (
            not isinstance(frozen, dict)
            or len(frozen) > 4
            or set(frozen)
            & {
                "random",
                "max_power",
                "heuristic",
                "champions_heuristic",
                "tactical_heuristic",
                "previous",
                "historical",
            }
            or any(
                not isinstance(name, str)
                or not name.isidentifier()
                or not isinstance(path, str)
                for name, path in frozen.items()
            )
        ):
            raise ValueError("invalid_frozen_opponents")
        offline = experiment.get("offline")
        if offline is not None and (
            not isinstance(offline, dict)
            or offline.get("mode", "awr") not in {"bc", "awr"}
            or not 1 <= offline.get("epochs", 8) <= 32
            or not isinstance(offline.get("dataset"), str)
            or not 0.1 <= offline.get("temperature", 1.0) <= 5
            or not 1e-6 <= offline.get("learning_rate", 5e-5) <= 1e-3
            or not 0 <= offline.get("entropy", 0.01) <= 0.1
            or experiment.get("warmstart_decisions", 0)
        ):
            raise ValueError("invalid_offline_learning_config")
        if experiment.get("encoder_version", VERSION) not in {
            VERSION,
            "showdown-learned-observation-v1",
            "showdown-learned-observation-v3",
            "showdown-learned-observation-v4",
        }:
            raise ValueError("unsupported_encoder")
        if experiment.get("transfer_model") and (
            experiment.get("initial_model")
            or experiment.get("encoder_version")
            not in {
                "showdown-learned-observation-v3",
                "showdown-learned-observation-v4",
            }
        ):
            raise ValueError("transfer_requires_fresh_v3_optimizer")
        if (
            not rollout <= experiment["steps"] <= 1048576
            or experiment["steps"] % rollout
        ):
            raise ValueError("bounded_steps_divisible_by_rollout_required")
        if (
            not rollout <= config.get("checkpoint_steps", 8192) <= 65536
            or config.get("checkpoint_steps", 8192) % rollout
        ):
            raise ValueError("invalid_checkpoint_interval")
        if (
            not 0 <= experiment.get("warmstart_decisions", 0) <= 16384
            or not 1 <= experiment.get("warmstart_epochs", 8) <= 24
        ):
            raise ValueError("unsafe_warmstart_budget")
        opponents = experiment.get("opponents", ["random", "max_power", "heuristic"])
        if (
            not opponents
            or len(opponents) > 12
            or set(opponents)
            - {
                "random",
                "max_power",
                "heuristic",
                "champions_heuristic",
                "tactical_heuristic",
                "previous",
                "historical",
            }
            - set(frozen)
        ):
            raise ValueError("unsupported_opponent_mixture")
        if experiment.get("teacher", "heuristic") not in {
            "heuristic",
            "champions_heuristic",
            "tactical_heuristic",
        }:
            raise ValueError("unsupported_warmstart_teacher")
        if experiment.get("historical_model") and "historical" not in opponents:
            raise ValueError("fixed_historical_requires_historical_opponent")
        if (
            not 1e-6 <= experiment.get("learning_rate", 1e-4) <= 1e-3
            or not 0 <= experiment.get("ent_coef", 0.005) <= 0.1
        ):
            raise ValueError("unsafe_learning_hyperparameters")
        if (
            not 1e-6
            <= experiment.get(
                "warmstart_learning_rate", experiment.get("learning_rate", 1e-4)
            )
            <= 1e-3
        ):
            raise ValueError("unsafe_warmstart_learning_rate")
    return config


def optimizer_steps(model):
    return max(
        (int(s["step"]) for s in model.policy.optimizer.state.values() if "step" in s),
        default=0,
    )


def freeze_historical_reference(
    state, number, previous_path, *, resumed, required, fixed_path=None
):
    """An experiment's opponent cannot silently change when its best model changes."""
    if state.get("frozen_historical_experiment") == number:
        return state.get("frozen_historical_path")
    if resumed and required:
        raise ValueError(
            "legacy_resume_missing_frozen_opponent_identity_start_new_explicit_run"
        )
    path = fixed_path or state.get("best") or previous_path
    state["frozen_historical_experiment"] = number
    state["frozen_historical_path"] = path
    state.pop("frozen_historical_model_id", None)
    return path


def save_checkpoint(model, encoder, directory, metadata):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "model"
    model.save(path)
    atomic_json(
        path.with_suffix(".json"),
        {
            "schema_version": "showdown-learned-model-v1",
            "evidence_class": "learned_policy_value",
            "interpretation": "experimental_policy_distribution_and_discounted_return_not_exact_win_probability",
            "algorithm": "sb3-contrib-MaskablePPO",
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
            "policy_class": type(model.policy).__name__,
            "model_seed": model.seed,
            "encoder_version": encoder.version,
            "catalog_fingerprint": encoder.catalog_fingerprint,
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
            "action_schema_version": "showdown-policy-actions-v1",
            "model_sha256": sha256(path.with_suffix(".zip").read_bytes()).hexdigest(),
            "total_steps": model.num_timesteps,
            "optimizer_steps": optimizer_steps(model),
            "parameter_count": sum(p.numel() for p in model.policy.parameters()),
            "observation_dim": encoder.dimension,
            "device": model.device.type,
            "gamma": model.gamma,
            "curriculum_version": CURRICULUM,
            **metadata,
        },
    )
    return str(path.with_suffix(".zip"))


class BudgetCallback(BaseCallback):
    def __init__(self, budget, progress=None):
        super().__init__()
        self.budget = budget
        self.progress = progress
        self.last_progress = 0

    def _on_step(self):
        if self.progress and time() - self.last_progress >= 2:
            self.progress(self.model.num_timesteps)
            self.last_progress = time()
        return not self.budget.stopping()


def warmstart(
    model,
    vector,
    encoder,
    count,
    epochs,
    seed,
    budget,
    learning_rate=3e-4,
    teacher_kind="heuristic",
    collection_env=None,
):
    """Supervised visible heuristic targets; upstream policy/optimizer stay authoritative."""
    if not count:
        return {"decisions": 0, "optimizer_updates": 0}
    rows = []
    env = collection_env if collection_env is not None else vector.envs[0]
    teacher = VisibleBaseline(teacher_kind, seed + 41)
    env.reset(seed=seed + 7300)
    attempted = 0
    episodes = 0
    classes = Counter()
    while len(rows) < count and attempted < count * 8 and not budget.stopping():
        episode = []
        env.reset()
        while not budget.stopping():
            view = env.current
            action = teacher.act(view)
            from advisor.learned_tactical_diagnostics import action_class

            category = action_class(view, action)
            classes[category] += 1
            episode.append(
                (encoder.encode(view), env.action_masks().copy(), action, category)
            )
            _, reward, terminated, truncated, _ = env.step(action)
            attempted += 1
            if terminated or truncated:
                episodes += 1
                if terminated:
                    rows.extend(
                        (
                            x,
                            mask,
                            action,
                            reward * model.gamma ** (len(episode) - i - 1),
                            category,
                        )
                        for i, (x, mask, action, category) in enumerate(episode)
                    )
                break
    rows = rows[:count]
    if not rows:
        return {"decisions": 0, "optimizer_updates": 0, "episodes": episodes}
    x = torch.tensor(np.stack([r[0] for r in rows]), device=model.device)
    masks = np.stack([r[1] for r in rows])
    actions = torch.tensor([r[2] for r in rows], device=model.device)
    returns = torch.tensor(
        [r[3] for r in rows], dtype=torch.float32, device=model.device
    )
    generator = torch.Generator().manual_seed(seed)
    updates = 0
    last_loss = None
    model.policy.set_training_mode(True)
    before = torch.cat(
        [p.detach().flatten() for p in model.policy.parameters()]
    ).clone()
    old_rates = [group["lr"] for group in model.policy.optimizer.param_groups]
    for group in model.policy.optimizer.param_groups:
        group["lr"] = learning_rate
    for _ in range(epochs):
        for indices in torch.randperm(len(rows), generator=generator).split(128):
            if budget.stopping():
                break
            values, logp, _ = model.policy.evaluate_actions(
                x[indices], actions[indices], action_masks=masks[indices.numpy()]
            )
            loss = (
                -logp.mean()
                + 0.5 * (values.flatten() - returns[indices]).square().mean()
            )
            if not torch.isfinite(loss):
                raise ValueError("nonfinite_warmstart_loss")
            model.policy.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.policy.parameters(), 0.5)
            model.policy.optimizer.step()
            updates += 1
            last_loss = float(loss.detach())
    for group, rate in zip(model.policy.optimizer.param_groups, old_rates):
        group["lr"] = rate
    correct = 0
    class_correct = Counter()
    with torch.no_grad():
        for indices in torch.arange(len(rows)).split(128):
            distribution = model.policy.get_distribution(
                x[indices], action_masks=masks[indices.numpy()]
            )
            correct += int(
                (distribution.distribution.probs.argmax(1) == actions[indices]).sum()
            )
            matches = (
                distribution.distribution.probs.argmax(1) == actions[indices]
            ).tolist()
            for i, match in zip(indices.tolist(), matches):
                class_correct[rows[i][4]] += int(match)
    delta = float(
        (torch.cat([p.detach().flatten() for p in model.policy.parameters()]) - before)
        .abs()
        .sum()
    )
    # The vector/model must restart coherently after direct collection.
    model._last_obs = None
    return {
        "decisions": len(rows),
        "attempted": attempted,
        "episodes": episodes,
        "optimizer_updates": updates,
        "last_loss": last_loss,
        "learning_rate": learning_rate,
        "teacher_demonstration_action_accuracy": correct / len(rows),
        "parameter_l1_change": delta,
        "attempted_teacher_action_classes": dict(classes),
        "retained_teacher_action_classes": dict(Counter(r[4] for r in rows)),
        "teacher_action_accuracy_by_class": {
            k: class_correct[k] / n for k, n in Counter(r[4] for r in rows).items()
        },
    }


def training_config_fingerprint(config):
    identity = None
    if config.get("curriculum_version") == "showdown-learning-curriculum-v7":
        from advisor.learned_full_domain import curriculum_identity

        identity = curriculum_identity(config["catalog"])
    elif config.get("curriculum_version") == "showdown-learning-curriculum-v8":
        from advisor.learned_full_roster import study_identity

        identity = study_identity(config["catalog"])
    content = (
        config if identity is None else {**config, "full_domain_identity": identity}
    )
    return sha256(json.dumps(content, sort_keys=True).encode()).hexdigest(), identity


def run(
    config,
    output,
    *,
    resume=False,
    require_detached=False,
    event_callback=None,
    resource_job=None,
):
    validate_config(config)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    fingerprint, full_domain_identity = training_config_fingerprint(config)
    lock = output / "run.lock"
    if lock.exists():
        old = json.loads(lock.read_text())
        if process_alive(old["pid"]):
            raise RuntimeError("training_output_already_running")
        if not resume:
            raise RuntimeError("stale_lock_requires_explicit_resume")
        lock.unlink()  # Only this trainer's stale lock, never a repository cleanup.
    with lock.open("x", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "started": time()}, f)
    budget = RuntimeLimit(output, config["max_runtime_seconds"])
    started = perf_counter()
    state_path = output / "state.json"
    state = {
        "schema_version": "showdown-autonomous-run-v1",
        "config_fingerprint": fingerprint,
        **(
            {"full_domain_identity": full_domain_identity}
            if full_domain_identity
            else {}
        ),
        "experiment_index": 0,
        "experiment_steps": 0,
        "latest": None,
        "best": None,
        "best_score": -1,
        "evaluations": [],
        "completed_battles": 0,
        "transitions": 0,
        "trained_rollout_transitions": 0,
        "warmstart_decisions": 0,
        "launches": 0,
    }
    vector = None

    def notify(phase, **extra):
        if event_callback:
            event_callback(
                {
                    "phase": phase,
                    "transitions": state["transitions"],
                    "completed_battles": state["completed_battles"],
                    **extra,
                }
            )

    try:
        job = resource_job or WindowsJob(
            memory_mib=config.get("memory_mib", 3072),
            cpu_percent=config.get("cpu_percent", 12.5),
            active_process_limit=max(12, 4 * config.get("envs", 4) + 8)
            if config.get("vector_backend") == "subproc"
            else 12,
        )
        device = config.get("device", "cpu")
        if device == "cuda":
            os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
            if not torch.cuda.is_available():
                raise RuntimeError("configured_cuda_unavailable_no_silent_fallback")
            torch.cuda.set_per_process_memory_fraction(
                config.get("gpu_memory_fraction", 0.25)
            )
        if require_detached and job.inherited_job:
            raise RuntimeError("trainer_still_in_launcher_job_persistence_not_verified")
        if resume:
            state = json.loads(state_path.read_text())
            if state["config_fingerprint"] != fingerprint:
                raise ValueError("resume_config_fingerprint_mismatch")
            if (output / "STOP").exists():
                (output / "STOP").unlink()
            if "trained_rollout_transitions" not in state:
                # Compatibility with early local trainer states: count only complete rollouts.
                paths = {row["checkpoint"] for row in state["evaluations"]}
                if state.get("latest"):
                    paths.add(state["latest"])
                rollout = 128 * config.get("envs", 4)
                state["trained_rollout_transitions"] = sum(
                    json.loads(Path(path).with_suffix(".json").read_text())[
                        "training_metrics"
                    ].get("collected_transitions", 0)
                    // rollout
                    * rollout
                    for path in paths
                )
                state["prior_rollout_count_inferred_from_checkpoint_metrics"] = True
        elif state_path.exists():
            raise ValueError("existing_output_requires_resume")
        state["launches"] += 1
        state["status"] = "running"
        atomic_json(output / "config.json", config)
        atomic_json(
            output / "control.json",
            {
                "pid": os.getpid(),
                "started_unix": time(),
                "inherited_job": job.inherited_job,
                "own_job": True,
                "cpu_percent": config.get("cpu_percent", 12.5),
                "memory_mib": config.get("memory_mib", 3072),
                "deadline_unix": time() + config["max_runtime_seconds"],
                "hard_shutdown_grace_seconds": 30,
                "resume_rollout_semantics": "discard_partial_rollout_reset_native_episodes",
            },
        )
        atomic_json(state_path, state)
        torch.set_num_threads(config.get("cpu_threads", 1))
        torch.use_deterministic_algorithms(True)
        network = enforce_local_network_only()
        catalog = Path(config["catalog"]).resolve()
        checkout = Path(config["checkout"]).resolve()
        previous = (
            LearnedPolicy(
                config["previous_model"],
                catalog,
                expected_model_id=state.get("previous_model_id"),
            )
            if config.get("previous_model")
            else None
        )
        state["previous_model_id"] = previous.model_id if previous else None
        curriculum = config.get("curriculum_version", CURRICULUM)
        evaluation_rivals = {
            kind: previous if kind == "previous" else kind
            for kind in config.get(
                "evaluation_opponents", ["random", "max_power", "heuristic"]
            )
        }
        for number in range(state["experiment_index"], len(config["experiments"])):
            if budget.stopping():
                break
            experiment = config["experiments"][number]
            seed = experiment["seed"]
            torch.manual_seed(seed)
            np.random.seed(seed)
            random.seed(seed)
            encoder = make_encoder(catalog, experiment.get("encoder_version", VERSION))
            historical_path = freeze_historical_reference(
                state,
                number,
                experiment.get("initial_model") or config.get("previous_model"),
                resumed=bool(state.get("latest")),
                required="historical" in experiment.get("opponents", []),
                fixed_path=experiment.get("historical_model"),
            )
            historical = (
                LearnedPolicy(
                    historical_path,
                    catalog,
                    expected_model_id=state.get("frozen_historical_model_id"),
                )
                if historical_path
                else None
            )
            state["frozen_historical_model_id"] = (
                historical.model_id if historical else None
            )
            atomic_json(state_path, state)

            references = {
                kind: (str(path), policy.model_id)
                for kind, path, policy in (
                    ("previous", config.get("previous_model"), previous),
                    ("historical", historical_path, historical),
                )
                if policy is not None
            }
            extra = {}
            for kind, path in experiment.get("frozen_opponents", {}).items():
                policy = LearnedPolicy(path, catalog)
                references[kind] = (str(Path(path).resolve()), policy.model_id)
                extra[kind] = policy.model_id
            previous_extra = state.get("frozen_extra_opponents")
            if state.get("latest"):
                if previous_extra is not None and previous_extra != extra:
                    raise ValueError("frozen_opponent_identity_changed_on_resume")
            state["frozen_extra_opponents"] = extra
            atomic_json(state_path, state)
            factories = [
                LearningEnvFactory(
                    str(checkout),
                    str(catalog),
                    encoder.version,
                    i * 100000,
                    curriculum,
                    tuple(
                        experiment.get(
                            "opponents", ["random", "max_power", "heuristic"]
                        )
                    ),
                    references,
                    config.get("collect_tactical_metrics", False),
                )
                for i in range(config.get("envs", 4))
            ]
            vector = (
                SubprocVecEnv(factories, start_method="spawn")
                if config.get("vector_backend", "dummy") == "subproc"
                else DummyVecEnv(factories)
            )
            source = state["latest"] if state["experiment_index"] == number else None
            initial_source = source or experiment.get("initial_model")
            if initial_source:
                loaded = LearnedPolicy(initial_source, catalog)
                if loaded.encoder.version != encoder.version:
                    raise ValueError("initial_model_encoder_mismatch")
                model = (
                    loaded.model
                    if device == "cpu" and loaded.model.n_envs == vector.num_envs
                    else MaskablePPO.load(initial_source, env=vector, device=device)
                )
                model.set_env(vector)
                if not source:
                    model.seed = seed
                    model.set_random_seed(seed)
                    model.learning_rate = experiment.get("learning_rate", 1e-4)
                    model._setup_lr_schedule()
                    model.ent_coef = experiment.get("ent_coef", 0.005)
                    if experiment.get("fresh_optimizer", False):
                        model.policy.optimizer = model.policy.optimizer_class(
                            model.policy.parameters(),
                            lr=model.learning_rate,
                            **model.policy.optimizer_kwargs,
                        )
            else:
                model = MaskablePPO(
                    PublicInteractionPolicy
                    if encoder.version == "showdown-learned-observation-v4"
                    else TacticalActionConditionedPolicy
                    if encoder.version == "showdown-learned-observation-v3"
                    else ActionConditionedPolicy
                    if encoder.version == VERSION
                    else "MlpPolicy",
                    vector,
                    n_steps=128,
                    batch_size=128,
                    n_epochs=4,
                    gamma=0.99,
                    learning_rate=experiment.get("learning_rate", 1e-4),
                    ent_coef=experiment.get("ent_coef", 0.005),
                    target_kl=0.03,
                    seed=seed,
                    device=device,
                    verbose=0,
                    policy_kwargs={}
                    if encoder.version
                    in {
                        VERSION,
                        "showdown-learned-observation-v3",
                        "showdown-learned-observation-v4",
                    }
                    else {"net_arch": {"pi": [64, 64], "vf": [64, 64]}},
                )
            vector.seed(seed + state["experiment_steps"] + state["launches"] * 10000)
            transfer_id = (
                loaded.metadata.get("weight_transfer_source_sha256")
                if initial_source
                else None
            )
            if not initial_source and experiment.get("transfer_model"):
                transfer_source = LearnedPolicy(experiment["transfer_model"], catalog)
                if encoder.version == "showdown-learned-observation-v4":
                    if (
                        transfer_source.encoder.version
                        != "showdown-learned-observation-v3"
                    ):
                        raise ValueError("v3_transfer_source_required")
                    transfer_v3_weights(model.policy, transfer_source.model.policy)
                else:
                    if transfer_source.encoder.version != VERSION:
                        raise ValueError("v2_transfer_source_required")
                    transfer_v2_weights(model.policy, transfer_source.model.policy)
                transfer_id = transfer_source.model_id
            if not source:
                # Keep independent seeds and matched architecture trials after
                # all checkpoint constructors/weight transfers have finished.
                model.set_random_seed(seed)
            warm_episodes = []

            def checkpoint(stage, details):
                episodes = warm_episodes + [
                    row for rows in vector.env_method("drain_completed") for row in rows
                ]
                warm_episodes.clear()
                outcomes = Counter(
                    "truncated" if row["truncated"] else row["winner"] or "draw"
                    for row in episodes
                )
                parameters = torch.cat(
                    [p.detach().flatten() for p in model.policy.parameters()]
                )
                if not torch.isfinite(parameters).all():
                    raise ValueError("nonfinite_learned_parameters")
                directory = (
                    output
                    / f"experiment_{number:02d}"
                    / f"checkpoint_{len(state['evaluations']):04d}_{stage}_{model.num_timesteps}_{uuid4().hex[:8]}"
                )
                path = save_checkpoint(
                    model,
                    encoder,
                    directory,
                    {
                        "experiment": experiment,
                        "curriculum_version": curriculum,
                        **(
                            {"full_domain_identity": full_domain_identity}
                            if full_domain_identity
                            else {}
                        ),
                        "stage": stage,
                        "initial_model": experiment.get("initial_model"),
                        "optimizer_initialization": "restored_same_encoder"
                        if initial_source
                        and (source or not experiment.get("fresh_optimizer", False))
                        else "fresh_same_encoder"
                        if initial_source
                        else "fresh",
                        "weight_transfer_source_sha256": transfer_id,
                        "weight_transfer_optimizer": "fresh_shape_compatible_optimizer"
                        if transfer_id
                        else None,
                        "weight_transfer_optimizer_scope": "ancestor_transfer_only"
                        if transfer_id and initial_source
                        else "current_initialization"
                        if transfer_id
                        else None,
                        "opponent_model_ids": {
                            "previous": previous.model_id if previous else None,
                            "historical": historical.model_id if historical else None,
                        },
                        "warmstart": state.get("warmstart"),
                        "offline": state.get("offline"),
                        "offline_learning_scope": "masked_executed_episode_return_weighting_not_Q_learning_or_optimal_action_labels"
                        if experiment.get("offline")
                        else None,
                        "extra_opponent_model_ids": extra,
                        "training_metrics": details,
                        "vector_backend": config.get("vector_backend", "dummy"),
                        "cpu_threads": config.get("cpu_threads", 1),
                        "gpu_memory_fraction": config.get("gpu_memory_fraction", 0.25)
                        if device == "cuda"
                        else None,
                        "episode_outcomes_this_checkpoint": dict(outcomes),
                    },
                )
                restored = LearnedPolicy(path, catalog)
                view = vector.get_attr("current", indices=0)[0]
                if not any(view["action_mask"]):
                    vector.env_method("reset", indices=0)
                    view = vector.get_attr("current", indices=0)[0]
                a, b = (
                    restored.act(view),
                    int(
                        model.predict(
                            encoder.encode(view),
                            action_masks=view["action_mask"],
                            deterministic=True,
                        )[0]
                    ),
                )
                if a != b:
                    raise AssertionError("checkpoint_reload_action_changed")
                state["latest"] = path
                state["optimizer_steps"] = optimizer_steps(model)
                state["experiment_index"] = number
                state["completed_battles"] += len(episodes)
                # Preserve the compatible counter and explicitly identify time limits.
                state["episode_count_scope"] = "ended_including_time_limit_truncations"
                totals = state.setdefault("episode_outcomes", {})
                for outcome, count in outcomes.items():
                    totals[outcome] = totals.get(outcome, 0) + count
                coverage = state.setdefault("sampled_domain_coverage", {})
                for worker_counts in vector.env_method("drain_coverage"):
                    for category, counts in worker_counts.items():
                        previous_counts = Counter(coverage.get(category, {}))
                        previous_counts.update(counts)
                        coverage[category] = dict(previous_counts)
                state["coverage_scope"] = (
                    "Coordinator fixtures actually reset, self/opponent six-slot rosters and selected three sets; includes active incomplete episodes. Not public actor/critic input, nor executed-move frequency."
                )
                tactical = Counter(state.get("public_tactical_action_counts", {}))
                for counts in vector.env_method("drain_tactical_counts"):
                    tactical.update(counts)
                state["public_tactical_action_counts"] = dict(tactical)
                state["outcome_tally_scope"] = (
                    "checkpoints_written_by_outcome_aware_trainer"
                )
                state["resources"] = {
                    "native_rss_bytes": sum(
                        resource["rss_bytes"]
                        for resource in vector.env_method("learning_resources")
                    ),
                    "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                    if device == "cuda"
                    else 0,
                    "python_cpu_seconds": __import__("time").process_time(),
                    "wall_seconds_this_launch": perf_counter() - started,
                    **job.usage(),
                }
                # Publish a recoverable checkpoint before potentially slower evaluation.
                atomic_json(state_path, state)
                if budget.stopping():
                    return False
                notify("evaluating", resources=state["resources"], checkpoint=path)
                try:
                    result = evaluate(
                        checkout,
                        catalog,
                        {"candidate": restored},
                        cases=config.get("validation_cases", 24),
                        offset=config.get("validation_offset", 7000),
                        curriculum_version=curriculum,
                        rivals=evaluation_rivals,
                        stopping=budget.stopping,
                    )
                except TimeoutError:
                    if budget.stopping():
                        return False
                    raise
                atomic_json(directory / "validation.json", result)
                summary = next(
                    row for row in result["summaries"] if row["opponent"] == "all"
                )
                score = summary["wins"] / summary["n"]
                entry = {
                    "checkpoint": path,
                    "experiment": number,
                    "steps": model.num_timesteps,
                    "score": score,
                    "wins": summary["wins"],
                    "n": summary["n"],
                    "truncated": summary["truncated"],
                    "stage": stage,
                }
                state["evaluations"].append(entry)
                if not summary["truncated"] and score > state.get(
                    "experiment_best_score", -1
                ):
                    state["experiment_best_score"] = score
                    state["plateau"] = 0
                else:
                    state["plateau"] = state.get("plateau", 0) + 1
                if not summary["truncated"] and score > state["best_score"]:
                    state["best"], state["best_score"] = path, score
                atomic_json(state_path, state)
                print(
                    json.dumps(
                        {
                            "checkpoint": entry,
                            "best": state["best"],
                            "battles": state["completed_battles"],
                        }
                    ),
                    flush=True,
                )
                return True

            if not source:
                state["experiment_steps"] = 0
                state["plateau"] = 0
                state["experiment_best_score"] = -1
                collection_env = (
                    factories[0]()
                    if config.get("vector_backend") == "subproc"
                    and experiment.get("warmstart_decisions", 0)
                    else None
                )
                torch.set_num_threads(config.get("cpu_threads", 1))
                try:
                    state["warmstart"] = warmstart(
                        model,
                        vector,
                        encoder,
                        experiment.get("warmstart_decisions", 0),
                        experiment.get("warmstart_epochs", 8),
                        seed,
                        budget,
                        experiment.get(
                            "warmstart_learning_rate",
                            experiment.get("learning_rate", 1e-4),
                        ),
                        experiment.get("teacher", "heuristic"),
                        collection_env=collection_env,
                    )
                finally:
                    if collection_env is not None:
                        warm_episodes.extend(collection_env.drain_completed())
                        collection_env.close()
                state["warmstart_decisions"] += state["warmstart"]["decisions"]
                state["offline"] = None
                if not experiment.get("offline"):
                    checkpoint("initial", {})
            if experiment.get("offline") and not (state.get("offline") or {}).get(
                "complete", False
            ):
                from advisor.learned_offline import fit_offline

                saved_offline = state.get("offline")

                def offline_epoch(progress):
                    nonlocal saved_offline
                    state["offline"] = {
                        **progress,
                        "complete": progress["completed_epochs"]
                        >= experiment["offline"].get("epochs", 8),
                    }
                    # Existing immutable checkpoints preserve optimizer and epoch identity.
                    if (
                        progress["completed_epochs"] % 4 == 0
                        and not state["offline"]["complete"]
                    ):
                        checkpoint("offline", progress)
                        saved_offline = state["offline"].copy()
                        torch.set_num_threads(config.get("cpu_threads", 1))

                torch.set_num_threads(config.get("cpu_threads", 1))
                offline_config = dict(experiment["offline"])
                if saved_offline:
                    offline_config["dataset_id"] = saved_offline["dataset_id"]
                fitted = fit_offline(
                    model,
                    encoder,
                    offline_config,
                    seed,
                    budget,
                    completed_epochs=(state.get("offline") or {}).get(
                        "completed_epochs", 0
                    ),
                    on_epoch=offline_epoch,
                )
                state["offline"] = {
                    **fitted,
                    "complete": fitted["completed_epochs"]
                    >= experiment["offline"].get("epochs", 8),
                }
                if not budget.stopping():
                    checkpoint("offline_complete", fitted)
                    state["plateau"] = 0
                else:
                    state["offline_stopped_launch"] = fitted
                    # Restore only the epoch that belongs to the persisted model.
                    state["offline"] = saved_offline
            while (
                state["experiment_steps"] < experiment["steps"]
                and not budget.stopping()
            ):
                before = torch.cat(
                    [p.detach().flatten() for p in model.policy.parameters()]
                ).clone()
                steps_before = model.num_timesteps
                updates_before = optimizer_steps(model)
                chunk = min(
                    config.get("checkpoint_steps", 8192),
                    experiment["steps"] - state["experiment_steps"],
                )
                torch.set_num_threads(config.get("cpu_threads", 1))
                notify("running", resources=job.usage())

                def live_progress(current):
                    pending = sum(vector.env_method("pending_completed_count"))
                    notify(
                        "running",
                        transitions=state["transitions"] + current - steps_before,
                        completed_battles=state["completed_battles"] + pending,
                        resources=job.usage(),
                    )

                model.learn(
                    total_timesteps=chunk,
                    reset_num_timesteps=False,
                    callback=BudgetCallback(
                        budget, live_progress if event_callback else None
                    ),
                )
                taken = model.num_timesteps - steps_before
                state["experiment_steps"] += taken
                state["transitions"] += taken
                trained = (
                    taken
                    // (128 * config.get("envs", 4))
                    * (128 * config.get("envs", 4))
                )
                state["trained_rollout_transitions"] = (
                    state.get("trained_rollout_transitions", 0) + trained
                )
                delta = float(
                    (
                        torch.cat(
                            [p.detach().flatten() for p in model.policy.parameters()]
                        )
                        - before
                    )
                    .abs()
                    .sum()
                )
                completed = optimizer_steps(model) > updates_before
                metrics = {
                    "collected_transitions": taken,
                    "trained_rollout_transitions": trained,
                    "parameter_l1_change": delta,
                    "optimizer_updates": optimizer_steps(model) - updates_before,
                    "partial_rollout_discarded_on_resume": taken
                    % (128 * config.get("envs", 4))
                    != 0,
                }
                metrics["ppo"] = {
                    k: float(v)
                    for k, v in model.logger.name_to_value.items()
                    if k.startswith("train/")
                    and isinstance(v, (float, int, np.floating))
                    and np.isfinite(v)
                }
                if completed and delta <= 0:
                    raise AssertionError("optimizer_did_not_change_parameters")
                checkpoint("ppo", metrics)
                if state.get("plateau", 0) >= config.get("plateau_patience", 4):
                    break
            vector.close()
            vector = None
            if budget.stopping():
                break
            state["experiment_index"] = number + 1
            state["experiment_steps"] = 0
            state["latest"] = None
            atomic_json(state_path, state)
        state["status"] = "stopped" if budget.stopping() else "complete"
        # Final test is executed once, only after validation selection. No candidate tunes against it.
        if (
            state["status"] == "complete"
            and state["best"]
            and config.get("final_test_cases", 0)
            and not state.get("final_test")
        ):
            players = {
                "best": LearnedPolicy(state["best"], catalog),
                "random": "random",
                "heuristic": "heuristic",
            }
            if "champions_heuristic" in evaluation_rivals:
                players["champions_heuristic"] = "champions_heuristic"
            if previous:
                players["previous"] = previous
            players.update(
                {
                    name: LearnedPolicy(path, catalog)
                    for name, path in config.get("reference_models", {}).items()
                }
            )
            for split in ("test", "unseen"):
                if budget.stopping():
                    break
                result = evaluate(
                    checkout,
                    catalog,
                    players,
                    split=split,
                    cases=config["final_test_cases"],
                    offset=config.get("final_test_offset", 20000),
                    curriculum_version=curriculum,
                    rivals=evaluation_rivals,
                )
                atomic_json(output / f"final_{split}.json", result)
            state["final_test"] = (output / "final_unseen.json").exists()
        state["wall_seconds_this_launch"] = perf_counter() - started
        state["network"] = network
        state["resources"].update(job.usage()) if state.get("resources") else None
        atomic_json(state_path, state)
        return state
    except BaseException as error:
        atomic_json(
            output / "failure.json",
            {
                "error": type(error).__name__,
                "message": str(error),
                "time": time(),
                "resources": job.usage() if "job" in locals() else {},
                "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                if torch.cuda.is_initialized()
                else 0,
                "gpu_peak_reserved_bytes": torch.cuda.max_memory_reserved()
                if torch.cuda.is_initialized()
                else 0,
            },
        )
        raise
    finally:
        if vector is not None:
            vector.close()
        budget.finished.set()
        lock.unlink(missing_ok=True)


def launch_detached(config_path, output, resume):
    """Use the real interpreter: Windows venv launchers create their own parent job."""
    if os.name != "nt":
        raise RuntimeError("detached_launcher_requires_windows")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    # Preserve this verified environment's libraries without the venv process shim.
    site = str(Path(sys.prefix) / "Lib" / "site-packages")
    env["PYTHONPATH"] = site
    env["PYTHONNOUSERSITE"] = "1"
    command = [
        sys._base_executable,
        str(Path(__file__).resolve()),
        "--config",
        str(Path(config_path).resolve()),
        "--output",
        str(output),
        "--require-detached",
    ] + (["--resume"] if resume else [])
    with (output / "process.txt").open("ab", buffering=0) as log:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_BREAKAWAY_FROM_JOB,
        )
    for _ in range(100):
        control = output / "control.json"
        if control.exists() and json.loads(control.read_text())["pid"] == process.pid:
            proof = json.loads(control.read_text())
            if proof["inherited_job"]:
                raise RuntimeError("unverified_detached_job")
            return proof
        if process.poll() is not None:
            raise RuntimeError("detached_trainer_start_failed_see_process_txt")
        __import__("time").sleep(0.1)
    process.terminate()
    raise RuntimeError("detached_trainer_start_timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--offline-dataset",
        type=Path,
        help="Override the public trajectory dataset for offline experiments",
    )
    parser.add_argument("--detach", action="store_true")
    parser.add_argument(
        "--require-detached", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument("--stop", action="store_true")
    parser.add_argument(
        "--checkout",
        type=Path,
        help="Override the local pinned engine path in the config",
    )
    args = parser.parse_args()
    if args.stop:
        (args.output / "STOP").touch()
        print("Graceful stop requested; hard shutdown after 30s grace.")
        return
    if not args.config:
        parser.error("--config is required")
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    if args.checkout:
        config["checkout"] = str(args.checkout.resolve())
    if args.offline_dataset:
        for experiment in config["experiments"]:
            if experiment.get("offline"):
                experiment["offline"]["dataset"] = str(args.offline_dataset.resolve())
    if not config.get("checkout"):
        parser.error("--checkout or config checkout is required")
    validate_config(config)
    if args.detach and (args.checkout or args.offline_dataset):
        args.output.mkdir(parents=True, exist_ok=True)
        effective = args.output / "effective-config.json"
        atomic_json(effective, config)
        args.config = effective
    print(
        json.dumps(
            launch_detached(args.config, args.output, args.resume)
            if args.detach
            else run(
                config,
                args.output,
                resume=args.resume,
                require_detached=args.require_detached,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
