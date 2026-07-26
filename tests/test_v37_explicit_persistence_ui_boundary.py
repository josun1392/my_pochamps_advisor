from copy import deepcopy
from types import SimpleNamespace
import inspect

import pytest

import ui.main_window as main_window_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from ui.main_window import MainWindow


class _Button:
    def __init__(self): self.disabled = []
    def setDisabled(self, value): self.disabled.append(value)


class _Panel:
    def __init__(self): self.events = []; self.structured_request_button = _Button()
    def set_running(self, value): self.events.append(("running", value))
    def set_mode_advice_text(self, mode, text): self.events.append(("text", mode, text))
    def set_error(self, message): self.events.append(("error", message))


class _Status:
    def __init__(self): self.messages = []
    def showMessage(self, message): self.messages.append(message)


class _Harness:
    _active_session_id = MainWindow._active_session_id
    _active_persistence_manager = MainWindow._active_persistence_manager
    _present_persistence_status = MainWindow._present_persistence_status
    _save_battle_state = MainWindow._save_battle_state
    _load_battle_state = MainWindow._load_battle_state
    _present_loaded_candidate = MainWindow._present_loaded_candidate
    _restore_loaded_candidate = MainWindow._restore_loaded_candidate
    _reset_restored_battle_presentation = MainWindow._reset_restored_battle_presentation
    _retire_advice_presentation_authority = MainWindow._retire_advice_presentation_authority
    _is_current_advice_request = MainWindow._is_current_advice_request
    _claim_current_advice_terminal = MainWindow._claim_current_advice_terminal
    _is_current_structured_session = MainWindow._is_current_structured_session
    _on_structured_recommendation_finished = MainWindow._on_structured_recommendation_finished
    _on_structured_recommendation_failed = MainWindow._on_structured_recommendation_failed

    def __init__(self, active=True):
        self._observation_runtime_session_manager = None
        if active:
            initial = create_unknown_bootstrap_battle_state("session-a", "pikachu", "eevee")["state"]
            self._observation_runtime_session_manager = BattleObservationRuntimeSessionManager.create("session-a", initial)["manager"]
        self.panel, self.status = _Panel(), _Status()
        self.center_column = SimpleNamespace(llm_advice_panel=self.panel)
        self._is_closing = False
        self._active_advice_owner = "structured"
        self._active_advice_request_token = 7
        self._active_advice_terminal_token = None

    def statusBar(self): return self.status


def _core_values(window):
    manager = window._observation_runtime_session_manager
    state = manager.read_state()
    return (
        manager.session_id,
        manager.read_collection_snapshot(),
        state["state"],
        state["state_fingerprint"],
        state["state"]["last_applied_observation_sequence"],
        manager.last_allocated_sequence,
        manager.read_applied_ledger(),
    )


def _candidate(window):
    manager = window._observation_runtime_session_manager
    return manager._active_session._runtime.export_envelope()["envelope"]


def test_save_action_requires_active_session(monkeypatch):
    window = _Harness(active=False)
    monkeypatch.setattr(main_window_module.QFileDialog, "getSaveFileName", lambda *_: pytest.fail("dialog"))
    window._save_battle_state()
    assert window.status.messages[-1] == "Battle-state save unavailable: start a battle first."


def test_save_action_invokes_explicit_command_once_and_is_non_mutating(monkeypatch, tmp_path):
    window = _Harness(); before = _core_values(window); calls = []
    monkeypatch.setattr(main_window_module.QFileDialog, "getSaveFileName", lambda *_: (str(tmp_path / "state.json"), ""))
    monkeypatch.setattr(window._observation_runtime_session_manager, "save", lambda *args: calls.append(args) or {"status": "save_complete"})
    window._save_battle_state()
    assert len(calls) == 1 and _core_values(window) == before
    assert window._active_advice_request_token == 7 and window.status.messages[-1] == "Battle state saved."


def test_save_cancel_is_non_error_and_invokes_no_command(monkeypatch):
    window = _Harness()
    monkeypatch.setattr(main_window_module.QFileDialog, "getSaveFileName", lambda *_: ("", ""))
    monkeypatch.setattr(window._observation_runtime_session_manager, "save", lambda *_: pytest.fail("save"))
    window._save_battle_state()
    assert window.status.messages[-1] == "Battle-state save cancelled." and window._active_advice_request_token == 7


def test_save_failure_preserves_current_ui_and_core(monkeypatch, tmp_path):
    window = _Harness(); before = _core_values(window); ui = list(window.panel.events)
    monkeypatch.setattr(main_window_module.QFileDialog, "getSaveFileName", lambda *_: (str(tmp_path / "state.json"), ""))
    monkeypatch.setattr(window._observation_runtime_session_manager, "save", lambda *_: {"status": "io_error"})
    window._save_battle_state()
    assert _core_values(window) == before and window.panel.events == ui and window._active_advice_request_token == 7
    assert window.status.messages[-1] == "Battle-state save failed."


def test_load_action_returns_detached_candidate_without_runtime_mutation(monkeypatch, tmp_path):
    window = _Harness(); manager = window._observation_runtime_session_manager; before = _core_values(window); target = tmp_path / "state.json"
    assert manager.save("session-a", target)["status"] == "save_complete"
    captured = {}
    monkeypatch.setattr(main_window_module.QFileDialog, "getOpenFileName", lambda *_: (str(target), ""))
    monkeypatch.setattr(_Harness, "_present_loaded_candidate", lambda self, _m, candidate, **kwargs: captured.update(candidate=candidate, **kwargs))
    window._load_battle_state()
    captured["candidate"]["store"]["state"]["session_id"] = "mutated"
    assert _core_values(window) == before and captured["loaded_for_session_id"] == "session-a"
    assert captured["expected_runtime_fingerprint"] == before[3]


