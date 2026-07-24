"""Pure lifecycle tests: request tokens never reach provider or panel text."""
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


class _Status:
    def __init__(self): self.messages = []
    def showMessage(self, value): self.messages.append(value)


class _Thread:
    def __init__(self): self.deleted = 0
    def deleteLater(self): self.deleted += 1


class _Harness:
    _begin_advice_request = MainWindow._begin_advice_request
    _is_current_advice_request = MainWindow._is_current_advice_request
    _clear_current_advice_request = MainWindow._clear_current_advice_request
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
        self.panel = _Panel()
        self.status = _Status()
        self.center_column = SimpleNamespace(llm_advice_panel=self.panel)
        self._structured_thread = None
        self._structured_worker = None
        self._llm_thread = None
        self._llm_worker = None

    def statusBar(self): return self.status


def _structured_result():
    return {"presentation_model": {"status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}}


def test_tokens_are_monotonic_and_same_owner_stale_success_and_failure_do_not_replace_current_ui():
    window = _Harness()
    token_a = window._begin_advice_request("structured")
    token_b = window._begin_advice_request("structured")
    assert (token_a, token_b) == (1, 2)

    window._on_structured_recommendation_finished(token_b, _structured_result())
    current_events = list(window.panel.events)
    window._on_structured_recommendation_finished(token_a, _structured_result())
    window._on_structured_recommendation_failed(token_a, "raw-like stale failure")

    assert window.panel.events == current_events
    assert window._is_current_advice_request("structured", token_b)
    assert all("2" not in event[-1] if isinstance(event[-1], str) else True for event in window.panel.events)


def test_stale_cleanup_releases_only_stale_object_and_preserves_current_worker_identity():
    window = _Harness()
    token_a = window._begin_advice_request("structured")
    old_thread, old_worker = _Thread(), object()
    token_b = window._begin_advice_request("structured")
    current_thread, current_worker = _Thread(), object()
    window._structured_thread, window._structured_worker = current_thread, current_worker

    window._cleanup_structured_worker(token_a, old_thread, old_worker)
    assert old_thread.deleted == 1
    assert window._structured_thread is current_thread and window._structured_worker is current_worker
    assert window._is_current_advice_request("structured", token_b)

    window._cleanup_structured_worker(token_b, current_thread, current_worker)
    assert current_thread.deleted == 1
    assert window._structured_thread is None and window._structured_worker is None
    assert window._active_advice_owner is None and window._active_advice_request_token is None


def test_cross_mode_stale_callback_and_legacy_stale_cleanup_cannot_damage_current_structured_request():
    window = _Harness()
    legacy_token = window._begin_advice_request("legacy")
    stale_thread, stale_worker = _Thread(), object()
    structured_token = window._begin_advice_request("structured")
    current_thread, current_worker = _Thread(), object()
    window._structured_thread, window._structured_worker = current_thread, current_worker

    window._on_llm_advice_finished(legacy_token, "legacy stale", {"usage": {}, "summary": {}})
    window._on_llm_advice_failed(legacy_token, "legacy stale failure")
    window._cleanup_llm_worker(legacy_token, stale_thread, stale_worker)

    assert not any(event[0] in {"text", "error"} for event in window.panel.events)
    assert stale_thread.deleted == 1
    assert window._is_current_advice_request("structured", structured_token)
    assert window._structured_thread is current_thread and window._structured_worker is current_worker
