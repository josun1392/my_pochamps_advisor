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
from advisor.learned_regularized_ppo import RegularizedMaskablePPO, regularizer_contract, model_regularizer_contract
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
from advisor.learned_move_identity import VERSIONS as OWN_MOVE_VERSIONS
from advisor.learned_move_identity_policy import OwnMoveTokenPolicy, transfer_v3_to_own_move
from advisor.learned_public_categories import VERSIONS as PUBLIC_CATEGORICAL_VERSIONS
from advisor.learned_public_categories_policy import PublicCategoricalPolicy, transfer_public_categorical_weights
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy, transfer_strategic_public_weights
from advisor.learned_own_hp import VERSIONS as HP_VERSIONS
from advisor.learned_own_hp_policy import OwnExactHPCategoricalPolicy, transfer_own_hp_weights
from advisor.learned_history_sequence import VERSIONS as HISTORY_VERSIONS
from advisor.learned_history_sequence_policy import PublicHistorySequencePolicy, transfer_history_sequence_weights
from advisor.learned_combat_v5 import VERSIONS as COMBAT_V5_VERSIONS
from advisor.learned_combat_v5_policy import IntegratedCombatV5Policy, transfer_combat_v5_weights, transfer_combat_v5_appearance_weights
from advisor.learned_combat_v5_aux import IntegratedCombatV5PPO
from advisor.learned_combat_v5_strategic import VERSION as STRATEGIC_COMBAT_V5
from advisor.learned_combat_v5_strategic_policy import StrategicCombatV5Policy, transfer_strategic_combat_v5_weights
from advisor.learned_combat_v5_strategic_aux import StrategicCombatV5PPO
from advisor.learned_combat_foundation import (
    FoundationCombatPPO, FoundationCombatPolicy, FoundationCombatEncoder, foundation_contract, transfer_foundation_weights,
)
from advisor.learned_parent_anchor import (
    ParentAnchoredFoundationPPO, validate_anchor_contract, model_parent_anchor_contract,
)
from advisor.learned_temperature import (
    TemperatureFoundationPPO, validate_temperature, model_temperature_contract,
)
from advisor.learned_objective import objective_contract, experiment_objective, require_resume_objective, categorical_learning_source_identity
from advisor.learned_training_operations import (
    ACCOUNTING_VERSION, OPERATIONS_VERSION, CompletedRollouts, RetryMonitor, TrainingJournal,
    ProgressRetryMonitor, LEGACY_RETRY_VERSION, PROGRESS_RETRY_VERSION,
)
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


def checkpoint_validation_enabled(config):
    """Explicitly bounded studies can reserve every battle for a frozen panel.

    Default behavior, checkpoint creation and native training are unchanged.
    Disabling validation is only supported with fixed-budget (no selection)
    experiments and no final test inside this trainer.
    """
    mode = config.get("checkpoint_evaluation_mode", "automatic_validation_v1")
    if mode not in {"automatic_validation_v1", "disabled_for_frozen_study_v1"}:
        raise ValueError("unsupported_checkpoint_evaluation_mode")
    enabled = mode == "automatic_validation_v1"
    if not enabled and (config.get("validation_selection_mode") != "diagnostic_fixed_budget_v1"
                        or config.get("final_test_cases", 0)):
        raise ValueError("disabled_validation_requires_fixed_budget_no_final_test")
    return enabled