def test_load_cancel_invokes_no_command(monkeypatch):
    window = _Harness()
    monkeypatch.setattr(main_window_module.QFileDialog, "getOpenFileName", lambda *_: ("", ""))
    monkeypatch.setattr(window._observation_runtime_session_manager, "load", lambda *_: pytest.fail("load"))
    window._load_battle_state()
    assert window.status.messages[-1] == "Battle-state load cancelled."


def test_foreign_session_candidate_does_not_roll_over_or_restore(monkeypatch, tmp_path):
    window = _Harness(); before = _core_values(window); foreign_state = create_unknown_bootstrap_battle_state("session-b", "pikachu", "eevee")["state"]
    foreign = BattleObservationRuntimeSessionManager.create("session-b", foreign_state)["manager"]; target = tmp_path / "foreign.json"
    assert foreign.save("session-b", target)["status"] == "save_complete"
    monkeypatch.setattr(main_window_module.QFileDialog, "getOpenFileName", lambda *_: (str(target), ""))
    monkeypatch.setattr(window._observation_runtime_session_manager, "restore", lambda *_: pytest.fail("restore"))
    window._load_battle_state()
    assert _core_values(window) == before and window.status.messages[-1] == "Loaded state belongs to a different battle session."


def test_restore_requires_explicit_confirmation(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager
    monkeypatch.setattr(main_window_module.QMessageBox, "question", lambda *_: main_window_module.QMessageBox.StandardButton.No)
    monkeypatch.setattr(manager, "restore", lambda *_: pytest.fail("restore"))
    window._present_loaded_candidate(manager, _candidate(window), loaded_for_session_id="session-a", expected_runtime_fingerprint=manager.read_state()["state_fingerprint"])
    assert window.status.messages[-1] == "Battle-state restore cancelled."


def test_restore_uses_load_time_fingerprint_and_retires_request_only_after_success(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager; candidate = _candidate(window); fingerprint = manager.read_state()["state_fingerprint"]; calls = []
    monkeypatch.setattr(manager, "restore", lambda *args: calls.append(args) or {"status": "restore_complete"})
    window._restore_loaded_candidate(manager, candidate, loaded_for_session_id="session-a", expected_runtime_fingerprint=fingerprint)
    assert calls[0][0] == "session-a" and calls[0][2] == fingerprint
    assert window._active_advice_request_token is None and any(event[0] == "text" for event in window.panel.events)
    assert window.status.messages[-1] == "Battle state restored."


def test_restore_rejects_stale_runtime_without_command_or_request_retirement(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager; before = _core_values(window)
    monkeypatch.setattr(manager, "restore", lambda *_: pytest.fail("restore"))
    window._restore_loaded_candidate(manager, _candidate(window), loaded_for_session_id="session-a", expected_runtime_fingerprint="stale")
    assert _core_values(window) == before and window._active_advice_request_token == 7
    assert window.status.messages[-1] == "Battle state changed after loading; restore was not applied."


def test_restore_failure_preserves_current_core_ui_and_request_authority(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager; before = _core_values(window); ui = list(window.panel.events); fingerprint = manager.read_state()["state_fingerprint"]
    monkeypatch.setattr(manager, "restore", lambda *_: {"status": "restore_rolled_back"})
    window._restore_loaded_candidate(manager, _candidate(window), loaded_for_session_id="session-a", expected_runtime_fingerprint=fingerprint)
    assert _core_values(window) == before and window.panel.events == ui and window._active_advice_request_token == 7
    assert window.status.messages[-1] == "Battle-state restore failed."


def test_restore_rejects_candidate_after_session_rollover(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager; candidate = _candidate(window); fingerprint = manager.read_state()["state_fingerprint"]
    rolled = manager.rollover("session-b", create_unknown_bootstrap_battle_state("session-b", "pikachu", "eevee")["state"]); assert rolled["status"] == "session_replaced"
    monkeypatch.setattr(manager, "restore", lambda *_: pytest.fail("restore"))
    window._restore_loaded_candidate(manager, candidate, loaded_for_session_id="session-a", expected_runtime_fingerprint=fingerprint)
    assert manager.session_id == "session-b" and window._active_advice_request_token == 7


def test_restore_retirement_suppresses_late_pre_restore_worker_results():
    window = _Harness()
    assert window._active_advice_owner == "structured" and window._active_advice_request_token == 7
    window._retire_advice_presentation_authority()
    assert not MainWindow._is_current_advice_request(window, "structured", 7)


def test_restore_success_suppresses_late_pre_restore_worker_success_and_error(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager; fingerprint = manager.read_state()["state_fingerprint"]
    monkeypatch.setattr(manager, "restore", lambda *_: {"status": "restore_complete"})
    window._restore_loaded_candidate(manager, _candidate(window), loaded_for_session_id="session-a", expected_runtime_fingerprint=fingerprint)
    before = (list(window.panel.events), list(window.status.messages))
    result = {"presentation_model": {"status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}}
    window._on_structured_recommendation_finished(7, "session-a", result)
    window._on_structured_recommendation_failed(7, "session-a", "late error")
    assert (window.panel.events, window.status.messages) == before


def test_main_window_has_no_long_lived_raw_candidate_field_or_implicit_features():
    source = inspect.getsource(main_window_module)
    assert "_pending_persistence_candidate" not in source
    assert not any(term in source for term in ("autosave", "startup_restore", "recent_files", "cloud_sync"))
    assert "getSaveFileName" in source and "getOpenFileName" in source
