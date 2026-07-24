"""Offline bounded-shutdown contract; no provider or network runner is used."""
from types import SimpleNamespace

import ui.main_window as main_window
from ui.main_window import LLMAdviceWorker, MainWindow, StructuredRecommendationWorker


class _Thread:
    def __init__(self, running=True):
        self.running = running
        self.interruptions = 0
        self.deleted = 0
        self.parent = None

    def isRunning(self): return self.running
    def requestInterruption(self): self.interruptions += 1
    def deleteLater(self): self.deleted += 1
    def setParent(self, parent): self.parent = parent


class _Panel:
    def __init__(self):
        self.events = []
        self.structured_request_button = SimpleNamespace(setDisabled=lambda value: self.events.append(("button", value)))

    def set_running(self, value): self.events.append(("running", value))
    def set_mode_advice_text(self, mode, text): self.events.append(("text", mode, text))
    def set_error(self, message): self.events.append(("error", message))
    def set_cost_text(self, value): self.events.append(("cost", value))


class _Harness:
    _begin_advice_request = MainWindow._begin_advice_request
    _is_current_advice_request = MainWindow._is_current_advice_request
    _claim_current_advice_terminal = MainWindow._claim_current_advice_terminal
    _clear_current_advice_request = MainWindow._clear_current_advice_request
    _delete_advice_thread_once = staticmethod(MainWindow._delete_advice_thread_once)
    _advice_threads_for_shutdown = MainWindow._advice_threads_for_shutdown
    _cleanup_structured_worker = MainWindow._cleanup_structured_worker
    _on_structured_recommendation_finished = MainWindow._on_structured_recommendation_finished
    closeEvent = MainWindow.closeEvent

    def __init__(self):
        self._is_closing = False; self._advice_request_sequence = 0
        self._active_advice_owner = self._active_advice_request_token = self._active_advice_terminal_token = None
        self._llm_thread = self._llm_worker = None
        self._structured_thread = self._structured_worker = None
        self.center_column = SimpleNamespace(llm_advice_panel=_Panel())

    def statusBar(self): return SimpleNamespace(showMessage=lambda _: None)


def test_close_requests_cooperative_stop_without_wait_and_late_cleanup_is_idempotent():
    window = _Harness()
    legacy, structured = _Thread(), _Thread()
    window._llm_thread, window._structured_thread = legacy, structured
    accepted = []
    window.closeEvent(SimpleNamespace(accept=lambda: accepted.append(True)))
    assert accepted == [True]
    assert (legacy.interruptions, structured.interruptions) == (1, 1)
    assert window._is_closing is True
    window._cleanup_structured_worker(999, structured, object())
    window._cleanup_structured_worker(999, structured, object())
    assert structured.deleted == 1


def test_workers_emit_internal_cancel_before_runner_and_after_local_runner(monkeypatch):
    calls = []
    legacy = LLMAdviceWorker({})
    legacy.cancelled.connect(lambda: calls.append("legacy-cancelled"))
    legacy._is_interruption_requested = lambda: True
    monkeypatch.setattr(main_window, "run_ui_selected_advice", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("runner called")))
    legacy.run()

    structured = StructuredRecommendationWorker([], {}, None)
    structured.cancelled.connect(lambda: calls.append("structured-cancelled"))
    structured._is_interruption_requested = lambda: True
    monkeypatch.setattr(main_window, "run_structured_ui_recommendation", lambda **kwargs: (_ for _ in ()).throw(AssertionError("runner called")))
    structured.run()

    after_runner = LLMAdviceWorker({})
    after_runner.cancelled.connect(lambda: calls.append("after-runner-cancelled"))
    states = iter((False, True))
    after_runner._is_interruption_requested = lambda: next(states)
    monkeypatch.setattr(main_window, "run_ui_selected_advice", lambda *args, **kwargs: ("local", {}, {}))
    after_runner.run()
    assert calls == ["legacy-cancelled", "structured-cancelled", "after-runner-cancelled"]
