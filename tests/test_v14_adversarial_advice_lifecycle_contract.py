"""Deterministic adversarial callback ordering for the token lifecycle."""
from types import SimpleNamespace

from ui.main_window import MainWindow


class _Panel:
    def __init__(self):
        self.events = []
        self.structured_request_button = SimpleNamespace(setDisabled=lambda value: self.events.append(("button", value)))
    def set_running(self, value): self.events.append(("running", value))
    def set_mode_advice_text(self, mode, text): self.events.append(("text", mode, text))
    def set_error(self, message): self.events.append(("error", message))
    def set_cost_text(self, value): self.events.append(("cost", value))


class _Thread:
    def __init__(self): self.deletes = 0
    def deleteLater(self): self.deletes += 1


class _Harness:
    _begin_advice_request = MainWindow._begin_advice_request
    _is_current_advice_request = MainWindow._is_current_advice_request
    _claim_current_advice_terminal = MainWindow._claim_current_advice_terminal
    _clear_current_advice_request = MainWindow._clear_current_advice_request
    _delete_advice_thread_once = staticmethod(MainWindow._delete_advice_thread_once)
    _on_structured_recommendation_finished = MainWindow._on_structured_recommendation_finished
    _on_structured_recommendation_failed = MainWindow._on_structured_recommendation_failed
    _cleanup_structured_worker = MainWindow._cleanup_structured_worker
    _on_llm_advice_finished = MainWindow._on_llm_advice_finished
    _on_llm_advice_failed = MainWindow._on_llm_advice_failed
    _cleanup_llm_worker = MainWindow._cleanup_llm_worker
    def __init__(self):
        self._advice_request_sequence = 0
        self._active_advice_owner = None
        self._active_advice_request_token = None
        self._active_advice_terminal_token = None
        self.panel = _Panel()
        self.center_column = SimpleNamespace(llm_advice_panel=self.panel)
        self._structured_thread = self._structured_worker = None
        self._llm_thread = self._llm_worker = None
        self.messages = []
    def statusBar(self): return SimpleNamespace(showMessage=self.messages.append)


def _result():
    return {"presentation_model": {"status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}}


def test_finished_before_success_and_duplicate_finished_are_idempotent_and_late_success_is_ignored():
    window = _Harness(); token = window._begin_advice_request("structured")
    thread, worker = _Thread(), object(); window._structured_thread, window._structured_worker = thread, worker
    window._cleanup_structured_worker(token, thread, worker)
    window._cleanup_structured_worker(token, thread, worker)
    events = list(window.panel.events)
    window._on_structured_recommendation_finished(token, _result())
    assert thread.deletes == 1 and window.panel.events == events
    assert window._active_advice_owner is None and window._active_advice_request_token is None


def test_duplicate_success_or_failure_claims_terminal_once_without_raw_or_token_output():
    window = _Harness(); token = window._begin_advice_request("structured")
    window._on_structured_recommendation_finished(token, _result())
    events = list(window.panel.events); messages = list(window.messages)
    window._on_structured_recommendation_finished(token, _result())
    window._on_structured_recommendation_failed(token, "secret-like stale error")
    assert window.panel.events == events and window.messages == messages
    assert all("secret-like" not in str(event) and str(token) not in str(event) for event in window.panel.events)


def test_triple_cross_mode_race_leaves_only_latest_terminal_effect_and_stale_callbacks_are_ignored():
    window = _Harness()
    token_a = window._begin_advice_request("structured")
    token_b = window._begin_advice_request("legacy")
    token_c = window._begin_advice_request("structured")
    window._on_structured_recommendation_failed(token_a, "A")
    window._on_llm_advice_failed(token_b, "B")
    window._on_structured_recommendation_finished(token_c, _result())
    assert [event[0] for event in window.panel.events].count("error") == 0
    assert any(event[0] == "text" and event[1] == "structured" for event in window.panel.events)
    assert window._is_current_advice_request("structured", token_c)
