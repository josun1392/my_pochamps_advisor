"""Frozen partitioned regression report for an observational outcome model."""
from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_linear_terminal_outcome_baseline import (
    predict_offline_terminal_outcome, validates_detached_linear_terminal_outcome_model,
)
from llm.advisor_offline_strategy_train_only_numeric_encoding import validates_detached_encoded_feature_record


SCHEMA_VERSION = "offline-strategy-linear-terminal-outcome-evaluation-v1"
POLICY_VERSION = "frozen-partitioned-mse-mae-train-mean-reference-v1"
PARTITIONS = ("train", "validation", "test")
LIMITATIONS = (
    "observational_terminal_outcome_prediction_not_causal_action_value",
    "not_q_value_or_advantage",
    "not_calibrated_win_probability",
    "no_counterfactual_action_evaluation",
    "predictive_strategy_feature_join_not_proven",
    "detached_live_source_retention_not_independently_reproven",
)


def materialize_offline_linear_terminal_outcome_evaluation(
    *, model: Mapping[str, Any], encoded_records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    """Evaluate one already-fitted model; no fit, tuning, or selection occurs."""
    if not validates_detached_linear_terminal_outcome_model(model):
        return _failure("model_invalid")
    if not isinstance(encoded_records, (list, tuple)):
        return _failure("encoded_records_invalid")
    if any(not validates_detached_encoded_feature_record(row) for row in encoded_records):
        return _failure("encoded_record_invalid")
    ids = [row["encoded_record_id"] for row in encoded_records]
    if len(ids) != len(set(ids)):
        return _failure("duplicate_encoded_record_id")
    if any(row["encoder_id"] != model["encoder_id"] for row in encoded_records):
        return _failure("encoder_mismatch")
    if any(row["audit"]["evaluation_split_id"] != model["evaluation_split_id"] for row in encoded_records):
        return _failure("evaluation_split_mismatch")
    if any(row["vector_dimension"] != model["vector_dimension"] for row in encoded_records):
        return _failure("vector_dimension_mismatch")

    ordered = sorted(encoded_records, key=lambda row: row["encoded_record_id"])
    per_record = []
    grouped: dict[str, list[dict[str, Any]]] = {partition: [] for partition in PARTITIONS}
    counts = {partition: {"total": 0, "feature_unavailable": 0, "label_unavailable": 0}
              for partition in PARTITIONS}
    reference = model["intercept"]  # frozen train target mean, never held-out labels
    for row in ordered:
        partition = row["evaluation_partition"]
        counts[partition]["total"] += 1
        if row["feature_availability"]["availability"] != "available":
            counts[partition]["feature_unavailable"] += 1
            continue
        if row["label"]["availability"] != "available":
            counts[partition]["label_unavailable"] += 1
            continue
        prediction = predict_offline_terminal_outcome(model=model, encoded_record=row)
        if prediction.get("status") != "predicted":
            return _failure("frozen_prediction_failed")
        target = row["label"]["value"]
        estimate = prediction["predicted_terminal_target"]
        try:
            squared = (estimate - target) ** 2
            absolute = abs(estimate - target)
            reference_squared = (reference - target) ** 2
            reference_absolute = abs(reference - target)
        except OverflowError:
            return _failure("nonfinite_evaluation_error")
        if not all(math.isfinite(value) for value in (squared, absolute, reference_squared, reference_absolute)):
            return _failure("nonfinite_evaluation_error")
        audit_row = {
            "encoded_record_id": row["encoded_record_id"], "partition": partition,
            "factual_target": target, "model_prediction": estimate,
            "train_mean_reference_prediction": reference,
            "squared_error": squared, "absolute_error": absolute,
            "reference_squared_error": reference_squared,
            "reference_absolute_error": reference_absolute,
        }
        grouped[partition].append(audit_row)
        per_record.append(audit_row)

    partitions = {}
    for partition in PARTITIONS:
        rows = grouped[partition]
        total = counts[partition]["total"]
        eligible = len(rows)
        if eligible:
            try:
                mse = math.fsum(row["squared_error"] for row in rows) / eligible
                mae = math.fsum(row["absolute_error"] for row in rows) / eligible
                reference_mse = math.fsum(row["reference_squared_error"] for row in rows) / eligible
                reference_mae = math.fsum(row["reference_absolute_error"] for row in rows) / eligible
            except OverflowError:
                return _failure("nonfinite_partition_metric")
            metrics = {
                "availability": "available", "example_count": eligible,
                "mean_squared_error": mse, "mean_absolute_error": mae,
                "reference_mean_squared_error": reference_mse,
                "reference_mean_absolute_error": reference_mae,
                "mse_delta_vs_train_mean_reference": reference_mse - mse,
                "mae_delta_vs_train_mean_reference": reference_mae - mae,
            }
            if any(not math.isfinite(value) for value in metrics.values() if type(value) is float):
                return _failure("nonfinite_partition_metric")
        else:
            metrics = {"availability": "unavailable", "reason": "no_metric_eligible_records"}
        partitions[partition] = {
            "total_record_count": total, "metric_eligible_record_count": eligible,
            "excluded_record_count": total - eligible,
            "exclusion_counts": {
                "feature_unavailable": counts[partition]["feature_unavailable"],
                "label_unavailable": counts[partition]["label_unavailable"],
            },
            "metrics": metrics,
        }
    identity = {
        "schema_version": SCHEMA_VERSION, "policy_version": POLICY_VERSION,
        "model_id": model["model_id"], "evaluation_split_id": model["evaluation_split_id"],
        "admitted_record_ids": tuple(sorted(ids)),
        "partitions": partitions, "per_record_evaluations": tuple(per_record),
    }
    return _freeze({
        "status": "materialized", "schema_version": SCHEMA_VERSION,
        "evaluation_id": "offline-linear-terminal-evaluation:" + fingerprint_decision_contract_reference(identity),
        "evaluation_policy_version": POLICY_VERSION,
        "model_id": model["model_id"], "encoder_id": model["encoder_id"],
        "evaluation_split_id": model["evaluation_split_id"],
        "train_mean_reference_prediction": reference,
        "record_count": len(ordered), "partitions": partitions,
        "per_record_evaluations": tuple(per_record), "limitations": LIMITATIONS,
    })


def _failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
