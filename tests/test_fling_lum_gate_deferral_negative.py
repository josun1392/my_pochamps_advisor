import pytest

from llm.advisor_immediate_move_vs_move_action_pair import (
    _lum_gate_deferral_for_first_cure,
)
from tests.fling_lum_status_confusion_cure_test_support import _pair


def test_lum_second_keeps_existing_combined_target_gate():
    case = _pair(
        order="opponent_first",
        target_condition="sleep",
        target_confusion="confused",
    )
    pair = case["pair"]
    assert pair["schema_version"] == "champions-status-confusion-gated-immediate-action-pair-v1"
    assert pair["status"] in {"evaluable", "incomplete"}


def test_equal_speed_two_order_scope_does_not_defer_any_lum_gate():
    case = _pair(target_condition="none", target_confusion="none")
    base = {
        "own_actor": case["d0"]["active_owners"]["self"],
        "opponent_actor": case["d0"]["active_owners"]["opponent"],
    }
    deferral = _lum_gate_deferral_for_first_cure(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        base=base,
        orders=[
            {"order": "own_first", "probability": 0.5},
            {"order": "opponent_first", "probability": 0.5},
        ],
        own_action=case["own"],
        opponent_action=case["opponent"],
        own_meta=case["own"]["move_metadata_authority"],
        opponent_meta=case["opponent"]["metadata_authority"],
    )
    assert deferral["active"] is False
    assert deferral["defer_status"] is False
    assert deferral["defer_confusion"] is False
    assert deferral["defer_combined"] is False


def test_confused_fling_user_keeps_own_confusion_gate():
    case = _pair(own_confusion="confused", target_confusion="none")
    assert case["pair"]["schema_version"] == "champions-confusion-gated-immediate-action-pair-v1"


@pytest.mark.parametrize("condition", ["sleep", "freeze"])
def test_sleep_or_frozen_fling_user_keeps_own_status_gate(condition):
    case = _pair(own_condition=condition)
    assert case["pair"]["schema_version"] == "champions-status-gated-immediate-action-pair-v1"


def test_wrong_berry_and_non_fling_do_not_defer_lum_gate():
    wrong = _pair(item="persim-berry", target_confusion="confused")
    base = {
        "own_actor": wrong["d0"]["active_owners"]["self"],
        "opponent_actor": wrong["d0"]["active_owners"]["opponent"],
    }
    wrong_deferral = _lum_gate_deferral_for_first_cure(
        strategy_d0=wrong["d0"],
        runtime_snapshot=wrong["snapshot"],
        base=base,
        orders=[{"order": "own_first"}],
        own_action=wrong["own"],
        opponent_action=wrong["opponent"],
        own_meta=wrong["own"]["move_metadata_authority"],
        opponent_meta=wrong["opponent"]["metadata_authority"],
    )
    assert wrong_deferral["active"] is False
    assert wrong["pair"]["status"] == "evaluable"

    non_fling = _pair(own_move="tackle", target_confusion="confused")
    assert non_fling["pair"]["schema_version"] == "champions-confusion-gated-immediate-action-pair-v1"


def test_target_ko_before_eat_has_no_lum_effect_or_ateberry():
    case = _pair(target_condition="sleep", target_confusion="confused", opponent_hp=1)
    if case["pair"]["status"] == "evaluable":
        for branch in case["pair"]["terminal_branches"]:
            first = branch["first_action_leaf"]
            assert first["consequences"]["target_ko"] is True
            assert "fling_lum_major_status_confusion_cure_target_effect" not in first["consequences"]
            assert "fling_berry_eaten_transition" not in first["consequences"]
            assert branch["second_action"]["state"] == "cancelled_due_to_faint"
    else:
        assert case["pair"]["status"] == "incomplete"