def validate_config(config):
    checkpoint_validation_enabled(config)
    if type(config.get("collect_opponent_selections", False)) is not bool:
        raise ValueError("boolean_opponent_selection_audit_required")
    if type(config.get("collect_learning_signal_joins", False)) is not bool:
        raise ValueError("boolean_public_signal_collection_required")
    if config.get("retry_monitor_version", LEGACY_RETRY_VERSION) not in {LEGACY_RETRY_VERSION, PROGRESS_RETRY_VERSION}:
        raise ValueError("unsupported_retry_monitor_version")
    if config.get("transition_budget_scope", "legacy_collected_v1") not in {"legacy_collected_v1", "trained_rollouts_v1"}:
        raise ValueError("invalid_transition_budget_scope")
    if config.get("schema_version") != "showdown-autonomous-training-v1":
        raise ValueError("unsupported_trainer_config")
    if config.get("validation_selection_mode", "best_and_plateau") not in {
        "best_and_plateau", "diagnostic_fixed_budget_v1",
    } or type(config.get("collect_rollout_diagnostics", False)) is not bool:
        raise ValueError("unsupported_learning_diagnostic_contract")
    if config.get("validation_selection_mode") == "diagnostic_fixed_budget_v1" and config.get("final_test_cases", 0):
        raise ValueError("diagnostic_mode_has_no_selected_final_test")
    if config.get("training_subset"):
        from advisor.learned_training_subset import NativeTrainingSubset
        if config.get("curriculum_version") != "showdown-learning-curriculum-v8":
            raise ValueError("training_subset_requires_native_v8")
        NativeTrainingSubset(config["training_subset"], config.get("training_subset_sha256"))
    if config.get("validation_subset_probes") and (
        not config.get("training_subset") or not config.get("validation_case_bank")
        or config.get("validation_selection_mode") != "diagnostic_fixed_budget_v1"
    ):
        raise ValueError("subset_probes_require_separate_heldout_and_diagnostic_mode")
    if config.get("terminal_transport_version") not in (None, "native-opaque-terminal-transport-v1"):
        raise ValueError("unsupported_native_terminal_transport")
    if config.get("validation_case_bank"):
        from advisor.learned_evaluation_bank import EvaluationCaseBank

        EvaluationCaseBank(
            config["validation_case_bank"], config.get("validation_case_bank_sha256"),
            scope="validation",
        )
        if config.get("final_test_cases", 0):
            raise ValueError("external_validation_bank_requires_separate_final_evaluation")
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
    if type(config.get("max_decisions", 256)) is not int or not 1 <= config.get("max_decisions", 256) <= 4096:
        raise ValueError("unsafe_native_episode_budget")
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
    if "ppo_update_audit" in config:
        from advisor.learned_ppo_contract_audit import VERSION as audit_version
        if config["ppo_update_audit"] != audit_version or not config.get("collect_learning_signal_joins"):
            raise ValueError("invalid_PPO_update_audit_opt_in")
    for experiment in config["experiments"]:
        if "actor_set_context" in experiment or "legal_set_training" in experiment:
            from advisor.learned_legal_set_context import validate_legal_set_training
            validate_legal_set_training(experiment)
            if config.get("envs") != 4 or config.get("device") != "cpu":
                raise ValueError("legal_set_training_requires_CPU_four_workers")
        if "masked_temperature" in experiment:
            validate_temperature(experiment["masked_temperature"])
            if ("combat_foundation" not in experiment or not experiment.get("initial_model")
                    or experiment.get("fresh_optimizer") is not False or experiment.get("parent_policy_anchor")
                    or experiment.get("transfer_model") or experiment.get("steps") != 65536
                    or rollout != 512 or experiment.get("warmstart_decisions", 0) or experiment.get("offline")):
                raise ValueError("temperature_requires_matched_Foundation_Adam_65536_512")
        if "parent_policy_anchor" in experiment:
            anchor = validate_anchor_contract(experiment["parent_policy_anchor"])
            if ("combat_foundation" not in experiment or not experiment.get("initial_model")
                    or experiment.get("initial_model_id") != anchor["parent_model_sha256"]
                    or experiment.get("fresh_optimizer") is not False
                    or experiment.get("transfer_model") or config.get("device", "cpu") != "cpu"):
                raise ValueError("parent_anchor_requires_declared_foundation_parent_and_Adam")
        if "combat_foundation" in experiment:
            if (experiment["combat_foundation"] != foundation_contract()
                    or experiment.get("encoder_version") != STRATEGIC_COMBAT_V5
                    or experiment.get("gamma") != 1 or experiment.get("gae_lambda") != .95
                    or experiment.get("zero_avoiding_beta") != .001
                    or experiment.get("ent_coef") != .01
                    or experiment.get("warmstart_decisions", 0) or experiment.get("offline")
                    or config.get("memory_mib", 0) > 12288 or config.get("cpu_percent", 0) > 50
                    or config.get("cpu_threads", 1) != 1
                    or config.get("transition_budget_scope") != "trained_rollouts_v1"):
                raise ValueError("combat_foundation_training_contract_mismatch")
        experiment_objective(experiment, experiment.get("encoder_version", VERSION))
        if "zero_avoiding_beta" in experiment:
            regularizer_contract(experiment["zero_avoiding_beta"])
            if experiment["zero_avoiding_beta"] and experiment.get("ent_coef", .005) <= 0:
                raise ValueError("regularizer_requires_positive_entropy_coefficient")
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
        frozen_ids = experiment.get("frozen_opponent_ids")
        if frozen_ids is not None and (not isinstance(frozen_ids, dict)
                or set(frozen_ids) != set(frozen)
                or any(not isinstance(v, str) or len(v) != 64
                       or any(c not in "0123456789abcdef" for c in v) for v in frozen_ids.values())):
            raise ValueError("invalid_frozen_opponent_ids")
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
            *OWN_MOVE_VERSIONS,
            *PUBLIC_CATEGORICAL_VERSIONS,
        }:
            raise ValueError("unsupported_encoder")
        if experiment.get("transfer_model") and (
            experiment.get("initial_model")
            or experiment.get("encoder_version")
            not in {
                "showdown-learned-observation-v3",
                "showdown-learned-observation-v4",
                *OWN_MOVE_VERSIONS,
                *PUBLIC_CATEGORICAL_VERSIONS,
            }
        ):
            raise ValueError("transfer_requires_fresh_v3_optimizer")
        if experiment.get("encoder_version") in OWN_MOVE_VERSIONS and (
            experiment.get("transfer_model") and not experiment.get("fresh_optimizer", False)
        ):
            raise ValueError("own_move_transfer_requires_explicit_fresh_optimizer")
        if experiment.get("encoder_version") in PUBLIC_CATEGORICAL_VERSIONS and (
            experiment.get("transfer_model") and not experiment.get("fresh_optimizer", False)
        ):
            raise ValueError("public_categorical_transfer_requires_explicit_fresh_optimizer")
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
        if experiment.get("opponent_schedule") is not None:
            from advisor.learned_opponent_curriculum import validate_schedule
            validate_schedule(experiment["opponent_schedule"], opponents)
            if (not config.get("collect_opponent_selections") or experiment["steps"] != 65536
                    or experiment.get("warmstart_decisions", 0) or experiment.get("offline")
                    or config.get("transition_budget_scope") != "trained_rollouts_v1"):
                raise ValueError("opponent_schedule_requires_audited_fixed_budget")
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
                "public_failure_aware_v1",
                "public_tactical_exchange_v1",
                "public_observation_best_response_v1",
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
    from advisor.learned_legal_set_context import model_legal_set_context_contract
    set_context = model_legal_set_context_contract(model)
    if "actor_set_context" in metadata and metadata["actor_set_context"] != set_context:
        raise ValueError("legal_set_context_save_metadata_mismatch")
    parent_proof = (model.parent_reference_proof()
                    if model_parent_anchor_contract(model) is not None else None)
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
            **({"integrated_auxiliary": model.auxiliary_metadata()} if hasattr(model, "auxiliary_metadata") else {}),
            **({"integrated_auxiliary_counts": getattr(model,"v5_target_counts",{})} if hasattr(model,"auxiliary_metadata") else {}),
            **({"training_regularizer": model_regularizer_contract(model)}
               if model_regularizer_contract(model) is not None else {}),
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
            **({"combat_foundation": foundation_contract()} if isinstance(model, FoundationCombatPPO) else {}),
            **({"actor_set_context": set_context} if set_context is not None else {}),
            **({"masked_temperature": model_temperature_contract(model), "temperature_state": model.temperature_state()}
               if model_temperature_contract(model) is not None else {}),
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
            "curriculum_version": CURRICULUM,
            **metadata,
            "gamma": model.gamma,
            "gae_lambda": model.gae_lambda,
            "training_objective": objective_contract(model.gamma, model.gae_lambda),
            **({"parent_policy_anchor": model_parent_anchor_contract(model)}
               if model_parent_anchor_contract(model) is not None else {}),
            **({"parent_reference_proof": parent_proof} if parent_proof is not None else {}),
            **({"categorical_learning_source_sha256": categorical_learning_source_identity()}
               if encoder.version in PUBLIC_CATEGORICAL_VERSIONS else {}),
            **({"feature_contract": encoder.feature_contract} if hasattr(encoder, "feature_contract") else {}),
        },
    )
    return str(path.with_suffix(".zip"))


