"""Versioned sparse terminal-return objective; never a win-probability contract."""
import math
from hashlib import sha256
from pathlib import Path

CATEGORICAL = "showdown-public-categorical-observation-v1"
CATEGORICAL_VERSIONS = (CATEGORICAL, "showdown-public-categorical-observation-v2", "showdown-public-categorical-observation-v3")
UNDISCOUNTED = "native_terminal_win_loss_draw_undiscounted_v1"
DISCOUNTED = "native_terminal_win_loss_draw_discounted_v1"


def categorical_learning_source_identity():
    root = Path(__file__).resolve().parents[1]
    names = [
        "advisor/learned_objective.py", "advisor/learned_public_categories.py",
        "advisor/learned_own_identity.py",
        "advisor/learned_public_categories_policy.py", "advisor/learned_action_policy.py",
        "advisor/learned_action_encoder.py", "advisor/learned_public_interactions.py",
        "advisor/learned_tactics_encoder.py", "advisor/learned_encoder.py",
        "advisor/learned_gym.py", "advisor/learned_parallel.py",
        "scripts/train_showdown_autonomous.py", "scripts/evaluate_showdown_policy.py",
        "scripts/build_showdown_runtime_categories.py", "tools/showdown_bridge/runtime-abilities.cjs",
        "models/showdown_public_categories_v3/catalog.json",
    ]
    return {name: sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in names}


def objective_contract(gamma, gae_lambda):
    if (type(gamma) not in (int, float) or gamma not in (0.99, 1.0)
            or type(gae_lambda) not in (int, float) or not math.isfinite(gae_lambda)
            or not 0 <= gae_lambda <= 1):
        raise ValueError("unsupported_terminal_learning_objective")
    return {
        "schema_version": "showdown-terminal-learning-objective-v1",
        "objective_id": UNDISCOUNTED if gamma == 1 else DISCOUNTED,
        "gamma": float(gamma), "gae_lambda": float(gae_lambda),
        "reward": "native_sparse_terminal_win_loss_draw",
        "duration_preference": "none" if gamma == 1 else "discounted_future_terminal_reward",
        "time_limit": "future_rollout_sb3_bootstrap_public_continuation_v1_not_native_draw_or_loss",
        "historical_rollout_scope": "not_reinterpreted_by_this_contract",
        "step_scope": "agent_decisions_with_native_wait_autoadvance",
        "value_scope": "learned_expected_return_not_exact_win_probability_or_mechanics_truth",
    }


def experiment_objective(experiment, encoder_version):
    contract = objective_contract(experiment.get("gamma", 0.99), experiment.get("gae_lambda", 0.95))
    if contract["gamma"] == 1 and encoder_version not in CATEGORICAL_VERSIONS:
        raise ValueError("gamma_one_requires_new_public_categorical_experiment")
    if experiment.get("objective", contract["objective_id"]) != contract["objective_id"]:
        raise ValueError("experiment_gamma_objective_mismatch")
    return contract


def require_resume_objective(model, experiment, encoder_version):
    requested = experiment_objective(experiment, encoder_version)
    actual = objective_contract(model.gamma, model.gae_lambda)
    if actual != requested:
        raise ValueError("checkpoint_objective_mismatch_no_silent_gamma_or_gae_mutation")
    return actual
