"""Exact semantic train occurrence counts without numeric OOV collisions."""
from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_strategy_exact_state_action_support import (
    fit_train_only_exact_state_action_support as fit,
    project_exact_state_action_support as project,
)
from llm.advisor_offline_strategy_model_feature_semantics import materialize_offline_strategy_model_feature_semantics as semantic
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_model_feature_semantics import case
from tests.test_offline_strategy_train_only_numeric_encoding import changed


def record():
    return semantic(**case()[0])


def query(index, row):
    result = project(support_index=index, semantic_record=row)
    assert result["status"] == "projected", result
    return result


def unavailable_like(train, *, partition="train"):
    args, _ = case(cause="forfeit_opponent")
    unavailable = _editable(semantic(**args))
    unavailable["audit"]["evaluation_split_id"] = train["audit"]["evaluation_split_id"]
    unavailable["evaluation_partition"] = partition
    return _freeze(unavailable)


def test_one_and_two_train_occurrences_count_without_deduplication():
    first = record()
    one = fit([first])
    assert one["status"] == "fitted", one
    assert one["eligible_train_record_count"] == 1
    assert one["distinct_exact_state_count"] == 1
    assert one["distinct_exact_state_action_count"] == 1
    assert query(one, first)["exact_state_train_count"] == 1
    assert query(one, first)["exact_state_action_train_count"] == 1
    second = changed(first, suffix="independent-decision-record")
    two = fit([first, second])
    assert two["eligible_train_record_count"] == 2
    assert query(two, first)["exact_state_train_count"] == 2
    assert query(two, first)["exact_state_action_train_count"] == 2
    assert two == fit([second, first])
    assert two["support_index_id"] == fit([second, first])["support_index_id"]


def test_shared_state_has_separate_action_counts_without_ratio():
    first = record()
    same_a = changed(first, suffix="a-2")
    same_a3 = changed(first, suffix="a-3")
    different_action = changed(first, lambda f: f["selected_action"].update(move_id="protect"), suffix="b-1")
    different_action2 = changed(different_action, suffix="b-2")
    index = fit([first, same_a, same_a3, different_action, different_action2])
    a = query(index, first)
    b = query(index, different_action)
    assert a["exact_state_fingerprint"] == b["exact_state_fingerprint"]
    assert a["exact_state_action_fingerprint"] != b["exact_state_action_fingerprint"]
    assert a["exact_state_train_count"] == b["exact_state_train_count"] == 5
    assert a["exact_state_action_train_count"] == 3
    assert b["exact_state_action_train_count"] == 2
    assert "probability" not in a and "action_frequency" not in a


def test_known_exact_state_can_have_zero_count_for_a_different_selected_action():
    first = record()
    index = fit([first])
    different = changed(first, lambda f: f["selected_action"].update(move_id="protect"),
                        partition="validation", suffix="different-action")
    projected = query(index, different)
    assert projected["exact_state_fingerprint"] == query(index, first)["exact_state_fingerprint"]
    assert projected["exact_state_train_count"] == 1
    assert projected["exact_state_action_train_count"] == 0


@pytest.mark.parametrize("edit", [
    lambda f: f["public_battle"]["active"]["self"]["current_hp"].update(value=50),
    lambda f: f["public_battle"]["field"]["weather"].update(value="sun"),
    lambda f: f["actor_private"]["own_roster"][0]["known_item"].update(value="different-item"),
    lambda f: f["exact_legal_actions"]["action_ids"].append("attack:new-move"),
])
def test_genuine_state_fact_changes_exact_state_fingerprint(edit):
    first = record()
    index = fit([first])
    heldout = changed(first, edit, partition="validation", suffix="changed-state")
    assert query(index, heldout)["exact_state_fingerprint"] != query(index, first)["exact_state_fingerprint"]
    assert query(index, heldout)["exact_state_train_count"] == 0
    assert query(index, heldout)["exact_state_action_train_count"] == 0