def require_finite_ppo(model, *, rollout=False):
    """Stop before another rollout/checkpoint if learning state is non-finite."""
    for value in model.policy.parameters():
        if not torch.isfinite(value).all():
            raise ValueError("nonfinite_ppo_parameters")
    for state in model.policy.optimizer.state.values():
        for value in state.values():
            if isinstance(value, torch.Tensor) and not torch.isfinite(value).all():
                raise ValueError("nonfinite_ppo_optimizer_state")
    for key, value in list(model.logger.name_to_value.items()):
        if not key.startswith("train/") or not isinstance(value, (float, int, np.floating)):
            continue
        if np.isfinite(value):
            if key == "train/explained_variance":
                model.logger.record("train/explained_variance_defined", 1.0)
            continue
        # Upstream explained variance is undefined for constant return targets,
        # rather than a failed loss/gradient. Make this scope explicit in logs.
        if (key == "train/explained_variance" and np.isnan(value)
                and np.isfinite(model.rollout_buffer.returns).all()
                and np.var(model.rollout_buffer.returns) == 0):
            model.logger.record("train/explained_variance_defined", 0.0)
            continue
        raise ValueError("nonfinite_ppo_metric:" + key)
    if rollout:
        for key in ("observations", "rewards", "values", "returns", "advantages"):
            if not np.isfinite(getattr(model.rollout_buffer, key)).all():
                raise ValueError("nonfinite_ppo_rollout:" + key)


