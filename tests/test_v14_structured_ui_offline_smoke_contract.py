import inspect
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_offline_smoke_contract_has_mode_heading_and_existing_panel_only():
    panel = inspect.getsource(LLMAdvicePanel.set_mode_advice_text)
    assert "[기존 조언]" in panel and "[구조화 추천]" in panel
    assert "setPlainText" in panel


def test_structured_finish_formats_validated_model_not_raw_provider_data():
    source = inspect.getsource(MainWindow._on_structured_recommendation_finished)
    assert "format_recommendation_presentation_text" in source
    assert "response_payload" not in source and "raw_response" not in source
