from copy import deepcopy

import pytest

from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    _defer_confusion_gate_for_first_persim_cure,
    _lum_gate_deferral_for_first_cure,
)
from tests.test_fling_major_status_cure_berry_gate_deferral import _case, _defer
from tests.test_fling_persim_confusion_cure_pair import _pair as _persim_pair
from tests.fling_lum_status_confusion_cure_test_support import _pair as _lum_pair
from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair


def _successful_first_leaves(pair):
    assert pair["status"] == "evaluable", pair
    return [
        branch["first_action_leaf"]
        for branch in pair["terminal_branches"]
        if branch["first_action_leaf"].get("consequences", {}).get("target_ko") is not True
    ]


def test_pressure_cheri_cure_remains_unchanged():
    pair, ledger = _production_fling_pair(
        item="cheri-berry", target_condition="paralysis", target_ability="pressure",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    leaves = _successful_first_leaves(pair)
    assert leaves
    assert all(
        leaf["consequences"]["fling_major_status_cure_berry_target_effect"]["outcome"]
        == "applied_major_status_cure"
        for leaf in leaves
    )


def test_target_klutz_known_absent_cheri_has_no_cure_but_ateberry_true():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
        target_ability="klutz",
        target_item=None,
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable", (pair.get("reason"), ledger.get("reason"))
    leaves = _successful_first_leaves(pair)
    assert leaves
    for leaf in leaves:
        consequences = leaf["consequences"]
        assert "fling_major_status_cure_berry_target_effect" not in consequences
        assert consequences["fling_berry_eaten_transition"]["resulting_state"] == "known_true"
        intrinsic = consequences["fling_berry_eaten_transition"][
            "berry_eat_item_interaction_authority"
        ]["target_intrinsic_berry_on_eat"]
        assert intrinsic["state"] == "suppressed_by_target_klutz"


def test_target_klutz_ability_shield_allows_cheri_intrinsic_cure():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
        target_ability="klutz",
        target_item="ability-shield",
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable", (pair.get("reason"), ledger.get("reason"))
    leaves = _successful_first_leaves(pair)
    assert leaves
    for leaf in leaves:
        payload = leaf["consequences"]["fling_major_status_cure_berry_target_effect"]
        assert payload["outcome"] == "applied_major_status_cure"
        intrinsic = payload["authority"]["target_intrinsic_on_eat_readiness"]
        assert intrinsic["readiness"] == "executes"
        item = intrinsic["authority"]["target_item_authority"]
        assert item["value"] == "ability-shield"


def test_target_klutz_unknown_item_fails_closed():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
        target_ability="klutz",
        target_item="__unknown__",
        opponent_move="protect",
    )
    assert pair["status"] == "incomplete"
    assert ledger["status"] == "incomplete"
    assert "fling_major_status_cure_berry_target_effect" not in repr(pair)


@pytest.mark.parametrize(
    ("item", "condition"),
    [("chesto-berry", "sleep"), ("aspear-berry", "freeze")],
)
def test_target_klutz_suppression_prevents_sleep_freeze_cure_deferral(item, condition):
    case = _case(
        item=item,
        target_condition=condition,
        target_ability="klutz",
        target_item=None,
    )
    own_first = [{"order": "own_first", "probability": 1, "source_branch": None}]
    assert _defer(case, own_first) is False


