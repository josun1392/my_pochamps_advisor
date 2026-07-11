from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_battle_state_context import build_item_event_context_from_confirmations
from tests.test_advisor_payload_contract import _move, _panel, _window
from ui.main_window import MainWindow, _normalize_item_event_session
from ui.widgets.item_event_dialog import ItemEventDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _event(**overrides: Any) -> dict[str, Any]:
    event = {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": 5,
        "note": "User saw Focus Sash activation text.",
    }
    event.update(overrides)
    return event


class _FakeDialog:
    def __init__(self, *, current_events: list[dict[str, Any]], result_events: list[dict[str, Any]]) -> None:
        self.current_events = deepcopy(current_events)
        self.item_event_confirmations = deepcopy(result_events)

    def exec(self) -> QDialog.DialogCode:
        return QDialog.DialogCode.Accepted


def _session_window(events: list[dict[str, Any]]) -> MainWindow:
    window = MainWindow.__new__(MainWindow)
    window._item_event_confirmations = deepcopy(events)
    window.center_column = SimpleNamespace(
        llm_advice_panel=SimpleNamespace(set_item_event_count=lambda count: None)
    )
    return window


def test_summary_count_and_dialog_summary_do_not_expose_raw_event_dicts() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    panel.set_item_event_count(0)
    assert panel.item_event_button.text() == "Item event"
    panel.set_item_event_count(2)
    assert panel.item_event_button.text() == "Item event (2)"

    dialog = ItemEventDialog(current_events=[_event(), _event(item="leftovers", event_type="item_recovery_observed", turn=7)])
    summaries = [dialog.event_list.item(index).text() for index in range(dialog.event_list.count())]
    assert dialog.event_list.count() == 2
    assert "opponent: focus-sash" in summaries[0]
    assert "item_activation_observed" in summaries[0]
    assert "Turn 5" in summaries[0]
    assert "{" not in "\n".join(summaries)


def test_dialog_edit_replaces_selected_event_and_cancel_keeps_session_state() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    initial = [_event(), _event(item="leftovers", event_type="item_recovery_observed", turn=7)]
    dialog = ItemEventDialog(current_events=initial)
    dialog.event_list.setCurrentRow(0)
    dialog.note_edit.setPlainText("Updated note.")
    dialog._save_and_accept()

    assert dialog.item_event_confirmations == [
        _event(note="Updated note."),
        initial[1],
    ]

    window = _session_window(initial)
    before_cancel = deepcopy(window._item_event_confirmations)
    assert before_cancel == initial


def test_invalid_edit_does_not_replace_session_state(monkeypatch: Any) -> None:
    previous = [_event()]
    window = _session_window(previous)

    monkeypatch.setattr(
        main_window_module,
        "ItemEventDialog",
        lambda *, current_events, parent: _FakeDialog(
            current_events=current_events,
            result_events=[_event(exact_hp=1)],
        ),
    )

    window._open_item_event_dialog()

    assert window._item_event_confirmations == previous


def test_dialog_delete_removes_only_selected_event_and_updates_payload_candidate() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    first = _event()
    second = _event(item="leftovers", event_type="item_recovery_observed", turn=7)
    dialog = ItemEventDialog(current_events=[first, second])
    dialog.event_list.setCurrentRow(0)
    dialog._delete_selected_event()
    dialog._save_and_accept()

    assert dialog.item_event_confirmations == [second]
    assert build_item_event_context_from_confirmations(dialog.item_event_confirmations) == {
        "observed_events": [{**second, "confidence": "observed"}]
    }


def test_duplicate_identity_updates_in_place_and_turn_none_is_duplicate() -> None:
    first = _event(note="first")
    updated = _event(note="updated")
    none_turn = _event(item="quick-claw", turn=None, note="first none")
    none_turn_updated = _event(item="quick-claw", turn=None, note="updated none")

    assert _normalize_item_event_session([first, updated, none_turn, none_turn_updated]) == [
        updated,
        none_turn_updated,
    ]


def test_different_turn_is_distinct_and_session_order_is_turn_then_stable_then_none() -> None:
    turn_five_first = _event(item="focus-sash", turn=5, note="first at five")
    turn_five_second = _event(item="quick-claw", turn=5, note="second at five")
    turn_two = _event(item="leftovers", event_type="item_recovery_observed", turn=2)
    turn_none = _event(item="choice-scarf", event_type="item_reveal_observed", turn=None)
    turn_six = _event(item="focus-sash", turn=6)

    ordered = _normalize_item_event_session([turn_five_first, turn_none, turn_five_second, turn_two, turn_six])

    assert ordered == [turn_two, turn_five_first, turn_five_second, turn_six, turn_none]


def test_editing_turn_reorders_and_duplicate_state_maps_once_when_enabled() -> None:
    updated = _event(item="focus-sash", turn=2, note="edited turn")
    later = _event(item="leftovers", event_type="item_recovery_observed", turn=5)
    window = _window(
        _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")]),
        _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")]),
    )
    window._item_event_confirmations = _normalize_item_event_session([later, updated, updated])

    battle_input = window._build_llm_battle_input(include_item_event_confirmations=True)

    assert battle_input["item_event_confirmations"] == [updated, later]


def test_explicit_session_reset_clears_events_but_checkbox_and_advice_do_not() -> None:
    events = [_event()]
    window = _session_window(events)
    window._update_item_event_summary()

    # The gate is only a payload decision, so it cannot mutate session state.
    assert window._item_event_confirmations == events
    window._clear_item_event_confirmations()
    assert window._item_event_confirmations == []
    assert build_item_event_context_from_confirmations(window._item_event_confirmations) is None


def test_lifecycle_panel_actions_do_not_emit_advice_request() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    calls = {"advice": 0, "item": 0, "reset": 0}
    panel.advice_requested.connect(lambda: calls.__setitem__("advice", calls["advice"] + 1))
    panel.item_event_requested.connect(lambda: calls.__setitem__("item", calls["item"] + 1))
    panel.item_event_session_reset_requested.connect(lambda: calls.__setitem__("reset", calls["reset"] + 1))

    panel.item_event_button.click()
    panel.clear_item_events_button.click()

    assert calls == {"advice": 0, "item": 1, "reset": 1}
