from copy import deepcopy

import pytest

from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from tests.test_runtime_d0_fling_item_execution_authority import (
    _production_fling_pair,
)


@pytest.mark.parametrize(
    ("item", "condition"),
    (
        ("cheri-berry", "paralysis"),
        ("chesto-berry", "sleep"),
        ("aspear-berry", "freeze"),
        ("rawst-berry", "burn"),
        ("pecha-berry", "poison"),
        ("pecha-berry", "toxic"),
    ),
)
def test_status_cure_berry_closes_immediate_pair_and_exact_ledger(item, condition):
    pair, ledger = _production_fling_pair(item=item, target_condition=condition)
    assert pair["status"] == "evaluable", pair.get("reason")
    assert ledger["status"] == "evaluable", ledger
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {branch["action_order"] for branch in pair["terminal_branches"]} == {"own_first"}
    assert {branch["second_action"]["state"] for branch in pair["terminal_branches"]} == {"executed"}
    for branch in pair["terminal_branches"]:
        effect = branch["first_action_leaf"]["consequences"][
            "fling_major_status_cure_berry_target_effect"
        ]
        assert effect["outcome"] == "applied_major_status_cure"
        assert effect["condition_before"] == condition
        assert effect["condition_after"] == "none"
        marker = effect["hypothetical_target_condition_removal"]
        assert marker["condition_before"] == condition
        assert marker["condition_after"] == "none"


def test_cheri_cure_removes_full_paralysis_cancellation_without_reordering():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    assert all(branch["action_order"] == "own_first" for branch in pair["terminal_branches"])
    assert "cancelled_due_to_paralysis" not in {
        branch["second_action"]["state"] for branch in pair["terminal_branches"]
    }
    assert {branch["second_action"]["state"] for branch in pair["terminal_branches"]} == {"executed"}


@pytest.mark.parametrize(
    ("item", "condition"),
    (("chesto-berry", "sleep"), ("aspear-berry", "freeze")),
)
def test_sleep_and_freeze_cures_execute_pending_action_without_stale_runtime_gate(item, condition):
    pair, ledger = _production_fling_pair(item=item, target_condition=condition)
    assert pair["status"] == ledger["status"] == "evaluable"
    assert {branch["second_action"]["state"] for branch in pair["terminal_branches"]} == {"executed"}


@pytest.mark.parametrize(
    ("item", "condition"),
    (
        ("rawst-berry", "burn"),
        ("pecha-berry", "poison"),
        ("pecha-berry", "toxic"),
    ),
)
def test_burn_poison_and_toxic_cures_reach_path_local_known_none(item, condition):
    pair, ledger = _production_fling_pair(item=item, target_condition=condition)
    assert pair["status"] == ledger["status"] == "evaluable"
    for branch in pair["terminal_branches"]:
        authority = branch["first_action_leaf"]["consequences"][
            "fling_major_status_cure_berry_target_effect"
        ]["authority"]
        assert authority["condition_before"] == condition
        assert authority["condition_after"] == "none"


def test_exact_ledger_rejects_forged_removal_marker():
    pair, _ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
    )
    forged = deepcopy(pair)
    branch = deepcopy(forged["terminal_branches"][0])
    marker = branch["first_action_leaf"]["consequences"][
        "fling_major_status_cure_berry_target_effect"
    ]["hypothetical_target_condition_removal"]
    marker["source_leaf_id"] = "forged"
    forged["terminal_branches"] = (branch, *forged["terminal_branches"][1:])
    normalized = normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)
    assert normalized["status"] == "rejected"


def test_no_transition_leaf_cannot_claim_condition_removal():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="burn",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    assert all(
        branch["first_action_leaf"]["consequences"][
            "fling_major_status_cure_berry_target_effect"
        ]["outcome"] == "no_transition_nonmatching_condition"
        for branch in pair["terminal_branches"]
    )

    valid_pair, _ = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
    )
    marker = deepcopy(
        valid_pair["terminal_branches"][0]["first_action_leaf"]["consequences"][
            "fling_major_status_cure_berry_target_effect"
        ]["hypothetical_target_condition_removal"]
    )
    forged = deepcopy(pair)
    branch = deepcopy(forged["terminal_branches"][0])
    branch["first_action_leaf"]["consequences"][
        "fling_major_status_cure_berry_target_effect"
    ]["hypothetical_target_condition_removal"] = marker
    forged["terminal_branches"] = (branch, *forged["terminal_branches"][1:])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"