def test_target_klutz_known_absent_persim_keeps_confusion_gate():
    case = _persim_pair(
        target_ability="klutz",
        target_item=None,
        opponent_confusion="confused",
        materialize_pair=False,
    )
    base = {
        "own_actor": case["d0"]["active_owners"]["self"],
        "opponent_actor": case["d0"]["active_owners"]["opponent"],
    }
    assert _defer_confusion_gate_for_first_persim_cure(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        base=base,
        orders=[{"order": "own_first"}],
        own_action=case["own"],
        own_meta=case["own"]["move_metadata_authority"],
    ) is False
    target = case["snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert target["current_confusion"] == "confused"
    assert target["champions_confusion_progression"]["state"] == "confused"


def test_target_klutz_known_absent_lum_keeps_atomic_status_confusion_gate():
    case = _lum_pair(
        target_ability="klutz",
        target_item=None,
        target_condition="sleep",
        target_confusion="confused",
        materialize_pair=False,
    )
    base = {
        "own_actor": case["d0"]["active_owners"]["self"],
        "opponent_actor": case["d0"]["active_owners"]["opponent"],
    }
    result = _lum_gate_deferral_for_first_cure(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        base=base,
        orders=[{"order": "own_first"}],
        own_action=case["own"],
        opponent_action=case["opponent"],
        own_meta=case["own"]["move_metadata_authority"],
        opponent_meta={
            "metadata": case["opponent"]["metadata_authority"]["metadata"],
        },
    )
    assert result == {
        "active": False,
        "defer_status": False,
        "defer_confusion": False,
        "defer_combined": False,
    }
    target = case["snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert target["condition"] == "sleep"
    assert target["current_confusion"] == "confused"


def test_target_klutz_known_absent_lum_paralysis_confusion_does_not_false_cure():
    case = _lum_pair(
        target_ability="klutz",
        target_item=None,
        target_condition="paralysis",
        target_confusion="confused",
        materialize_pair=False,
    )
    base = {
        "own_actor": case["d0"]["active_owners"]["self"],
        "opponent_actor": case["d0"]["active_owners"]["opponent"],
    }
    result = _lum_gate_deferral_for_first_cure(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        base=base,
        orders=[{"order": "own_first"}],
        own_action=case["own"],
        opponent_action=case["opponent"],
        own_meta=case["own"]["move_metadata_authority"],
        opponent_meta={
            "metadata": case["opponent"]["metadata_authority"]["metadata"],
        },
    )
    assert result["active"] is False
    assert result["defer_confusion"] is False
    target = case["snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert target["condition"] == "paralysis"
    assert target["current_confusion"] == "confused"


def test_type_resist_empty_intrinsic_remains_evaluable_under_target_klutz():
    pair, ledger = _production_fling_pair(
        item="colbur-berry",
        target_ability="klutz",
        target_item=None,
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable", (pair, ledger)
    leaves = _successful_first_leaves(pair)
    assert leaves
    for leaf in leaves:
        payload = leaf["consequences"][
            "fling_type_resist_empty_intrinsic_berry_target_effect"
        ]
        assert payload["outcome"] == "no_intrinsic_target_effect"
        assert payload["authority"]["target_intrinsic_on_eat_readiness"][
            "readiness"
        ] == "suppressed_by_target_klutz"
        assert leaf["consequences"]["fling_berry_eaten_transition"][
            "resulting_state"
        ] == "known_true"


def test_ledger_rejects_forged_suppression_as_cure_and_forged_target_item():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
        target_ability="klutz",
        target_item=None,
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    forged = deepcopy(pair)
    branch = deepcopy(forged["terminal_branches"][0])
    first = branch["first_action_leaf"]
    transition = first["consequences"]["fling_berry_eaten_transition"]
    interaction = transition["berry_eat_item_interaction_authority"]
    intrinsic = interaction["target_intrinsic_berry_on_eat"]
    intrinsic["state"] = "executes"
    intrinsic["target_item_ignore_klutz_authority"] = {
        "status": "resolved",
        "ignore_klutz": True,
        "basis": "forged",
    }
    forged["terminal_branches"] = (branch, *forged["terminal_branches"][1:])
    rejected = normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)
    assert rejected["status"] == "rejected"

    positive, _ = _production_fling_pair(
        item="cheri-berry",
        target_condition="paralysis",
        target_ability="klutz",
        target_item="ability-shield",
        opponent_move="protect",
    )
    forged_item = deepcopy(positive)
    branch = deepcopy(forged_item["terminal_branches"][0])
    payload = branch["first_action_leaf"]["consequences"][
        "fling_major_status_cure_berry_target_effect"
    ]
    payload["authority"]["target_intrinsic_on_eat_readiness"]["authority"][
        "target_item_authority"
    ]["value"] = "leftovers"
    forged_item["terminal_branches"] = (
        branch, *forged_item["terminal_branches"][1:]
    )
    assert normalize_exact_immediate_action_pair_outcome_ledger(
        pair=forged_item
    )["status"] == "rejected"
