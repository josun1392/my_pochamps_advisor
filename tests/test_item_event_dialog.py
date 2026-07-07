from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from llm.advisor_battle_state_context import EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES
from ui.widgets.item_event_dialog import (
    ITEM_EVENT_SOURCE,
    ITEM_EVENT_STATUS,
    ItemEventDialog,
)


_FORBIDDEN_RESULT_FIELDS = {
    "berry_recovered_exact_hp",
    "exact_damage",
    "exact_hp",
    "focus_sash_post_hit_hp_1",
    "item_damage_modifier_applied",
    "item_speed_modifier_applied",
    "post_turn_hp_from_item",
    "post_turn_item_state",
    "quick_claw_activated_by_rng",
    "resolved_item_effect",
    "rng_roll",
    "speed_order_override",
}


def test_item_event_dialog_returns_valid_observed_event_shape() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    _set_combo(dialog.side_combo, "opponent")
    dialog.item_combo.setEditText("focus-sash")
    _set_combo(dialog.event_type_combo, "item_activation_observed")
    dialog.turn_spin.setValue(5)
    dialog.note_edit.setPlainText("User saw Focus Sash activation text.")

    dialog._save_and_accept()

    assert dialog.item_event_confirmations == [
        {
            "side": "opponent",
            "item": "focus-sash",
            "event_type": "item_activation_observed",
            "status": ITEM_EVENT_STATUS,
            "source": ITEM_EVENT_SOURCE,
            "turn": 5,
            "note": "User saw Focus Sash activation text.",
        }
    ]
    _assert_forbidden_result_fields_absent(dialog.item_event_confirmations)


@pytest.mark.parametrize("event_type", sorted(EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES))
def test_item_event_dialog_supports_allowed_event_types(event_type: str) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    dialog.item_combo.setEditText("quick-claw")
    _set_combo(dialog.event_type_combo, event_type)

    dialog._save_and_accept()

    events = dialog.item_event_confirmations
    assert events is not None
    assert events[0]["event_type"] == event_type
    assert events[0]["source"] == ITEM_EVENT_SOURCE
    assert events[0]["status"] == ITEM_EVENT_STATUS
    _assert_forbidden_result_fields_absent(events)


def test_item_event_dialog_blank_turn_and_note_keep_none_values() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    dialog.item_combo.setEditText("leftovers")
    _set_combo(dialog.event_type_combo, "item_recovery_observed")
    dialog.turn_spin.setValue(0)
    dialog.note_edit.clear()

    dialog._save_and_accept()

    events = dialog.item_event_confirmations
    assert events is not None
    assert events[0]["turn"] is None
    assert events[0]["note"] is None


def test_item_event_dialog_cancel_does_not_save_draft() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    dialog.item_combo.setEditText("sitrus-berry")

    dialog.reject()

    assert dialog.item_event_confirmations is None


def test_item_event_dialog_reset_clears_draft_without_accepting() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    dialog.item_combo.setEditText("focus-sash")
    dialog.turn_spin.setValue(5)
    dialog.note_edit.setPlainText("User saw activation.")

    dialog._reset_draft()

    assert dialog.item_event_confirmations is None
    assert dialog.item_combo.currentText() == ""
    assert dialog.turn_spin.value() == 0
    assert dialog.note_edit.toPlainText() == ""


def test_item_event_dialog_reset_then_apply_returns_empty_list() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog(
        current_events=[
            {
                "side": "opponent",
                "item": "focus-sash",
                "event_type": "item_activation_observed",
                "status": ITEM_EVENT_STATUS,
                "source": ITEM_EVENT_SOURCE,
                "turn": 5,
                "note": "User saw activation.",
            }
        ]
    )

    dialog._reset_draft()
    dialog._save_and_accept()

    assert dialog.item_event_confirmations == []


def test_item_event_dialog_loads_initial_event() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog(
        current_events=[
            {
                "side": "self",
                "item": "choice-scarf",
                "event_type": "item_reveal_observed",
                "status": ITEM_EVENT_STATUS,
                "source": ITEM_EVENT_SOURCE,
                "turn": 2,
                "note": "User confirmed reveal.",
            }
        ]
    )

    assert dialog.side_combo.currentData() == "self"
    assert dialog.item_combo.currentText() == "choice-scarf"
    assert dialog.event_type_combo.currentData() == "item_reveal_observed"
    assert dialog.turn_spin.value() == 2
    assert dialog.note_edit.toPlainText() == "User confirmed reveal."


def test_item_event_dialog_rejects_missing_item() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    dialog.item_combo.setEditText("")

    with pytest.raises(ValueError, match="item"):
        dialog._save_and_accept()

    assert dialog.item_event_confirmations is None


def test_item_event_dialog_rejects_invalid_event_type() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = ItemEventDialog()
    dialog.item_combo.setEditText("focus-sash")
    dialog.event_type_combo.addItem("Resolved item effect", "resolved_item_effect")
    _set_combo(dialog.event_type_combo, "resolved_item_effect")

    with pytest.raises(ValueError, match="event type"):
        dialog._save_and_accept()

    assert dialog.item_event_confirmations is None


def _set_combo(combo, value: str) -> None:
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def _assert_forbidden_result_fields_absent(value: object) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in _FORBIDDEN_RESULT_FIELDS
            _assert_forbidden_result_fields_absent(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_forbidden_result_fields_absent(child_value)
