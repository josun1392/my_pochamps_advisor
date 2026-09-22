from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

import ui.main_window as main_window_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from ui.main_window import MainWindow
from ui.widgets.current_field_state_dialog import CurrentFieldStateDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _field(weather: str = "rain") -> dict[str, object]:
    return {"weather": weather, "terrain": "none", "global_effects": [], "side_effects": [{"side": "self", "effect": "reflect"}], "status": "user_confirmed", "source": "user_confirmed_current_field_state"}


class _FakeDialog:
    def __init__(self, snapshot: dict[str, object] | None, accepted: bool = True, **_: object) -> None:
        self.current_field_state_confirmation = snapshot
        self._accepted = accepted

    def exec(self) -> QDialog.DialogCode:
        return QDialog.DialogCode.Accepted if self._accepted else QDialog.DialogCode.Rejected


def _window() -> tuple[MainWindow, LLMAdvicePanel]:
    QApplication.instance() or QApplication([])
    window = MainWindow.__new__(MainWindow)
    panel = LLMAdvicePanel()
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    window._current_field_state_confirmation = None
    window._locked_on_state_confirmation = None
    state = create_unknown_bootstrap_battle_state("field-ui", "self-a", "opponent-a")["state"]
    window._observation_runtime_session_manager = BattleObservationRuntimeSessionManager.create("field-ui", state)["manager"]
    window._current_trusted_turn_number = 1
    return window, panel


def test_field_dialog_apply_readback_and_snapshot_normalization() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentFieldStateDialog(current_field=_field())
    assert "Field snapshot saved" in dialog.summary_label.text()
    dialog.weather.setCurrentText("snow")
    dialog._save()
    assert dialog.current_field_state_confirmation is not None
    assert dialog.current_field_state_confirmation["weather"] == "snow"
    assert dialog.current_field_state_confirmation["confidence"] == "known"


def test_grounded_confirmation_is_explicit_and_unknown_by_default() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentFieldStateDialog(current_field=_field())
    assert dialog.grounded_context_confirmation is None
    dialog.self_grounded.setCurrentText("known_grounded")
    dialog.opponent_grounded.setCurrentText("known_ungrounded")
    dialog._save()
    assert dialog.grounded_context_confirmation == {
        "self": {"status": "known_grounded", "provenance": "user_confirmed_current"},
        "opponent": {"status": "known_ungrounded", "provenance": "user_confirmed_current"},
    }


def test_field_session_apply_cancel_clear_and_count(monkeypatch) -> None:
    window, panel = _window()
    dialogs = [_FakeDialog(_field()), _FakeDialog(_field("sun")), _FakeDialog(_field("snow"), accepted=False)]
    monkeypatch.setattr(main_window_module, "CurrentFieldStateDialog", lambda **kwargs: dialogs.pop(0))
    window._open_current_field_state_dialog(); window._open_current_field_state_dialog(); window._open_current_field_state_dialog()
    assert window._current_field_state_confirmation["weather"] == "sun"
    assert panel.current_field_state_button.text() == "Field state (3)"
    window._grounded_context_confirmation = {
        "self": {"status": "known_grounded", "provenance": "user_confirmed_current"},
        "opponent": {"status": "known_ungrounded", "provenance": "user_confirmed_current"},
    }
    window._clear_current_field_state_confirmation()
    assert window._current_field_state_confirmation is None
    assert window._grounded_context_confirmation == {
        "self": {"status": "unknown", "provenance": "unknown"},
        "opponent": {"status": "unknown", "provenance": "unknown"},
    }
    assert panel.current_field_state_button.text() == "Field state"


def test_gravity_field_ui_emits_exact_active_and_inactive_without_duration(monkeypatch) -> None:
    window, _panel = _window()
    dialogs = [
        _FakeDialog({**_field(), "global_effects": ["gravity"]}),
        _FakeDialog({**_field(), "global_effects": []}),
    ]
    monkeypatch.setattr(main_window_module, "CurrentFieldStateDialog", lambda **kwargs: dialogs.pop(0))

    window._open_current_field_state_dialog()
    state = window._observation_runtime_session_manager.read_state()["state"]
    assert state["field"]["gravity_status"] == "active"
    assert "remaining_duration" not in state["field"]

    window._current_trusted_turn_number = 2
    window._open_current_field_state_dialog()
    state = window._observation_runtime_session_manager.read_state()["state"]
    assert state["field"]["gravity_status"] == "inactive"
    assert "remaining_duration" not in state["field"]


def test_locked_on_ui_explicit_inactive_and_active_exact_target(monkeypatch) -> None:
    window, _panel = _window()

    inactive_answers = iter([("self", True), ("Inactive", True)])
    monkeypatch.setattr(main_window_module.QInputDialog, "getItem", lambda *args, **kwargs: next(inactive_answers))
    monkeypatch.setattr(main_window_module.QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window._open_locked_on_state_confirmation()
    state = window._observation_runtime_session_manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["locked_on_state"] == {"status": "known_inactive"}

    window._current_trusted_turn_number = 2
    active_answers = iter([("self", True), ("Active", True), ("opponent slot 0: opponent-a", True)])
    monkeypatch.setattr(main_window_module.QInputDialog, "getItem", lambda *args, **kwargs: next(active_answers))
    window._open_locked_on_state_confirmation()
    state = window._observation_runtime_session_manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["locked_on_state"] == {
        "status": "known_active",
        "bound_target": {"session_id": "field-ui", "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"},
    }
    assert window._locked_on_state_confirmation["status"] == "active"


def test_locked_on_active_ui_refuses_missing_target_and_session_reset_clears_cache(monkeypatch) -> None:
    window, _panel = _window()
    manager = window._observation_runtime_session_manager
    state = manager.read_state()["state"]
    state["opponent_side"]["pokemon"] = {}
    replaced = BattleObservationRuntimeSessionManager.create("field-ui", state)
    window._observation_runtime_session_manager = replaced["manager"]

    answers = iter([("self", True), ("Active", True)])
    monkeypatch.setattr(main_window_module.QInputDialog, "getItem", lambda *args, **kwargs: next(answers))
    window._open_locked_on_state_confirmation()
    assert window._locked_on_state_confirmation is None

    window._locked_on_state_confirmation = {"status": "active", "sentinel": True}
    window._battle_session_sequence = 0
    monkeypatch.setattr(MainWindow, "_selected_identity", lambda self, column: {"pokemon_id": "self-a" if column == "team_my" else "opponent-a"})
    monkeypatch.setattr(MainWindow, "_loaded_roster_identities", lambda self, column: {0: "self-a" if column == "team_my" else "opponent-a"})
    new_session = window._begin_new_battle_session()
    assert new_session == "ui-session-1"
    assert window._locked_on_state_confirmation is None
