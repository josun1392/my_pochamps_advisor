from types import SimpleNamespace

from ui.main_window import MainWindow


class _Thread:
    def __init__(self): self.deleted = 0; self.running = True; self.interruptions = 0; self.parent = None
    def deleteLater(self): self.deleted += 1
    def isRunning(self): return self.running
    def requestInterruption(self): self.interruptions += 1
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
    _on_structured_recommendation_failed = MainWindow._on_structured_recommendation_failed
    closeEvent = MainWindow.closeEvent
    def __init__(self):
        self._is_closing = False; self._advice_request_sequence = 0
        self._active_advice_owner = self._active_advice_request_token = self._active_advice_terminal_token = None
        self.panel = _Panel(); self.center_column = SimpleNamespace(llm_advice_panel=self.panel)
        self._llm_thread = self._llm_worker = None
        self._structured_thread = self._structured_worker = None
    def statusBar(self): return SimpleNamespace(showMessage=lambda _: None)


def _result():
    return {"presentation_model": {"status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}}


def test_close_invalidates_request_and_late_success_failure_do_not_touch_ui_but_cleanup_is_safe():
    window = _Harness(); token = window._begin_advice_request("structured")
    thread, worker = _Thread(), object(); window._structured_thread, window._structured_worker = thread, worker
    accepted = []; window.closeEvent(SimpleNamespace(accept=lambda: accepted.append(True)))
    window._on_structured_recommendation_finished(token, _result())
    window._on_structured_recommendation_failed(token, "raw-like")
    window._cleanup_structured_worker(token, thread, worker)
    window._cleanup_structured_worker(token, thread, worker)
    assert accepted == [True] and window.panel.events == [] and thread.deleted == 1
    assert window._active_advice_owner is None and window._begin_advice_request("structured") is None
    assert thread.interruptions == 1
