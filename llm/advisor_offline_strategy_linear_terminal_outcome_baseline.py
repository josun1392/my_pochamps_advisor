"""Offline observational ridge baseline for the approved terminal target."""
from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_train_only_numeric_encoding import validates_detached_encoded_feature_record


MODEL_SCHEMA = "offline-strategy-linear-terminal-outcome-baseline-v1"
PREDICTION_SCHEMA = "offline-strategy-linear-terminal-outcome-prediction-v1"
MODEL_FAMILY = "l2_regularized_linear_least_squares"
POLICY_VERSION = "train-only-centered-dual-ridge-v1"
L2_PENALTY = 1.0
LIMITATIONS = (
    "observational_terminal_outcome_prediction_not_causal_action_value",
    "not_q_value_or_advantage_or_counterfactual_reward",
    "not_calibrated_win_probability_or_recommendation_score",
    "predictive_strategy_feature_join_not_proven",
    "detached_live_source_retention_not_independently_reproven",
)


def fit_offline_linear_terminal_outcome_baseline(
    records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    """Fit one fixed-penalty ridge model from usable train rows only.

    The intercept is unpenalized. A centered dual solve uses an n-by-n system,
    with n equal to the admitted training count; no random state is involved.
    """
    if not isinstance(records, (list, tuple)) or not records:
        return _model_failure("encoded_records_invalid")
    if any(not validates_detached_encoded_feature_record(row) for row in records):
        return _model_failure("encoded_record_invalid")
    ids = [row["encoded_record_id"] for row in records]
    if len(ids) != len(set(ids)):
        return _model_failure("duplicate_encoded_record_id")
    if len({row["encoder_id"] for row in records}) != 1:
        return _model_failure("mixed_encoder_id")
    if len({row["audit"]["evaluation_split_id"] for row in records}) != 1:
        return _model_failure("mixed_evaluation_split_id")
    if len({row["vector_dimension"] for row in records}) != 1:
        return _model_failure("mixed_vector_dimension")
    train = sorted((row for row in records if row["evaluation_partition"] == "train"
                    and row["feature_availability"]["availability"] == "available"
                    and row["label"]["availability"] == "available"),
                   key=lambda row: (row["vector"], row["label"]["value"]))
    if not train:
        return _model_failure("no_usable_train_record")
    dimension = train[0]["vector_dimension"]
    try:
        vectors = [tuple(float(value) for value in row["vector"]) for row in train]
        if any(not math.isfinite(value) for vector in vectors for value in vector):
            return _model_failure("nonfinite_train_vector")
        labels = [float(row["label"]["value"]) for row in train]
        count = len(train)
        means = tuple(math.fsum(vector[j] for vector in vectors) / count for j in range(dimension))
        if any(not math.isfinite(mean) for mean in means):
            return _model_failure("nonfinite_train_preprocessing")
        variances = tuple(math.fsum((vector[j] - means[j]) ** 2 for vector in vectors) / count
                          for j in range(dimension))
        scales = tuple(math.sqrt(variance) if variance > 0.0 else 1.0 for variance in variances)
        if any(not math.isfinite(scale) or scale <= 0.0 for scale in scales):
            return _model_failure("nonfinite_train_preprocessing")
        standardized = [tuple((vector[j] - means[j]) / scales[j] for j in range(dimension))
                        for vector in vectors]
        mean_label = math.fsum(labels) / count
        rhs = [label - mean_label for label in labels]
        gram = [[math.fsum(standardized[i][j] * standardized[k][j] for j in range(dimension))
                 + (L2_PENALTY if i == k else 0.0) for k in range(count)] for i in range(count)]
        dual = _solve_positive_definite(gram, rhs)
        coefficients = tuple(math.fsum(standardized[i][j] * dual[i] for i in range(count))
                             for j in range(dimension))
        intercept = mean_label
        if not all(math.isfinite(value) for value in (*coefficients, intercept)):
            return _model_failure("nonfinite_fitted_model")
    except (OverflowError, ValueError, ZeroDivisionError):
        return _model_failure("numerical_fit_failed")
    train_fingerprint = fingerprint_decision_contract_reference(tuple(
        (row["vector"], row["label"]["value"]) for row in train
    ))
    model_data = {
        "schema_version": MODEL_SCHEMA, "model_family": MODEL_FAMILY,
        "model_policy_version": POLICY_VERSION, "encoder_id": train[0]["encoder_id"],
        "evaluation_split_id": train[0]["audit"]["evaluation_split_id"],
        "vector_dimension": dimension, "training_example_count": count,
        "hyperparameters": {"l2_penalty": L2_PENALTY, "intercept_penalized": False,
                            "solver": "centered_dual_gaussian_elimination_partial_pivot"},
        "preprocessing": {"coordinate_means": means, "coordinate_scales": scales,
                          "zero_variance_scale": 1.0, "statistics_source": "usable_train_rows_only"},
        "intercept": intercept, "coefficients": coefficients,
        "train_data_fingerprint": train_fingerprint, "limitations": LIMITATIONS,
    }
    # Split identity is retained for prediction binding, but a held-out change
    # can alter that audit ID without changing the training examples.
    model_identity = {key: item for key, item in model_data.items() if key != "evaluation_split_id"}
    return _freeze({"status": "fitted", "model_id": "offline-linear-terminal-baseline:"
                    + fingerprint_decision_contract_reference(model_identity), **model_data})


def predict_offline_terminal_outcome(*, model: Mapping[str, Any], encoded_record: Mapping[str, Any]) -> Mapping[str, Any]:
    """Predict from the vector alone; labels and partition are audit metadata."""
    if not _valid_model(model):
        return _prediction_failure("model_invalid")
    if not validates_detached_encoded_feature_record(encoded_record):
        return _prediction_failure("encoded_record_invalid")
    if encoded_record["encoder_id"] != model["encoder_id"]:
        return _prediction_failure("encoder_mismatch")
    if encoded_record["audit"]["evaluation_split_id"] != model["evaluation_split_id"]:
        return _prediction_failure("evaluation_split_mismatch")
    if encoded_record["vector_dimension"] != model["vector_dimension"]:
        return _prediction_failure("vector_dimension_mismatch")
    if encoded_record["feature_availability"]["availability"] != "available":
        return _prediction_failure("feature_unavailable")
    vector = encoded_record["vector"]
    means = model["preprocessing"]["coordinate_means"]
    scales = model["preprocessing"]["coordinate_scales"]
    try:
        prediction = model["intercept"] + math.fsum(
            model["coefficients"][j] * ((vector[j] - means[j]) / scales[j])
            for j in range(model["vector_dimension"])
        )
    except (OverflowError, ValueError, ZeroDivisionError):
        return _prediction_failure("nonfinite_prediction")
    if not math.isfinite(prediction):
        return _prediction_failure("nonfinite_prediction")
    return _freeze({
        "status": "predicted", "schema_version": PREDICTION_SCHEMA,
        "prediction_id": "offline-linear-terminal-prediction:" + fingerprint_decision_contract_reference({
            "model_id": model["model_id"], "vector": vector,
        }),
        "model_id": model["model_id"], "encoded_record_id": encoded_record["encoded_record_id"],
        "evaluation_partition": encoded_record["evaluation_partition"],
        "predicted_terminal_target": prediction,
        "prediction_semantics": "observational_terminal_outcome_target_estimate",
        "limitations": LIMITATIONS,
    })


def _solve_positive_definite(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Deterministic partial-pivot elimination for the ridge-positive system."""
    n = len(rhs)
    a = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if not math.isfinite(a[pivot][col]) or abs(a[pivot][col]) <= 1e-14:
            raise ValueError("singular_ridge_system")
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        for row in range(col + 1, n):
            factor = a[row][col] / divisor
            a[row][col] = 0.0
            for k in range(col + 1, n + 1):
                a[row][k] -= factor * a[col][k]
    solution = [0.0] * n
    for row in range(n - 1, -1, -1):
        solution[row] = (a[row][n] - math.fsum(a[row][k] * solution[k] for k in range(row + 1, n))) / a[row][row]
    if any(not math.isfinite(value) for value in solution):
        raise ValueError("nonfinite_solver_result")
    return solution


def _valid_model(value: Any) -> bool:
    if (not isinstance(value, MappingProxyType) or set(value) != {
        "status", "model_id", "schema_version", "model_family", "model_policy_version", "encoder_id",
        "evaluation_split_id", "vector_dimension", "training_example_count", "hyperparameters",
        "preprocessing", "intercept", "coefficients", "train_data_fingerprint", "limitations",
    } or value["status"] != "fitted" or value["schema_version"] != MODEL_SCHEMA
            or value["model_family"] != MODEL_FAMILY or value["model_policy_version"] != POLICY_VERSION
            or value["limitations"] != LIMITATIONS or type(value["vector_dimension"]) is not int
            or value["vector_dimension"] < 1 or type(value["training_example_count"]) is not int
            or value["training_example_count"] < 1):
        return False
    hp = value["hyperparameters"]
    prep = value["preprocessing"]
    dimension = value["vector_dimension"]
    if (not isinstance(hp, MappingProxyType) or hp != {
        "l2_penalty": L2_PENALTY, "intercept_penalized": False,
        "solver": "centered_dual_gaussian_elimination_partial_pivot",
    } or not isinstance(prep, MappingProxyType) or set(prep) != {
        "coordinate_means", "coordinate_scales", "zero_variance_scale", "statistics_source",
    } or prep["zero_variance_scale"] != 1.0 or prep["statistics_source"] != "usable_train_rows_only"
            or any(not isinstance(value[key], str) or not value[key] for key in (
                "encoder_id", "evaluation_split_id", "train_data_fingerprint",
            ))):
        return False
    means, scales, coefficients = prep["coordinate_means"], prep["coordinate_scales"], value["coefficients"]
    if (not all(isinstance(items, tuple) and len(items) == dimension for items in (means, scales, coefficients))
            or any(type(item) is not float or not math.isfinite(item) for items in (means, scales, coefficients)
                   for item in items) or any(scale <= 0.0 for scale in scales)
            or type(value["intercept"]) is not float or not math.isfinite(value["intercept"])):
        return False
    model_data = {key: item for key, item in value.items() if key not in {"status", "model_id", "evaluation_split_id"}}
    return value["model_id"] == "offline-linear-terminal-baseline:" + fingerprint_decision_contract_reference(model_data)


def _model_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": MODEL_SCHEMA, "reason": reason})


def _prediction_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": PREDICTION_SCHEMA, "reason": reason})