class BudgetCallback(BaseCallback):
    def __init__(self, budget, progress=None, collect_diagnostics=False, signal_recorder=None):
        super().__init__()
        self.budget = budget
        self.progress = progress
        self.last_progress = 0
        self.collect_diagnostics = collect_diagnostics
        self.measurements = {"rollout_seconds": 0., "ppo_update_seconds": 0.,
                             "public_diagnostic_seconds": 0., "rollouts": []}
        self.rollout_start = None
        self.update_start = None
        self.completed_rollouts = CompletedRollouts()
        self.signal_recorder = signal_recorder

    def _on_step(self):
        if self.signal_recorder is not None:
            self.signal_recorder.step(self.locals["infos"], self.locals["dones"])
        if hasattr(self.model, "record_auxiliary"):
            self.model.record_auxiliary(self.locals["infos"])
        if self.progress and time() - self.last_progress >= 2:
            self.progress(self.model.num_timesteps)
            self.last_progress = time()
        return not self.budget.stopping()

    def _on_rollout_start(self):
        self.completed_rollouts.settle(optimizer_steps(self.model))
        if self.signal_recorder is not None:
            self.signal_recorder.start(self.model, optimizer_steps(self.model))
        if hasattr(self.model, "begin_auxiliary_rollout"):
            self.model.begin_auxiliary_rollout()
        require_finite_ppo(self.model)
        if self.collect_diagnostics:
            now = perf_counter()
            if self.update_start is not None:
                self.measurements["ppo_update_seconds"] += now - self.update_start
            self.rollout_start, self.update_start = now, None

    def _on_rollout_end(self):
        if hasattr(self.model, "freeze_auxiliary_rollout"):
            self.model.freeze_auxiliary_rollout()
        require_finite_ppo(self.model, rollout=True)
        self.completed_rollouts.collected(self.model.n_steps * self.model.n_envs, optimizer_steps(self.model))
        if self.signal_recorder is not None:
            self.signal_recorder.end(self.model, optimizer_steps(self.model))
        if self.collect_diagnostics:
            now = perf_counter()
            self.measurements["rollout_seconds"] += now - self.rollout_start
            buffer = self.model.rollout_buffer
            observations = buffer.observations.reshape(-1, *self.model.observation_space.shape)
            masks = buffer.action_masks.reshape(-1, self.model.action_space.n)
            maxima, entropies = [], []
            with torch.no_grad():
                for i in range(0, len(observations), 128):
                    dist = self.model.policy.get_distribution(
                        torch.as_tensor(observations[i:i+128], device=self.model.device),
                        action_masks=masks[i:i+128])
                    selected = ~masks[i:i+128, 26].astype(bool)
                    maxima.extend(dist.distribution.probs.max(dim=1).values.cpu().numpy()[selected].tolist())
                    entropies.extend(dist.entropy().cpu().numpy()[selected].tolist())
            self.measurements["rollouts"].append({
                "model_timesteps": self.model.num_timesteps,
                "scope": "pre_update_own_public_rollout_excluding_wait_only_decisions",
                "decisions": len(maxima),
                "max_legal_action_probability_quantiles": np.quantile(maxima, [0, .25, .5, .75, .95, 1]).tolist() if maxima else [],
                "mean_action_entropy": float(np.mean(entropies)) if entropies else None,
                "effective_rollout_transitions": len(observations),
                "advantage_mean": float(buffer.advantages.mean()),
                "advantage_std": float(buffer.advantages.std()),
                "return_mean": float(buffer.returns.mean()),
                "return_std": float(buffer.returns.std()),
                "nonzero_reward_count": int(np.count_nonzero(buffer.rewards)),
            })
            self.update_start = perf_counter()
            self.measurements["public_diagnostic_seconds"] += self.update_start - now

    def _on_training_end(self):
        require_finite_ppo(self.model)
        self.completed_rollouts.settle(optimizer_steps(self.model))
        if self.signal_recorder is not None:
            self.signal_recorder.settled(optimizer_steps(self.model), self.model)
        if self.collect_diagnostics and self.update_start is not None:
            self.measurements["ppo_update_seconds"] += perf_counter() - self.update_start
            self.update_start = None


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
    if any(e.get("encoder_version") in PUBLIC_CATEGORICAL_VERSIONS for e in config.get("experiments", [])):
        content = {**content, "categorical_learning_source_sha256": categorical_learning_source_identity()}
    if config.get("training_subset"):
        from advisor.learned_training_subset import NativeTrainingSubset
        content = {**content, "native_training_subset": NativeTrainingSubset(
            config["training_subset"], config["training_subset_sha256"]).identity}
    if any("public_failure_aware_v1" in e.get("opponents", []) for e in config["experiments"]):
        from advisor.learned_failure_opponent import VERSION as failure_version
        content = {**content, "public_failure_opponent": failure_version,
                   "public_failure_source_sha256": {
                       name: sha256((Path(__file__).resolve().parents[1] / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                       for name in ("advisor/learned_failure_opponent.py", "advisor/learned_public_metrics.py")}}
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
        "operations_version": OPERATIONS_VERSION,
        "training_accounting_version": ACCOUNTING_VERSION,
    }
    vector = None
    execution_failed = False
    journal = None

    def notify(phase, **extra):
        if journal is not None:
            journal.append(phase, transitions=extra.get("transitions", state["transitions"]),
                completed_battles=extra.get("completed_battles", state["completed_battles"]),
                details=extra)
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
            if state.get("training_accounting_version") != ACCOUNTING_VERSION:
                raise ValueError("resume_accounting_version_mismatch_no_legacy_reinterpretation")
            if (output / "STOP").exists():
                (output / "STOP").unlink()
        elif state_path.exists():
            raise ValueError("existing_output_requires_resume")
        journal = TrainingJournal(output, state)
        if resume and state.get("retry_monitor_pending"):
            journal.append("retry_episodes_retired_on_resume", pending=state["retry_monitor_pending"],
                reason="native_episodes_reset_not_exact_mid_episode_restore")
        retry_version = config.get("retry_monitor_version", LEGACY_RETRY_VERSION)
        retry_monitor = ProgressRetryMonitor() if retry_version == PROGRESS_RETRY_VERSION else RetryMonitor()
        if retry_version == PROGRESS_RETRY_VERSION:
            state["retry_monitor_version"] = retry_version
        state["retry_monitor_pending"] = {}
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
                expected_model_id=state.get("previous_model_id") or config.get("previous_model_id"),
            )
            if config.get("previous_model")
            else None
        )
        state["previous_model_id"] = previous.model_id if previous else None
        curriculum = config.get("curriculum_version", CURRICULUM)
        subset_identity = None
        if config.get("training_subset"):
            from advisor.learned_training_subset import NativeTrainingSubset
            subset_identity = NativeTrainingSubset(config["training_subset"], config["training_subset_sha256"]).identity
        validation_provider = None
        if config.get("validation_case_bank"):
            from advisor.learned_evaluation_bank import EvaluationCaseBank

            validation_provider = EvaluationCaseBank(
                config["validation_case_bank"], config["validation_case_bank_sha256"],
                scope="validation",
            )
            if config.get("validation_subset_probes"):
                from advisor.learned_training_subset import NativeTrainingSubset, SubsetProbeBank
                validation_provider = SubsetProbeBank(NativeTrainingSubset(
                    config["training_subset"], config["training_subset_sha256"]), validation_provider)
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
            if "combat_foundation" in experiment:
                encoder = FoundationCombatEncoder(catalog)
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
                    expected_model_id=state.get("frozen_historical_model_id") or experiment.get("historical_model_id"),
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
                policy = LearnedPolicy(path, catalog, expected_model_id=experiment.get("frozen_opponent_ids", {}).get(kind))
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
                    max_decisions=config.get("max_decisions", 256),
                    diagnostic_directory=str(output / "public_encoding_failures"),
                    terminal_transport_version=config.get("terminal_transport_version"),
                    training_subset_path=config.get("training_subset"),
                    training_subset_sha256=config.get("training_subset_sha256"),
                    foundation_profile="combat_foundation" in experiment,
                    opponent_schedule=experiment.get("opponent_schedule"),
                    collect_opponent_selections=config.get("collect_opponent_selections", False),
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
                loaded = LearnedPolicy(initial_source, catalog,
                    expected_model_id=None if source else experiment.get("initial_model_id"))
                from advisor.learned_legal_set_context import model_legal_set_context_contract
                actual_set = model_legal_set_context_contract(loaded.model)
                requested_set = experiment.get("actor_set_context")
                if actual_set != requested_set and (source or actual_set is not None):
                    raise ValueError("resume_legal_set_context_contract_mismatch")
                if source and loaded.metadata.get("legal_set_training") != experiment.get("legal_set_training"):
                    raise ValueError("resume_legal_set_training_contract_mismatch")
                if loaded.encoder.version != encoder.version:
                    raise ValueError("initial_model_encoder_mismatch")
                if loaded.metadata.get("combat_foundation") != experiment.get("combat_foundation"):
                    raise ValueError("foundation_initialization_requires_explicit_weight_transfer")
                require_resume_objective(loaded.model, experiment, encoder.version)
                requested_regularizer = (regularizer_contract(experiment["zero_avoiding_beta"])
                                         if "zero_avoiding_beta" in experiment else None)
                actual_regularizer = model_regularizer_contract(loaded.model)
                requested_anchor = experiment.get("parent_policy_anchor")
                actual_anchor = model_parent_anchor_contract(loaded.model)
                requested_temperature = experiment.get("masked_temperature")
                actual_temperature = model_temperature_contract(loaded.model)
                if actual_temperature != requested_temperature and (source or actual_temperature is not None):
                    raise ValueError("resume_temperature_contract_mismatch")
                if actual_anchor != requested_anchor and (source or actual_anchor is not None):
                    raise ValueError("resume_parent_anchor_contract_mismatch")
                if requested_anchor is not None and encoder.catalog_fingerprint != requested_anchor["catalog_fingerprint"]:
                    raise ValueError("parent_anchor_encoder_mismatch")
                if actual_regularizer != requested_regularizer and (
                        source or actual_regularizer is not None or requested_regularizer is None):
                    raise ValueError("resume_regularizer_contract_mismatch")
                # Enabling a new objective from an explicitly declared legacy parent
                # preserves compatible tensors AND Adam, never a mid-rollout claim.
                algorithm = (TemperatureFoundationPPO if requested_temperature is not None
                    else ParentAnchoredFoundationPPO if requested_anchor is not None
                    else type(loaded.model) if encoder.version in (*COMBAT_V5_VERSIONS, STRATEGIC_COMBAT_V5)
                    else RegularizedMaskablePPO if requested_regularizer else type(loaded.model))
                model = (
                    loaded.model
                    if device == "cpu" and loaded.model.n_envs == vector.num_envs and actual_regularizer == requested_regularizer and actual_anchor == requested_anchor and actual_temperature == requested_temperature
                    else algorithm.load(initial_source, env=vector, device=device,
                                        **({"zero_avoiding_beta": requested_regularizer["beta"]}
                                           if requested_regularizer else {}),
                                        **({"masked_temperature": requested_temperature} if requested_temperature is not None else {}),
                                        **({"parent_policy_anchor": requested_anchor,
                                            "parent_reference_path": experiment["initial_model"],
                                            "parent_catalog_path": str(catalog)} if requested_anchor is not None else {}))
                )
                if model_regularizer_contract(model) != requested_regularizer:
                    raise ValueError("training_regularizer_restore_failed")
                if model_parent_anchor_contract(model) != requested_anchor:
                    raise ValueError("training_parent_anchor_restore_failed")
                if model_temperature_contract(model) != requested_temperature:
                    raise ValueError("training_temperature_restore_failed")
                if requested_set is not None and actual_set is None:
                    from advisor.learned_legal_set_context import extend_foundation_legal_set_context
                    model = extend_foundation_legal_set_context(model)
                if requested_temperature is not None:
                    if model.temperature_trained != state["experiment_steps"]:
                        raise ValueError("temperature_trained_checkpoint_accounting_mismatch")
                    model.set_temperature_audit_directory(output / "temperature_audit")
                if requested_anchor is not None:
                    model.parent_reference_proof()
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
                algorithm = FoundationCombatPPO if "combat_foundation" in experiment else StrategicCombatV5PPO if encoder.version == STRATEGIC_COMBAT_V5 else IntegratedCombatV5PPO if encoder.version in COMBAT_V5_VERSIONS else RegularizedMaskablePPO if "zero_avoiding_beta" in experiment else MaskablePPO
                model = algorithm(
                    FoundationCombatPolicy
                    if "combat_foundation" in experiment
                    else StrategicCombatV5Policy
                    if encoder.version == STRATEGIC_COMBAT_V5
                    else IntegratedCombatV5Policy
                    if encoder.version in COMBAT_V5_VERSIONS
                    else PublicHistorySequencePolicy
                    if encoder.version in HISTORY_VERSIONS
                    else OwnExactHPCategoricalPolicy
                    if encoder.version in HP_VERSIONS
                    else StrategicPublicCategoricalPolicy
                    if encoder.version == "showdown-public-categorical-observation-v4"
                    else PublicCategoricalPolicy
                    if encoder.version in PUBLIC_CATEGORICAL_VERSIONS
                    else OwnMoveTokenPolicy
                    if encoder.version in OWN_MOVE_VERSIONS
                    else PublicInteractionPolicy
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
                    gamma=experiment_objective(experiment, encoder.version)["gamma"],
                    gae_lambda=experiment_objective(experiment, encoder.version)["gae_lambda"],
                    learning_rate=experiment.get("learning_rate", 1e-4),
                    ent_coef=experiment.get("ent_coef", 0.005),
                    target_kl=0.03,
                    seed=seed,
                    device=device,
                    verbose=0,
                    **({"zero_avoiding_beta": experiment["zero_avoiding_beta"]}
                       if "zero_avoiding_beta" in experiment else {}),
                    policy_kwargs={}
                    if encoder.version
                    in {
                        VERSION,
                        "showdown-learned-observation-v3",
                        "showdown-learned-observation-v4",
                        *OWN_MOVE_VERSIONS,
                        *PUBLIC_CATEGORICAL_VERSIONS,
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
                transfer_source = LearnedPolicy(experiment["transfer_model"], catalog,
                    expected_model_id=experiment.get("transfer_model_id"))
                if encoder.version in PUBLIC_CATEGORICAL_VERSIONS:
                    if "combat_foundation" in experiment:
                        transfer_foundation_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif encoder.version == STRATEGIC_COMBAT_V5:
                        transfer_strategic_combat_v5_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif encoder.version in COMBAT_V5_VERSIONS:
                        if transfer_source.encoder.version in COMBAT_V5_VERSIONS:
                            transfer_combat_v5_appearance_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                        else:
                            transfer_combat_v5_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif encoder.version in HISTORY_VERSIONS:
                        transfer_history_sequence_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif encoder.version in HP_VERSIONS:
                        transfer_own_hp_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif encoder.version == "showdown-public-categorical-observation-v4":
                        transfer_strategic_public_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif (encoder.version == "showdown-public-categorical-observation-v3"
                            and transfer_source.encoder.version == "showdown-public-categorical-observation-v2"):
                        from advisor.learned_public_categories_policy import transfer_runtime_ability_weights
                        transfer_runtime_ability_weights(model.policy, transfer_source.model.policy, encoder, transfer_source.encoder)
                    elif transfer_source.encoder.version not in {
                        "showdown-learned-observation-v3", "showdown-learned-observation-v4",
                    }:
                        raise ValueError("v3_or_v4_transfer_source_required")
                    else:
                        transfer_public_categorical_weights(model.policy, transfer_source.model.policy)
                elif encoder.version in OWN_MOVE_VERSIONS:
                    if transfer_source.encoder.version != "showdown-learned-observation-v3":
                        raise ValueError("v3_transfer_source_required")
                    transfer_v3_to_own_move(model.policy, transfer_source.model.policy)
                elif encoder.version == "showdown-learned-observation-v4":
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
                        "training_config_fingerprint": fingerprint,
                        "operations_version": OPERATIONS_VERSION,
                        "training_accounting_version": ACCOUNTING_VERSION,
                        **({"retry_monitor_version": retry_version} if retry_version == PROGRESS_RETRY_VERSION else {}),
                        **({"public_failure_opponent_source_sha256": {
                            name: sha256((Path(__file__).resolve().parents[1] / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                            for name in ("advisor/learned_failure_opponent.py", "advisor/learned_public_metrics.py")}}
                           if "public_failure_aware_v1" in experiment.get("opponents", []) else {}),
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
                        **({"legal_set_training": experiment["legal_set_training"],
                            "legal_set_optimizer": "old_named_states_preserved_new_residual_empty_at_transfer"}
                           if "legal_set_training" in experiment else {}),
                        "weight_transfer_source_sha256": transfer_id,
                        "initial_value_transfer_scope": "source_value_initialization_no_functional_objective_conversion"
                        if transfer_id else None,
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
                        "action_selection": {
                            "training": "upstream_maskable_ppo_stochastic",
                            "evaluation": "learned_masked_argmax_and_seeded_public_baselines",
                            "preview": "coordinator_seeded_random_ordered_three_of_six"
                            if not config.get("training_subset") else subset_identity["selection_mode"],
                        },
                        **({"training_subset_identity": subset_identity} if subset_identity else {}),
                        "ppo_update_contract": {"n_steps": model.n_steps, "batch_size": model.batch_size,
                            "n_epochs": model.n_epochs, "n_envs": model.n_envs,
                            "target_kl": model.target_kl,
                            "lr_schedule": "existing_constant_learning_rate",
                            "validation_selection_mode": config.get("validation_selection_mode", "best_and_plateau")},
                        "native_max_decisions": config.get("max_decisions", 256),
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
                episode_cursors = vector.env_method("episode_cursor")
                atomic_json(directory / "episodes.json", {
                    "schema_version": "showdown-training-episode-audit-v1",
                    "scope": "coordinator_only_inputs_not_policy_features_or_exact_rollout_replay",
                    "source_checkpoint": state.get("latest"), "endpoint_checkpoint_sha256": restored.model_id,
                    "checkpoint_binding": "training_interval_endpoint_not_each_step_policy_identity",
                    "episodes": episodes, "pending": episode_cursors,
                })
                if config.get("collect_opponent_selections", False):
                    atomic_json(directory / "opponent_selections.json", {
                        "scope": "coordinator_episode_start_receipts_not_policy_inputs",
                        "receipts": [r for worker in vector.env_method("drain_opponent_selections") for r in worker],
                        "schedule": experiment.get("opponent_schedule"),
                        "completed_trained_transitions": state["experiment_steps"],
                    })
                retry_records = [row for worker in vector.env_method("drain_retry_diagnostics") for row in worker]
                atomic_json(directory / "public_retry_diagnostics.json", {
                    "scope": "coordinator_only_owner_visible_requests_no_private_truth_or_native_error_cause",
                    "records": retry_records,
                })
                alerts = retry_monitor.inspect(retry_records, episodes, details.get("collected_transitions", 0),
                    **({"progress": episode_cursors} if retry_version == PROGRESS_RETRY_VERSION else {}))
                state["retry_monitor_pending"] = retry_monitor.pending
                atomic_json(directory / "operational_monitor.json", {"schema_version": OPERATIONS_VERSION,
                    "alerts": alerts, "retry_monitor_pending": retry_monitor.pending,
                    **({"retry_monitor_version": retry_version,
                        "episode_retry_statistics": retry_monitor.statistics()}
                       if retry_version == PROGRESS_RETRY_VERSION else {})})
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
                state["latest_model_sha256"] = restored.model_id
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
                behavior = Counter(state.get("public_behavior_counts", {}))
                interval_behavior = Counter()
                for counts in vector.env_method("drain_public_behavior_counts"):
                    behavior.update(counts)
                    interval_behavior.update(counts)
                state["public_behavior_counts"] = dict(behavior)
                atomic_json(directory / "public_behavior_metrics.json", {
                    "scope": "coordinator_only_public_opportunity_selection_and_execution_not_optimality",
                    "counts": dict(interval_behavior),
                })
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
                journal.publish(state)
                if alerts:
                    (output / "STOP").touch()
                notify("checkpoint_committed", checkpoint=path, operational_alerts=alerts)
                if budget.stopping():
                    return False
                if not checkpoint_validation_enabled(config):
                    return True
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
                        case_provider=validation_provider,
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
                if config.get("validation_selection_mode", "best_and_plateau") == "best_and_plateau" and not summary["truncated"] and score > state["best_score"]:
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
                if not experiment.get("offline") or experiment.get("record_initial_checkpoint", False):
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
                if config.get("collect_opponent_selections", False):
                    from advisor.learned_opponent_curriculum import next_boundary
                    chunk = next_boundary(experiment.get("opponent_schedule"), state["experiment_steps"], chunk)
                    vector.env_method("set_opponent_schedule_cursor", state["experiment_steps"])
                torch.set_num_threads(config.get("cpu_threads", 1))
                notify("running", resources=job.usage())

                def live_progress(current):
                    pending = sum(vector.env_method("pending_completed_count"))
                    notify(
                        "running",
                        transitions=state["transitions"] + current - steps_before,
                        completed_battles=state["completed_battles"] + pending,
                        resources=job.usage(),
                        observed_trained_rollout_transitions=state["trained_rollout_transitions"] + callback.completed_rollouts.transitions,
                        optimizer_steps=optimizer_steps(model),
                    )

                if config.get("collect_learning_signal_joins", False):
                    from advisor.learned_signal_recorder import PublicSignalRecorder
                    if config.get("ppo_update_audit"):
                        from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
                        signal_recorder = AuditedSignalRecorder(output / "public_signal_joins", encoder)
                    else:
                        signal_recorder = PublicSignalRecorder(output / "public_signal_joins", encoder)
                else:
                    signal_recorder = None
                callback = BudgetCallback(budget, live_progress,
                    collect_diagnostics=config.get("collect_rollout_diagnostics", False),
                    signal_recorder=signal_recorder)
                try:
                    model.learn(total_timesteps=chunk, reset_num_timesteps=False, callback=callback)
                finally:
                    if signal_recorder is not None and hasattr(signal_recorder, "close"):
                        signal_recorder.close()
                taken = model.num_timesteps - steps_before
                state["transitions"] += taken
                trained = callback.completed_rollouts.transitions
                if not 0 <= trained <= taken:
                    raise ValueError("invalid_completed_rollout_accounting")
                state["experiment_steps"] += (trained if config.get("transition_budget_scope") == "trained_rollouts_v1" else taken)
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
                    "partial_rollout_discarded_on_resume": taken != trained,
                    "untrained_collected_transitions": taken - trained,
                    "training_accounting_version": ACCOUNTING_VERSION,
                    "transition_budget_scope": config.get("transition_budget_scope", "legacy_collected_v1"),
                }
                metrics["ppo"] = {
                    k: float(v)
                    for k, v in model.logger.name_to_value.items()
                    if k.startswith(("train/", "foundation/"))
                    and isinstance(v, (float, int, np.floating))
                    and np.isfinite(v)
                }
                if config.get("collect_rollout_diagnostics", False):
                    metrics["public_rollout_diagnostics"] = callback.measurements
                if isinstance(model, FoundationCombatPPO):
                    metrics["foundation_environment"] = vector.env_method("drain_foundation_profile")
                    metrics["foundation_updates"] = getattr(model, "foundation_profile_rows", [])
                    model.foundation_profile_rows = []
                if completed and delta <= 0:
                    raise AssertionError("optimizer_did_not_change_parameters")
                checkpoint("ppo", metrics)
                if config.get("validation_selection_mode", "best_and_plateau") == "best_and_plateau" and state.get("plateau", 0) >= config.get("plateau_patience", 4):
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
        journal.publish(state)
        notify("launch_end", status=state["status"])
        return state
    except BaseException as error:
        execution_failed = True
        if journal is not None:
            try:
                journal.append("launch_failed", error=type(error).__name__, message=str(error))
            except OSError:
                pass
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
        try:
            if vector is not None:
                try:
                    from scripts.collect_showdown_public_trajectories import close_owned_vector
                    close_owned_vector(vector, failed=execution_failed)
                except (EOFError, BrokenPipeError, OSError) as cleanup_error:
                    # A crashed owned child must not mask the original failure
                    # or prevent timer/lock cleanup. No unrelated process access.
                    atomic_json(output / "worker_cleanup_error.json", {"error": type(cleanup_error).__name__, "message": str(cleanup_error)})
                    for process in getattr(vector, "processes", []):
                        if process.is_alive():
                            process.terminate()
                        process.join(timeout=1)
        finally:
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
