"""Frozen train-only observational terminal-outcome ridge baseline."""
import math
from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_linear_terminal_outcome_baseline import (
    L2_PENALTY,
    fit_offline_linear_terminal_outcome_baseline as fit,
    predict_offline_terminal_outcome as predict,
)
from llm.advisor_offline_strategy_model_feature_semantics import materialize_offline_strategy_model_feature_semantics as semantic
from llm.advisor_offline_strategy_train_only_numeric_encoding import (
    encode_semantic_feature_record as encode,
    fit_train_only_numeric_encoder as fit_encoder,
    validates_detached_encoded_feature_record,
)
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_model_feature_semantics import case
from tests.test_offline_strategy_train_only_numeric_encoding import changed


def base():
    s = semantic(**case()[0])
    encoder = fit_encoder([s])
    row = encode(encoder=encoder, semantic_record=s)
    assert validates_detached_encoded_feature_record(row)
    return encoder, row


def variant(row, *, label=None, partition=None, vector=None, suffix="variant", encoder_id=None,
            split_id=None, unavailable=False):
    """Build a detached, self-consistent synthetic encoded test record."""
    raw = _editable(row)
    raw["audit"]["semantic_feature_record_id"] += ":" + suffix
    if label is not None:
        raw["label"] = {"availability": "available", "value": label,
                        "semantics": "terminal_outcome_self_perspective"}
    if partition is not None:
        raw["evaluation_partition"] = partition
    if vector is not None:
        raw["vector"] = list(vector)
        raw["vector_dimension"] = len(vector)
    if encoder_id is not None:
        raw["encoder_id"] = encoder_id
    if split_id is not None:
        raw["audit"]["evaluation_split_id"] = split_id
    if unavailable:
        raw["feature_availability"] = {"availability": "unavailable", "reason": "no_free_choice"}
        raw["source_semantic_feature_fingerprint"] = None
        raw["vector"] = None
    raw["encoded_record_id"] = "encoded-semantic-feature:" + fingerprint_decision_contract_reference({
        "encoder_id": raw["encoder_id"], "feature_record_id": raw["audit"]["semantic_feature_record_id"],
        "vector": raw["vector"],
    })
    result = _freeze(raw)
    assert validates_detached_encoded_feature_record(result)
    return result


def test_one_train_row_fits_finite_immutable_model_and_predicts():
    encoder, row = base()
    model = fit([row])
    assert model["status"] == "fitted", model
    assert model["training_example_count"] == 1
    assert model["vector_dimension"] == encoder["vector_dimension"]
    assert model["hyperparameters"]["l2_penalty"] == L2_PENALTY == 1.0
    assert model["hyperparameters"]["intercept_penalized"] is False
    assert model["preprocessing"]["statistics_source"] == "usable_train_rows_only"
    assert model["preprocessing"]["coordinate_means"] == tuple(float(x) for x in row["vector"])
    assert all(scale == 1.0 for scale in model["preprocessing"]["coordinate_scales"])
    assert all(coefficient == 0.0 for coefficient in model["coefficients"])
    assert model["intercept"] == 1.0
    result = predict(model=model, encoded_record=row)
    assert result["status"] == "predicted", result
    assert result["predicted_terminal_target"] == 1.0
    assert result["prediction_semantics"] == "observational_terminal_outcome_target_estimate"
    assert "observational_terminal_outcome_prediction_not_causal_action_value" in model["limitations"]
    assert "predictive_strategy_feature_join_not_proven" in model["limitations"]
    with pytest.raises(TypeError):
        model["coefficients"] = ()
    with pytest.raises(TypeError):
        result["predicted_terminal_target"] = 0.0


def test_synthetic_directional_ridge_solve_and_order_independence():
    _, template = base()
    rows = []
    for x, label in ((0, -1), (1, 0), (2, 1)):
        vector = list(template["vector"])
        vector[0] = x
        rows.append(variant(template, vector=vector, label=label, suffix=f"x-{x}"))
    model = fit(rows)
    assert model["status"] == "fitted", model
    assert model == fit(list(reversed(rows)))
    predictions = [predict(model=model, encoded_record=row)["predicted_terminal_target"] for row in rows]
    assert all(math.isfinite(value) for value in predictions)
    assert predictions[0] < predictions[1] < predictions[2]
    assert predictions[1] == pytest.approx(0.0, abs=1e-12)
    assert predictions[0] == pytest.approx(-0.75, abs=1e-12)
    assert predictions[2] == pytest.approx(0.75, abs=1e-12)


