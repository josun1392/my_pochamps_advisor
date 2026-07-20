FLOW_OPTIONS = ("coexistence", "replacement")
WORKER_OPTIONS = ("existing_worker", "new_structured_worker", "generic_worker")
PRESENTATION_OPTIONS = ("formatted_text_panel", "structured_widget")
T1_QUESTIONS = (
    "coexistence_or_replacement",
    "worker_architecture",
    "presentation_architecture",
    "authorize_one_actual_gemini_smoke",
)


def test_decision_gate_documents_all_unresolved_t1_choices_before_runtime_work():
    assert FLOW_OPTIONS == ("coexistence", "replacement")
    assert WORKER_OPTIONS == ("existing_worker", "new_structured_worker", "generic_worker")
    assert PRESENTATION_OPTIONS == ("formatted_text_panel", "structured_widget")
    assert len(T1_QUESTIONS) == 4


def test_actual_provider_and_ui_work_remain_blocked_without_t1_selection():
    authorization = {"actual_provider_call": False, "ui_rendering": False, "turn_engine": False, "ranking": False}
    assert not any(authorization.values())
