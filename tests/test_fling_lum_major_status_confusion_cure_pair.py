import pytest

from tests.fling_lum_status_confusion_cure_test_support import (
    _assert_lum_first_exact,
    _pair,
)


@pytest.mark.parametrize("condition", ["sleep", "freeze"])
def test_lum_first_sleep_or_freeze_cure_executes_pending_action_without_status_gate(condition):
    case = _pair(target_condition=condition)
    _assert_lum_first_exact(case, "applied_major_status_cure")
    assert "cancelled_due_to_sleep" not in repr(case["pair"])
    assert "cancelled_due_to_freeze" not in repr(case["pair"])


def test_lum_first_confusion_cure_executes_without_confusion_branches():
    case = _pair(target_confusion="confused")
    _assert_lum_first_exact(case, "applied_confusion_cure")
    rendered = repr(case["pair"])
    assert "confusion_self_hit" not in rendered
    assert "confusion_selected_action_executes" not in rendered
    assert "confusion_snaps_out" not in rendered
