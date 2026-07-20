import inspect

from ui.main_window import MainWindow, StructuredRecommendationWorker


def test_structured_start_blocks_duplicates_and_cleanup_clears_references():
    assert "if self._structured_thread is not None" in inspect.getsource(MainWindow._start_structured_recommendation)
    cleanup = inspect.getsource(MainWindow._cleanup_structured_worker)
    assert "deleteLater" in cleanup and "self._structured_thread = None" in cleanup and "self._structured_worker = None" in cleanup


def test_worker_signal_never_emits_exception_detail():
    source = inspect.getsource(StructuredRecommendationWorker.run)
    assert "self.failed.emit" in source and "str(exc)" not in source and "traceback" not in source
