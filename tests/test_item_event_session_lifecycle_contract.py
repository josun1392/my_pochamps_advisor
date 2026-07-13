from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QDialog

import llm.advisor_client as advisor_client
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


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _capture_prompt_with_mocked_provider(
    monkeypatch: pytest.MonkeyPatch,
    battle_input: dict[str, Any],
    *,
    limited_context_enabled: bool,
) -> tuple[str, int]:
    captured: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v12-56-lifecycle"
        captured.append(prompt)
        return "offline lifecycle response", {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})
    advisor_client.run_ui_selected_advice(
        battle_input,
        model="offline-v12-56-lifecycle",
        enable_battle_state_context=limited_context_enabled,
    )
    assert len(captured) == 1
    return captured[0], len(captured)


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
    turn_one = _event(item="sitrus-berry", event_type="item_consumption_observed", turn=1)
    turn_five_first = _event(item="focus-sash", turn=5, note="first at five")
    turn_five_second = _event(item="quick-claw", turn=5, note="second at five")
    turn_two = _event(item="leftovers", event_type="item_recovery_observed", turn=2)
    turn_none = _event(item="choice-scarf", event_type="item_reveal_observed", turn=None)
    turn_six = _event(item="focus-sash", turn=6)
    turn_ten = _event(item="yache-berry", event_type="item_prevention_observed", turn=10)

    ordered = _normalize_item_event_session(
        [turn_five_first, turn_none, turn_five_second, turn_ten, turn_two, turn_six, turn_one]
    )

    assert ordered == [turn_one, turn_two, turn_five_first, turn_five_second, turn_six, turn_ten, turn_none]


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


def test_edit_that_collides_with_another_event_keeps_the_edited_value_once() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    first = _event(item="focus-sash", turn=2, note="original")
    existing = _event(item="leftovers", event_type="item_recovery_observed", turn=5, note="existing")
    dialog = ItemEventDialog(current_events=[first, existing])
    dialog.event_list.setCurrentRow(0)
    dialog.item_combo.setEditText("leftovers")
    index = dialog.event_type_combo.findData("item_recovery_observed")
    assert index >= 0
    dialog.event_type_combo.setCurrentIndex(index)
    dialog.turn_spin.setValue(5)
    dialog.note_edit.setPlainText("edited collision")
    dialog._save_and_accept()

    assert dialog.item_event_confirmations == [_event(
        item="leftovers",
        event_type="item_recovery_observed",
        turn=5,
        note="edited collision",
    )]


def test_main_window_lifecycle_changes_flow_to_payload_and_mocked_provider_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    first = _event(turn=2, note="before edit")
    edited = _event(item="quick-claw", turn=1, note="after edit")
    dialogs = [
        _FakeDialog(current_events=[], result_events=[first]),
        _FakeDialog(current_events=[first], result_events=[edited]),
        _FakeDialog(current_events=[edited], result_events=[]),
    ]
    panel = LLMAdvicePanel()
    window = _window(
        _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")]),
        _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")]),
    )
    window._item_event_confirmations = []
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    monkeypatch.setattr(main_window_module, "ItemEventDialog", lambda *, current_events, parent: dialogs.pop(0))

    window._open_item_event_dialog()
    assert panel.item_event_button.text() == "Item event (1)"
    prompt, calls = _capture_prompt_with_mocked_provider(
        monkeypatch,
        window._build_llm_battle_input(include_item_event_confirmations=True),
        limited_context_enabled=True,
    )
    payload = _prompt_payload(prompt)
    assert calls == 1
    assert payload["item_event_context"]["observed_events"][0]["note"] == "before edit"
    assert "If item_event_context is present" in prompt

    window._open_item_event_dialog()
    edited_input = window._build_llm_battle_input(include_item_event_confirmations=True)
    assert edited_input["item_event_confirmations"] == [edited]
    edited_prompt, _ = _capture_prompt_with_mocked_provider(
        monkeypatch,
        edited_input,
        limited_context_enabled=True,
    )
    assert "before edit" not in edited_prompt
    assert "after edit" in edited_prompt

    window._open_item_event_dialog()
    deleted_input = window._build_llm_battle_input(include_item_event_confirmations=True)
    deleted_prompt, _ = _capture_prompt_with_mocked_provider(
        monkeypatch,
        deleted_input,
        limited_context_enabled=True,
    )
    assert panel.item_event_button.text() == "Item event"
    assert "item_event_confirmations" not in deleted_input
    assert "item_event_context" not in _prompt_payload(deleted_prompt)
    assert "If item_event_context is present" not in deleted_prompt


def test_checkbox_gate_preserves_session_state_and_restores_event_prompt_when_reenabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event()
    panel = LLMAdvicePanel()
    window = _window(
        _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")]),
        _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")]),
    )
    window._item_event_confirmations = [event]
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    window._update_item_event_summary()

    panel.turn_pipeline_checkbox.setChecked(False)
    off_input = window._build_llm_battle_input(include_item_event_confirmations=panel.turn_pipeline_enabled())
    off_prompt, _ = _capture_prompt_with_mocked_provider(monkeypatch, off_input, limited_context_enabled=False)
    assert window._item_event_confirmations == [event]
    assert panel.item_event_button.text() == "Item event (1)"
    assert "item_event_confirmations" not in off_input
    assert "If item_event_context is present" not in off_prompt

    panel.turn_pipeline_checkbox.setChecked(True)
    on_input = window._build_llm_battle_input(include_item_event_confirmations=panel.turn_pipeline_enabled())
    on_prompt, _ = _capture_prompt_with_mocked_provider(monkeypatch, on_input, limited_context_enabled=True)
    assert on_input["item_event_confirmations"] == [event]
    assert "If item_event_context is present" in on_prompt


def test_clear_resets_summary_dialog_payload_and_prompt_without_advice_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event()
    panel = LLMAdvicePanel()
    advice_requests = 0

    def record_advice_request() -> None:
        nonlocal advice_requests
        advice_requests += 1

    panel.advice_requested.connect(record_advice_request)
    window = _window(
        _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")]),
        _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")]),
    )
    window._item_event_confirmations = [event]
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    panel.item_event_session_reset_requested.connect(window._clear_item_event_confirmations)
    window._update_item_event_summary()

    panel.clear_item_events_button.click()
    cleared_input = window._build_llm_battle_input(include_item_event_confirmations=True)
    cleared_prompt, calls = _capture_prompt_with_mocked_provider(monkeypatch, cleared_input, limited_context_enabled=True)
    dialog = ItemEventDialog(current_events=window._item_event_confirmations)

    assert advice_requests == 0
    assert calls == 1
    assert panel.item_event_button.text() == "Item event"
    assert dialog.event_list.count() == 0
    assert "item_event_confirmations" not in cleared_input
    assert "item_event_context" not in _prompt_payload(cleared_prompt)
    assert "If item_event_context is present" not in cleared_prompt


def test_invalid_selection_or_repeated_delete_preserves_remaining_draft_without_crash() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    first = _event(turn=1)
    second = _event(item="leftovers", event_type="item_recovery_observed", turn=2)
    dialog = ItemEventDialog(current_events=[first, second])

    dialog._load_selected_event(99)
    dialog._delete_selected_event()
    assert dialog.event_list.count() == 2
    dialog.event_list.setCurrentRow(0)
    dialog._delete_selected_event()
    dialog._delete_selected_event()
    dialog._save_and_accept()

    assert dialog.item_event_confirmations == [second]


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
