"""Caller-supplied exact-support minima without confidence or model claims."""
import inspect
from copy import deepcopy

import pytest

from llm.advisor_offline_strategy_exact_state_action_support import fit_train_only_exact_state_action_support as fit
from llm.advisor_offline_strategy_exact_support_abstention import (
    apply_exact_support_abstention_policy as apply,
    materialize_exact_support_abstention_policy as policy,
)
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_exact_state_action_support import record, unavailable_like
from tests.test_offline_strategy_train_only_numeric_encoding import changed


def index_and_queries():
    first = record()
    same_a = changed(first, suffix="a-2")
    same_a3 = changed(first, suffix="a-3")
    b = changed(first, lambda f: f["selected_action"].update(move_id="protect"), suffix="b-1")
    b2 = changed(b, suffix="b-2")
    index = fit([first, same_a, same_a3, b, b2])
    assert index["status"] == "fitted", index
    return index, first, b


def gate(index, row, state_min, action_min):
    explicit = policy(min_exact_state_train_count=state_min,
                      min_exact_state_action_train_count=action_min)
    assert explicit["status"] == "materialized", explicit
    result = apply(policy=explicit, support_index=index, semantic_record=row)
    assert result["status"] == "decided", result
    return explicit, result


def test_thresholds_are_mandatory_explicit_positive_integers_with_deterministic_identity():
    parameters = inspect.signature(policy).parameters
    assert parameters["min_exact_state_train_count"].default is inspect.Parameter.empty
    assert parameters["min_exact_state_action_train_count"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        policy(min_exact_state_train_count=2)
    with pytest.raises(TypeError):
        policy(min_exact_state_action_train_count=2)
    a = policy(min_exact_state_train_count=2, min_exact_state_action_train_count=3)
    assert a == policy(min_exact_state_train_count=2, min_exact_state_action_train_count=3)
    assert a["policy_authority"] == "explicit_external_exact_support_threshold_policy"
    assert a["abstention_policy_id"] != policy(
        min_exact_state_train_count=3, min_exact_state_action_train_count=3)["abstention_policy_id"]
    assert a["abstention_policy_id"] != policy(
        min_exact_state_train_count=2, min_exact_state_action_train_count=4)["abstention_policy_id"]
    with pytest.raises(TypeError):
        a["min_exact_state_train_count"] = 1


@pytest.mark.parametrize("bad", [0, -1, True, False, 1.0, 2.5, "1", None])
def test_invalid_thresholds_fail_closed(bad):
    assert policy(min_exact_state_train_count=bad, min_exact_state_action_train_count=2)["reason"] == (
        "min_exact_state_train_count_invalid")
    assert policy(min_exact_state_train_count=2, min_exact_state_action_train_count=bad)["reason"] == (
        "min_exact_state_action_train_count_invalid")


def test_allow_above_and_equal_both_explicit_thresholds():
    index, first, b = index_and_queries()
    _, above = gate(index, first, 4, 2)
    assert above["gate_result"] == "allow_learned_estimate"
    assert above["reasons"] == ()
    assert above["exact_state_train_count"] == 5
    assert above["exact_state_action_train_count"] == 3
    _, equality = gate(index, first, 5, 3)
    assert equality["gate_result"] == "allow_learned_estimate"
    assert equality["reasons"] == ()
    _, other_action = gate(index, b, 5, 2)
    assert other_action["gate_result"] == "allow_learned_estimate"
    assert other_action["exact_state_action_train_count"] == 2
    assert "threshold_pass_does_not_establish_statistical_confidence_or_correctness" in equality["limitations"]
    assert "decision_record_occurrence_count_not_independent_sample_count" in equality["limitations"]


def test_state_action_and_both_below_have_independent_ordered_reasons():
    index, first, _ = index_and_queries()
    _, state_below = gate(index, first, 6, 3)
    assert state_below["gate_result"] == "abstain"
    assert state_below["reasons"] == ("exact_state_support_below_policy_minimum",)
    _, action_below = gate(index, first, 5, 4)
    assert action_below["reasons"] == ("exact_state_action_support_below_policy_minimum",)
    _, both = gate(index, first, 6, 4)
    assert both["reasons"] == (
        "exact_state_support_below_policy_minimum",
        "exact_state_action_support_below_policy_minimum",
    )
    assert both["gate_result"] == "abstain"
    assert both == apply(policy=policy(min_exact_state_train_count=6, min_exact_state_action_train_count=4),
                         support_index=index, semantic_record=first)


def test_zero_exact_support_is_factual_and_unavailable_query_is_distinct():
    index, first, _ = index_and_queries()
    unknown_state = changed(first, lambda f: f["public_battle"]["active"]["self"]["current_hp"].update(value=49),
                            partition="test", suffix="unknown-state")
    _, zero = gate(index, unknown_state, 1, 1)
    assert zero["support_projection"]["availability"] == "available"
    assert zero["exact_state_train_count"] == 0
    assert zero["exact_state_action_train_count"] == 0
    assert zero["reasons"] == (
        "exact_state_support_below_policy_minimum",
        "exact_state_action_support_below_policy_minimum",
    )
    other_action = changed(first, lambda f: f["selected_action"].update(move_id="new-action"),
                           partition="validation", suffix="zero-action")
    _, action_zero = gate(index, other_action, 1, 1)
    assert action_zero["exact_state_train_count"] == 5
    assert action_zero["exact_state_action_train_count"] == 0
    assert action_zero["reasons"] == ("exact_state_action_support_below_policy_minimum",)
    unavailable = unavailable_like(first, partition="validation")
    _, missing = gate(index, unavailable, 1, 1)
    assert missing["gate_result"] == "abstain"
    assert missing["reasons"] == ("semantic_model_input_unavailable",)
    assert missing["exact_state_train_count"] is None
    assert missing["exact_state_action_train_count"] is None
    assert missing["support_projection"]["availability"] == "unavailable"


def test_query_partition_and_label_do_not_change_gate_semantics():
    index, first, _ = index_and_queries()
    _, baseline = gate(index, first, 5, 3)
    for partition in ("train", "validation", "test"):
        for label in (1, 0, -1):
            same = changed(first, partition=partition, label=label, suffix=f"{partition}-{label}")
            _, result = gate(index, same, 5, 3)
            assert result["gate_result"] == baseline["gate_result"]
            assert result["reasons"] == baseline["reasons"]
            assert result["abstention_decision_id"] == baseline["abstention_decision_id"]
            assert result["exact_state_train_count"] == 5
            assert result["exact_state_action_train_count"] == 3


@pytest.mark.parametrize("field,kind", [("pokemon_id", "pokemon"), ("move_ids", "move")])
def test_heldout_unseen_semantic_category_abstains_without_oov_shortcut(field, kind):
    index, first, _ = index_and_queries()
    if kind == "pokemon":
        edit = lambda f: f["public_battle"]["active"]["opponent"].update(pokemon_id="heldout-only-pokemon")
    else:
        edit = lambda f: f["public_battle"]["opponent_revealed_moves"].update(move_ids=["heldout-only-move"])
    heldout = changed(first, edit, partition="test", suffix=field)
    _, result = gate(index, heldout, 1, 1)
    assert result["exact_state_train_count"] == 0
    assert result["exact_state_action_train_count"] == 0
    assert result["gate_result"] == "abstain"


def test_gate_reprojects_source_counts_and_does_not_mutate_inputs():
    index, first, _ = index_and_queries()
    before_index = deepcopy(_editable(index))
    before_row = deepcopy(_editable(first))
    explicit, result = gate(index, first, 5, 3)
    assert result["support_projection"]["exact_state_train_count"] == 5
    assert result["support_projection"]["exact_state_action_train_count"] == 3
    assert _editable(index) == before_index and _editable(first) == before_row
    assert gate(index, first, 5, 4)[1]["gate_result"] == "abstain"
    assert _editable(index) == before_index
    with pytest.raises(TypeError):
        result["support_projection"]["exact_state_train_count"] = 0
    with pytest.raises(TypeError):
        result["gate_result"] = "abstain"
    assert apply(policy=dict(explicit), support_index=index, semantic_record=first)["reason"] == "abstention_policy_invalid"
    forbidden = {"confidence", "probability", "reliability", "statistical_significance", "mse", "mae",
                 "model_id", "prediction", "recommendation", "action_rank"}
    assert not forbidden & set(explicit)
    assert not forbidden & set(result)
