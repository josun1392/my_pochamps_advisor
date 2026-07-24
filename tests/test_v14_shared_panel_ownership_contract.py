import inspect
from ui.main_window import MainWindow


def test_shared_panel_tracks_owner_and_suppresses_stale_cross_mode_results():
    source = inspect.getsource(MainWindow)
    assert "_active_advice_owner" in source and "_active_advice_request_token" in source
    assert "_is_current_advice_request" in source and "_begin_advice_request" in source


def test_owner_is_cleared_with_each_worker_cleanup():
    assert "_clear_current_advice_request" in inspect.getsource(MainWindow._cleanup_llm_worker)
    assert "_clear_current_advice_request" in inspect.getsource(MainWindow._cleanup_structured_worker)
