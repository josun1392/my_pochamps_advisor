from copy import deepcopy

import pytest

from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from tests.test_runtime_d0_fling_item_execution_authority import (
    _production_fling_pair,
)


MOVES = ["water-gun", "tackle", "growl", "tail-whip"]


def _pp(values):
    return [
        {"slot_index": index, "move_id": MOVES[index], "current_pp": current, "max_pp": maximum}
        for index, (current, maximum) in enumerate(values)
    ]


def _pair(*, values=None, order="own_first", opponent_move="water-gun"):
    values = values or [(4, 10), (0, 15), (10, 10), (10, 10)]
    return _production_fling_pair(
        item="leppa-berry",
        target_item=None,
        target_move_pp_slots=_pp(values),
        opponent_move=opponent_move,
        action_order=order,
    )


def _branch_with_leppa(pair):
    for index, branch in enumerate(pair["terminal_branches"]):
        first = branch.get("first_action_leaf", {})
        effect = first.get("consequences", {}).get("fling_leppa_pp_restore_target_effect")
        if isinstance(effect, dict):
            return index, branch
    raise AssertionError("no Leppa consequence branch")


def _replace_branch(pair, index, branch):
    rows = list(pair["terminal_branches"])
    rows[index] = branch
    pair["terminal_branches"] = tuple(rows)


def test_fling_first_pair_preserves_exact_post_eat_pp_consequence_pending_action_order_and_root_mass():
    pair, ledger = _pair()
    assert pair["status"] == "evaluable", pair.get("reason")
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    observed = 0
    for branch in pair["terminal_branches"]:
        effect = branch["first_action_leaf"].get("consequences", {}).get(
            "fling_leppa_pp_restore_target_effect"
        )
        if not isinstance(effect, dict):
            continue
        observed += 1
        assert branch["action_order"] == "own_first"
        assert effect["outcome"] == "pp_restored"
        assert effect["selected_slot_index"] == 1
        assert effect["selected_move_id"] == "tackle"
        assert effect["selection_reason"] == "first_zero_pp"
        assert effect["pp_before"] == 0
        assert effect["nominal_restore"] == 10
        assert effect["actual_restore"] == 10
        assert effect["pp_after"] == 10
        assert effect["timing"] == "post_eat_pre_pending_action"
        assert effect["external_staleness"]["value"] is True
        assert branch["first_action_leaf"]["consequences"]["fling_berry_eaten_transition"]["resulting_state"] == "known_true"
        assert branch["second_action"]["state"] == "executed"
    assert observed > 0


def test_target_first_pair_fails_closed_instead_of_using_stale_pre_action_pp():
    pair, ledger = _pair(
        values=[(4, 10), (7, 15), (10, 10), (10, 10)],
        order="opponent_first",
    )
    assert pair["status"] == "incomplete"
    assert pair["reason"] == "fling_leppa_target_first_post_action_pp_authority_unavailable"
    assert ledger["status"] == "incomplete"


def test_equal_speed_pair_does_not_renormalize_away_target_first_half():
    pair, ledger = _pair(
        values=[(4, 10), (7, 15), (10, 10), (10, 10)],
        order="unresolved_tie",
    )
    assert pair["status"] == "incomplete"
    assert pair["reason"] == "fling_leppa_target_first_post_action_pp_authority_unavailable"
    assert ledger["status"] == "incomplete"


def test_all_full_fling_first_pair_is_evaluable_and_keeps_staleness_and_ateberry():
    pair, ledger = _pair(values=[(10, 10), (15, 15), (20, 20), (30, 30)])
    assert pair["status"] == ledger["status"] == "evaluable"
    _, branch = _branch_with_leppa(pair)
    effect = branch["first_action_leaf"]["consequences"]["fling_leppa_pp_restore_target_effect"]
    assert effect["outcome"] == "no_effect_all_pp_full"
    assert effect["actual_restore"] == 0
    assert effect["external_staleness"]["value"] is True
    assert branch["first_action_leaf"]["consequences"]["fling_berry_eaten_transition"]["resulting_state"] == "known_true"


def test_ledger_rejects_forged_selection_and_pp_arithmetic():
    pair, _ = _pair()
    for field, value in (
        ("selected_slot_index", 2),
        ("selected_move_id", "growl"),
        ("selection_reason", "first_missing_pp"),
        ("nominal_restore", 11),
        ("actual_restore", 99),
        ("pp_after", 99),
    ):
        forged = deepcopy(pair)
        index, branch = _branch_with_leppa(forged)
        branch = deepcopy(branch)
        effect = branch["first_action_leaf"]["consequences"]["fling_leppa_pp_restore_target_effect"]
        effect[field] = value
        effect["authority"][field] = value
        _replace_branch(forged, index, branch)
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_forged_current_pp_order_and_source_binding():
    pair, _ = _pair()
    for mutate in ("reorder", "source"):
        forged = deepcopy(pair)
        index, branch = _branch_with_leppa(forged)
        branch = deepcopy(branch)
        effect = branch["first_action_leaf"]["consequences"]["fling_leppa_pp_restore_target_effect"]
        if mutate == "reorder":
            authority = effect["authority"]["current_pp_authority"]
            rows = list(authority["ordered_pp_slots"])
            rows[0], rows[1] = rows[1], rows[0]
            authority["ordered_pp_slots"] = tuple(rows)
        else:
            effect["authority"]["source_leaf_id"] = "forged-leaf"
        _replace_branch(forged, index, branch)
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_forged_eat_ateberry_staleness_and_target_item_consumption():
    pair, _ = _pair()
    for kind in ("eat", "ateberry", "staleness", "item"):
        forged = deepcopy(pair)
        index, branch = _branch_with_leppa(forged)
        branch = deepcopy(branch)
        first = branch["first_action_leaf"]
        effect = first["consequences"]["fling_leppa_pp_restore_target_effect"]
        if kind == "eat":
            effect["authority"]["berry_eat_item_interaction_authority"]["target_eat_occurred"] = False
        elif kind == "ateberry":
            first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] = "known_false"
        elif kind == "staleness":
            effect["external_staleness"]["value"] = False
            effect["authority"]["external_staleness"]["value"] = False
        else:
            effect["target_item_after"] = {"status": "known_absent", "value": None}
        _replace_branch(forged, index, branch)
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"
