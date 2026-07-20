import inspect
from ui.main_window import MainWindow


def test_shared_panel_tracks_owner_and_suppresses_stale_cross_mode_results():
    source = inspect.getsource(MainWindow)
    assert "_active_advice_owner" in source and "_advice_request_sequence" in source
    assert 'self._active_advice_owner != "legacy"' in source
    assert 'self._active_advice_owner != "structured"' in source


def test_owner_is_cleared_with_each_worker_cleanup():
    assert 'self._active_advice_owner = None' in inspect.getsource(MainWindow._cleanup_llm_worker)
    assert 'self._active_advice_owner = None' in inspect.getsource(MainWindow._cleanup_structured_worker)
