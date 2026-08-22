from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

import ui.main_window as main_window_subject
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _manager():
    state = create_unknown_bootstrap_battle_state("strategy-ui", "active", "opponent")["state"]
    return BattleObservationRuntimeSessionManager.create("strategy-ui", state)["manager"]


def test_strategy_button_has_its_own_signal_and_never_emits_gemini_signals() -> None:
    app = QApplication.instance() or QApplication([]); assert app is not None
    panel = LLMAdvicePanel(); events = []
    panel.advice_requested.connect(lambda: events.append("legacy_gemini"))
    panel.structured_advice_requested.connect(lambda: events.append("structured_gemini"))
    panel.deterministic_strategy_requested.connect(lambda: events.append("deterministic"))

    panel.deterministic_strategy_button.click()

    assert panel.deterministic_strategy_button.text() == "전략 분석"
    assert events == ["deterministic"]
    panel.set_running(True)
    assert not panel.deterministic_strategy_button.isEnabled()


class _Panel:
    def __init__(self): self.explanations = []; self.text = []
    def set_strategy_explanation(self, explanation): self.explanations.append(explanation)
    def set_advice_text(self, text): self.text.append(text)


class _Harness:
    _start_deterministic_strategy_analysis = MainWindow._start_deterministic_strategy_analysis
    _active_session_id = MainWindow._active_session_id

    def __init__(self):
        self._observation_runtime_session_manager = _manager()
        self.center_column = SimpleNamespace(llm_advice_panel=_Panel())
        self.messages = []
    def statusBar(self): return SimpleNamespace(showMessage=lambda message: self.messages.append(message))


def test_main_window_activation_delegates_only_to_closed_bridge(monkeypatch) -> None:
    window = _Harness(); calls = []
    expected = {"status": "resolved", "explanation": {"schema_version": "deterministic-strategy-explanation-v1"}}
    monkeypatch.setattr(main_window_subject, "run_current_ui_detached_strategy", lambda **kwargs: calls.append(kwargs) or expected)

    window._start_deterministic_strategy_analysis()

    assert len(calls) == 1
    assert calls[0]["runtime_session_manager"] is window._observation_runtime_session_manager
    assert calls[0]["decision_side"] == "self" and "decision_owner" not in calls[0]
    assert callable(calls[0]["selection_cycle_builder"])
    assert window.center_column.llm_advice_panel.explanations == [expected["explanation"]]
    assert window.messages == ["전략 분석 완료"]


def test_main_window_activation_surfaces_stale_without_presenting_old_explanation(monkeypatch) -> None:
    window = _Harness()
    monkeypatch.setattr(main_window_subject, "run_current_ui_detached_strategy", lambda **_: {"status": "stale"})

    window._start_deterministic_strategy_analysis()

    assert window.center_column.llm_advice_panel.explanations == []
    assert "폐기" in window.center_column.llm_advice_panel.text[0]