def test_heldout_rows_labels_and_features_never_change_fit_or_preprocessing():
    _, train = base()
    second_vector = list(train["vector"])
    second_vector[0] += 1
    second_train = variant(train, vector=second_vector, label=-1, suffix="second-train")
    original = fit([train, second_train])
    extreme = list(train["vector"])
    extreme[0] = 1000000
    validation = variant(train, partition="validation", vector=extreme, label=-1, suffix="validation")
    test = variant(train, partition="test", vector=extreme, label=0, suffix="test")
    combined = fit([test, second_train, train, validation])
    assert combined == original
    assert combined["model_id"] == original["model_id"]
    changed_validation = variant(validation, label=1, suffix="changed-validation")
    assert fit([train, second_train, changed_validation, test]) == original
    assert predict(model=original, encoded_record=validation)["status"] == "predicted"
    assert predict(model=original, encoded_record=test)["status"] == "predicted"
    assert model_prediction(original, validation) == model_prediction(original, test)


def model_prediction(model, row):
    return predict(model=model, encoded_record=row)["predicted_terminal_target"]


def test_train_label_or_feature_change_can_change_model_identity():
    _, train = base()
    original = fit([train])
    relabeled = variant(train, label=-1, suffix="new-train-label")
    assert fit([relabeled])["model_id"] != original["model_id"]
    vector = list(train["vector"])
    vector[0] += 1
    changed_feature = variant(train, vector=vector, suffix="new-train-feature")
    assert fit([changed_feature])["model_id"] != original["model_id"]


def test_split_audit_id_can_change_without_changing_fitted_model_identity():
    _, train = base()
    original = fit([train])
    same_training = variant(train, split_id="reissued-split-after-heldout-change", suffix="same-training")
    reissued = fit([same_training])
    assert reissued["model_id"] == original["model_id"]
    assert reissued["coefficients"] == original["coefficients"]
    assert reissued["evaluation_split_id"] == "reissued-split-after-heldout-change"


def test_unavailable_train_rows_are_audited_but_do_not_contribute():
    _, train = base()
    unavailable = variant(train, unavailable=True, suffix="unavailable")
    assert fit([train, unavailable]) == fit([train])
    assert fit([unavailable])["reason"] == "no_usable_train_record"
    assert predict(model=fit([train]), encoded_record=unavailable)["reason"] == "feature_unavailable"


def test_mixed_identity_dimension_and_duplicates_reject():
    _, train = base()
    assert fit([train, train])["reason"] == "duplicate_encoded_record_id"
    other_encoder = variant(train, encoder_id="train-only-numeric-encoder:foreign", suffix="other-encoder")
    assert fit([train, other_encoder])["reason"] == "mixed_encoder_id"
    other_split = variant(train, split_id="foreign-split", suffix="other-split")
    assert fit([train, other_split])["reason"] == "mixed_evaluation_split_id"
    longer = variant(train, vector=(*train["vector"], 0), suffix="longer")
    assert fit([train, longer])["reason"] == "mixed_vector_dimension"
    model = fit([train])
    assert predict(model=model, encoded_record=other_encoder)["reason"] == "encoder_mismatch"
    assert predict(model=model, encoded_record=other_split)["reason"] == "evaluation_split_mismatch"
    assert predict(model=model, encoded_record=longer)["reason"] == "vector_dimension_mismatch"


def test_prediction_ignores_label_and_partition():
    _, train = base()
    model = fit([train])
    a = predict(model=model, encoded_record=train)
    for label, partition in ((-1, "validation"), (0, "test"), (1, "train")):
        other = variant(train, label=label, partition=partition, suffix=f"{label}-{partition}")
        prediction = predict(model=model, encoded_record=other)
        assert prediction["predicted_terminal_target"] == a["predicted_terminal_target"]
        assert prediction["prediction_id"] == a["prediction_id"]
        assert prediction["evaluation_partition"] == partition


def test_existing_encoder_oov_holdout_vector_remains_predictable():
    train_semantic = semantic(**case()[0])
    unseen = changed(train_semantic, lambda f: f["public_battle"]["active"]["opponent"].update(
        pokemon_id="heldout-only-pokemon"), partition="test", suffix="heldout")
    encoder = fit_encoder([train_semantic, unseen])
    train = encode(encoder=encoder, semantic_record=train_semantic)
    heldout = encode(encoder=encoder, semantic_record=unseen)
    assert "heldout-only-pokemon" not in encoder["vocabularies"]["pokemon"]
    model = fit([train, heldout])
    assert model["status"] == "fitted"
    prediction = predict(model=model, encoded_record=heldout)
    assert prediction["status"] == "predicted" and math.isfinite(prediction["predicted_terminal_target"])


def test_malformed_detached_record_and_caller_mutation_fail_closed():
    _, train = base()
    model = fit([train])
    before = deepcopy(_editable(train))
    forged = _editable(train)
    forged["vector"][0] += 1  # encoded identity now disagrees with the vector
    assert fit([_freeze(forged)])["reason"] == "encoded_record_invalid"
    assert predict(model=model, encoded_record=_freeze(forged))["reason"] == "encoded_record_invalid"
    assert _editable(train) == before
    assert not {"q_value", "advantage", "rank", "recommended_action", "probability", "confidence"} & set(model)