def test_labels_and_partition_do_not_enter_exact_fingerprints_or_counts():
    first = record()
    baseline = fit([first])
    for label in (1, 0, -1):
        relabeled = changed(first, label=label, suffix=f"label-{label}")
        assert fit([relabeled])["support_index_id"] == baseline["support_index_id"]
        assert fit([relabeled])["exact_state_counts"] == baseline["exact_state_counts"]
        assert fit([relabeled])["exact_state_action_counts"] == baseline["exact_state_action_counts"]
        for partition in ("validation", "test"):
            heldout = changed(first, label=label, partition=partition,
                              suffix=f"{partition}-{label}")
            projected = query(baseline, heldout)
            assert projected["exact_state_fingerprint"] == query(baseline, first)["exact_state_fingerprint"]
            assert projected["exact_state_action_fingerprint"] == query(baseline, first)["exact_state_action_fingerprint"]
            assert projected["exact_state_train_count"] == 1
            assert projected["exact_state_action_train_count"] == 1
            assert fit([first, heldout])["support_index_id"] == baseline["support_index_id"]


def test_heldout_unseen_categories_do_not_create_oov_based_false_support():
    first = record()
    baseline = fit([first])
    for partition in ("validation", "test"):
        pokemon = changed(first, lambda f: f["public_battle"]["active"]["opponent"].update(
            pokemon_id=f"{partition}-unseen-pokemon"), partition=partition, suffix=partition + "-pokemon")
        move = changed(first, lambda f: f["public_battle"]["opponent_revealed_moves"].update(
            move_ids=[f"{partition}-unseen-move"]), partition=partition, suffix=partition + "-move")
        for heldout in (pokemon, move):
            assert query(baseline, heldout)["availability"] == "available"
            assert query(baseline, heldout)["exact_state_train_count"] == 0
            assert query(baseline, heldout)["exact_state_action_train_count"] == 0
            assert fit([first, heldout])["support_index_id"] == baseline["support_index_id"]
    assert "exact_semantic_equality_only_no_similarity_or_oov_collapse" in baseline["limitations"]


def test_unavailable_train_and_query_are_distinct_from_zero_support():
    first = record()
    missing = unavailable_like(first)
    index = fit([first, missing])
    assert index["eligible_train_record_count"] == 1
    assert index["unavailable_train_record_count"] == 1
    assert index["support_index_id"] == fit([first])["support_index_id"]
    unavailable = query(index, missing)
    assert unavailable["availability"] == "unavailable"
    assert unavailable["exact_state_train_count"] is None
    assert unavailable["exact_state_action_train_count"] is None
    assert unavailable["exact_state_fingerprint"] is None
    zero = query(index, changed(first, lambda f: f["public_battle"]["active"]["self"]["current_hp"].update(value=49),
                                partition="test", suffix="zero"))
    assert zero["availability"] == "available"
    assert zero["exact_state_train_count"] == zero["exact_state_action_train_count"] == 0
    assert fit([missing])["reason"] == "no_eligible_train_feature_record"


def test_duplicate_mixed_split_and_malformed_record_fail_closed():
    first = record()
    assert fit([first, first])["reason"] == "duplicate_feature_record_id"
    other = _editable(changed(first, suffix="other"))
    other["audit"]["evaluation_split_id"] = "foreign-split"
    other = _freeze(other)
    assert fit([first, other])["reason"] == "mixed_evaluation_split_id"
    assert project(support_index=fit([first]), semantic_record=other)["reason"] == "evaluation_split_mismatch"
    malformed = _editable(first)
    malformed["model_features"]["selected_action"]["move_id"] = "forged"
    assert fit([_freeze(malformed)])["reason"] == "semantic_record_invalid"
    assert project(support_index=fit([first]), semantic_record=_freeze(malformed))["reason"] == "semantic_record_invalid"


def test_fitted_counts_and_projection_are_immutable_without_quality_claims():
    first = record()
    original = deepcopy(_editable(first))
    index = fit([first])
    projection = query(index, first)
    assert _editable(first) == original
    with pytest.raises(TypeError):
        index["exact_state_counts"][projection["exact_state_fingerprint"]] = 2
    with pytest.raises(TypeError):
        projection["exact_state_train_count"] = 2
    assert "decision_record_occurrence_count_not_independent_sample_count" in index["limitations"]
    forbidden = {"confidence", "sufficient", "supported", "abstain", "threshold", "score",
                 "reward", "win_rate", "mean_label", "prediction", "model_id"}
    assert not forbidden & set(index)
    assert not forbidden & set(projection)
