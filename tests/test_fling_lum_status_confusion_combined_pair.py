import pytest

from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from tests.fling_lum_status_confusion_cure_test_support import (
    _assert_lum_first_exact,
    _pair,
)


@pytest.mark.parametrize("condition", ["sleep", "freeze"])
def test_lum_first_combined_sleep_freeze_and_confusion_removes_both_gates(condition):
    case = _pair(target_condition=condition, target_confusion="confused")
    _assert_lum_first_exact(case, "applied_major_status_and_confusion_cure")
    rendered = repr(case["pair"])
    for forbidden in (
        "cancelled_due_to_sleep",
        "cancelled_due_to_freeze",
        "confusion_self_hit",
        "confusion_selected_action_executes",
        "confusion_snaps_out",
    ):
        assert forbidden not in rendered
    for branch in case["pair"]["terminal_branches"]:
        first = branch["first_action_leaf"]
        intermediate = materialize_detached_predictive_intermediate_state(
            strategy_d0=case["d0"], terminal_leaf=first,
        )
        row = intermediate["active"]["opponent"]
        assert row["hypothetical_condition"]["status"] == "known_none"
        assert row["hypothetical_confusion"]["status"] == "known_none"
        assert row["hypothetical_confusion"]["champions_confusion_progression"] is None


def test_lum_first_paralysis_and_confusion_has_no_confusion_or_full_paralysis_branch():
    case = _pair(target_condition="paralysis", target_confusion="confused")
    _assert_lum_first_exact(case, "applied_major_status_and_confusion_cure")
    rendered = repr(case["pair"])
    assert "cancelled_due_to_paralysis" not in rendered
    assert "confusion_self_hit" not in rendered
    assert "confusion_selected_action_executes" not in rendered
    assert "confusion_snaps_out" not in rendered
