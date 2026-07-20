import inspect

from ui.widgets.llm_advice_panel import LLMAdvicePanel


PRESENTATION_FIELDS = {
    "status", "recommended_move", "recommended_slot_index", "primary_reasons",
    "risks", "alternatives", "candidate_summaries", "errors",
}
FORBIDDEN_HANDOFF_FIELDS = {"raw_response", "provider", "repository", "ui_object", "api_key", "traceback", "network_config"}


def test_validated_presentation_handoff_is_structured_and_excludes_provider_owned_data():
    assert not (PRESENTATION_FIELDS & FORBIDDEN_HANDOFF_FIELDS)
    assert {"recommended_move", "recommended_slot_index", "candidate_summaries"} <= PRESENTATION_FIELDS


def test_current_panel_remains_text_only_until_t1_approved_ui_change():
    source = inspect.getsource(LLMAdvicePanel)
    assert "def set_advice_text" in source and "def set_error" in source
    assert "build_recommendation_presentation_model" not in source
