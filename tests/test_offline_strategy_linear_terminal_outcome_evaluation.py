"""Frozen partitioned MSE/MAE versus the train-mean constant reference."""
from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_strategy_linear_terminal_outcome_baseline import (
    fit_offline_linear_terminal_outcome_baseline as fit,
    predict_offline_terminal_outcome as predict,
)
from llm.advisor_offline_strategy_linear_terminal_outcome_evaluation import (
    materialize_offline_linear_terminal_outcome_evaluation as evaluate,
)
from llm.advisor_offline_strategy_train_only_numeric_encoding import validates_detached_encoded_feature_record
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_linear_terminal_outcome_baseline import base, variant


def example_rows():
    _, template = base()
    train = []
    for x, label in ((0, -1), (1, 0), (2, 1)):
        vector = list(template["vector"])
        vector[0] = x
        train.append(variant(template, vector=vector, label=label, suffix=f"train-{x}"))
    model = fit(train)
    assert model["status"] == "fitted", model
    validation = variant(train[0], partition="validation", suffix="validation")
    test = variant(train[2], partition="test", suffix="test")
    return model, train, validation, test


def metric(report, partition, name):
    return report["partitions"][partition]["metrics"][name]


def test_frozen_train_validation_test_metrics_and_reference_formulas():
    model, train, validation, test = example_rows()
    report = evaluate(model=model, encoded_records=[*train, validation, test])
    assert report["status"] == "materialized", report
    assert report["record_count"] == 5
    assert report["train_mean_reference_prediction"] == model["intercept"] == 0.0
    assert metric(report, "train", "example_count") == 3
    assert metric(report, "train", "mean_squared_error") == pytest.approx(1 / 24)
    assert metric(report, "train", "mean_absolute_error") == pytest.approx(1 / 6)
    assert metric(report, "train", "reference_mean_squared_error") == pytest.approx(2 / 3)
    assert metric(report, "train", "reference_mean_absolute_error") == pytest.approx(2 / 3)
    assert metric(report, "train", "mse_delta_vs_train_mean_reference") == pytest.approx(5 / 8)
    assert metric(report, "train", "mae_delta_vs_train_mean_reference") == pytest.approx(1 / 2)
    for partition in ("validation", "test"):
        assert metric(report, partition, "example_count") == 1
        assert metric(report, partition, "mean_squared_error") == pytest.approx(1 / 16)
        assert metric(report, partition, "mean_absolute_error") == pytest.approx(1 / 4)
        assert metric(report, partition, "reference_mean_squared_error") == 1.0
        assert metric(report, partition, "reference_mean_absolute_error") == 1.0
        assert metric(report, partition, "mse_delta_vs_train_mean_reference") == pytest.approx(15 / 16)
        assert metric(report, partition, "mae_delta_vs_train_mean_reference") == pytest.approx(3 / 4)
    assert tuple(row["encoded_record_id"] for row in report["per_record_evaluations"]) == tuple(
        sorted(row["encoded_record_id"] for row in [*train, validation, test]))
    for source in [*train, validation, test]:
        row = next(item for item in report["per_record_evaluations"]
                   if item["encoded_record_id"] == source["encoded_record_id"])
        standalone = predict(model=model, encoded_record=source)
        assert row["model_prediction"] == standalone["predicted_terminal_target"]
        assert row["train_mean_reference_prediction"] == model["intercept"]
        assert row["squared_error"] == pytest.approx((row["model_prediction"] - row["factual_target"]) ** 2)
        assert row["absolute_error"] == pytest.approx(abs(row["model_prediction"] - row["factual_target"]))
        assert row["reference_squared_error"] == pytest.approx((model["intercept"] - row["factual_target"]) ** 2)
        assert row["reference_absolute_error"] == pytest.approx(abs(model["intercept"] - row["factual_target"]))


def test_order_independence_and_deeply_read_only_report():
    model, train, validation, test = example_rows()
    rows = [*train, validation, test]
    original = deepcopy([_editable(row) for row in rows])
    first = evaluate(model=model, encoded_records=rows)
    second = evaluate(model=model, encoded_records=list(reversed(rows)))
    assert first == second and first["evaluation_id"] == second["evaluation_id"]
    assert [_editable(row) for row in rows] == original
    with pytest.raises(TypeError):
        first["partitions"]["test"]["metrics"]["mean_squared_error"] = 0.0
    assert "observational_terminal_outcome_prediction_not_causal_action_value" in first["limitations"]
    assert "no_counterfactual_action_evaluation" in first["limitations"]
    assert not {"accuracy", "auc", "f1", "threshold", "probability", "confidence", "q_value",
                "recommended_action", "selected_model", "tuned_l2"} & set(first)


def test_heldout_label_changes_only_that_partitions_errors():
    model, train, validation, test = example_rows()
    original_model = deepcopy(_editable(model))
    first = evaluate(model=model, encoded_records=[*train, validation, test])
    changed_validation = variant(validation, label=1, suffix="changed-validation")
    second = evaluate(model=model, encoded_records=[*train, changed_validation, test])
    assert metric(second, "validation", "mean_squared_error") != metric(first, "validation", "mean_squared_error")
    assert second["partitions"]["train"] == first["partitions"]["train"]
    assert second["partitions"]["test"] == first["partitions"]["test"]
    assert predict(model=model, encoded_record=changed_validation)["predicted_terminal_target"] == predict(
        model=model, encoded_record=validation)["predicted_terminal_target"]
    assert second["train_mean_reference_prediction"] == first["train_mean_reference_prediction"]
    changed_test = variant(test, label=-1, suffix="changed-test")
    third = evaluate(model=model, encoded_records=[*train, validation, changed_test])
    assert metric(third, "test", "mean_squared_error") != metric(first, "test", "mean_squared_error")
    assert third["partitions"]["validation"] == first["partitions"]["validation"]
    assert third["partitions"]["train"] == first["partitions"]["train"]
    assert predict(model=model, encoded_record=changed_test)["predicted_terminal_target"] == predict(
        model=model, encoded_record=test)["predicted_terminal_target"]
    assert third["train_mean_reference_prediction"] == first["train_mean_reference_prediction"]
    assert _editable(model) == original_model


def test_empty_partitions_and_all_empty_collection_are_explicit():
    model, train, _, _ = example_rows()
    report = evaluate(model=model, encoded_records=train)
    for partition in ("validation", "test"):
        assert report["partitions"][partition]["total_record_count"] == 0
        assert report["partitions"][partition]["metrics"] == {
            "availability": "unavailable", "reason": "no_metric_eligible_records"}
    empty = evaluate(model=model, encoded_records=[])
    assert empty["status"] == "materialized" and empty["record_count"] == 0
    assert all(empty["partitions"][partition]["metrics"]["availability"] == "unavailable"
               for partition in ("train", "validation", "test"))
    assert empty == evaluate(model=model, encoded_records=[])


def test_feature_and_label_unavailability_are_counted_without_fake_zero():
    model, train, validation, test = example_rows()
    no_feature = variant(validation, unavailable=True, suffix="no-feature")
    raw = _editable(test)
    raw["audit"]["semantic_feature_record_id"] += ":no-label"
    raw["label"] = {"availability": "unavailable", "reason": "label_not_observed"}
    from llm.advisor_offline_decision_point_provenance import fingerprint_decision_contract_reference
    raw["encoded_record_id"] = "encoded-semantic-feature:" + fingerprint_decision_contract_reference({
        "encoder_id": raw["encoder_id"], "feature_record_id": raw["audit"]["semantic_feature_record_id"],
        "vector": raw["vector"],
    })
    no_label = _freeze(raw)
    assert validates_detached_encoded_feature_record(no_label)
    report = evaluate(model=model, encoded_records=[*train, no_feature, no_label])
    assert report["partitions"]["validation"]["excluded_record_count"] == 1
    assert report["partitions"]["validation"]["exclusion_counts"]["feature_unavailable"] == 1
    assert report["partitions"]["test"]["excluded_record_count"] == 1
    assert report["partitions"]["test"]["exclusion_counts"]["label_unavailable"] == 1
    assert report["partitions"]["validation"]["metrics"]["availability"] == "unavailable"
    assert report["partitions"]["test"]["metrics"]["availability"] == "unavailable"
    assert len(report["per_record_evaluations"]) == 3


def test_duplicate_foreign_encoder_split_dimension_and_fabricated_model_reject():
    model, train, _, _ = example_rows()
    row = train[0]
    assert evaluate(model=model, encoded_records=[row, row])["reason"] == "duplicate_encoded_record_id"
    foreign_encoder = variant(row, encoder_id="train-only-numeric-encoder:foreign", suffix="foreign-encoder")
    assert evaluate(model=model, encoded_records=[row, foreign_encoder])["reason"] == "encoder_mismatch"
    foreign_split = variant(row, split_id="foreign-split", suffix="foreign-split")
    assert evaluate(model=model, encoded_records=[row, foreign_split])["reason"] == "evaluation_split_mismatch"
    longer = variant(row, vector=(*row["vector"], 0), suffix="longer")
    assert evaluate(model=model, encoded_records=[row, longer])["reason"] == "vector_dimension_mismatch"
    assert evaluate(model={**model}, encoded_records=train)["reason"] == "model_invalid"
    tampered = _editable(model)
    tampered["coefficients"][0] += 1.0
    assert evaluate(model=_freeze(tampered), encoded_records=train)["reason"] == "model_invalid"


def test_raw_linear_prediction_outside_target_range_is_not_clamped():
    model, train, _, _ = example_rows()
    vector = list(train[2]["vector"])
    vector[0] = 100
    far = variant(train[2], vector=vector, label=1, partition="test", suffix="far")
    report = evaluate(model=model, encoded_records=[*train, far])
    audit = next(row for row in report["per_record_evaluations"] if row["partition"] == "test")
    assert audit["model_prediction"] > 1.0
    assert audit["model_prediction"] == predict(model=model, encoded_record=far)["predicted_terminal_target"]
