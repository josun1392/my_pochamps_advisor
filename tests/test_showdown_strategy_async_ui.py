"""Qt background native evaluation, freshness, session isolation and cancellation."""
from copy import deepcopy
import os
from time import monotonic
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QLabel
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from advisor.showdown_bridge import ShowdownBridgeError
from llm.advisor_ui_detached_strategy_bridge import run_current_ui_detached_strategy
from tests.test_showdown_strategy_evaluation import configuration
from ui.main_window import MainWindow


def pump(app, predicate, timeout=10):
    deadline = monotonic() + timeout
    while not predicate() and monotonic() < deadline:
        app.processEvents()
    assert predicate(), "native Qt worker did not finish"


@pytest.fixture
def window():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    snapshot, builder, context = configuration(horizon=16)
    manager = BattleObservationRuntimeSessionManager.create(snapshot["session_id"], snapshot["state"])["manager"]
    window._observation_runtime_session_manager = manager
    window.configure_showdown_shadow(checkout=checkout, context=context, experimental_ranking=True)
    yield app, window, manager, snapshot, builder
    window.configure_showdown_shadow()
    pump(app, lambda: window._showdown_evaluation_thread is None)
    window.close()
    app.processEvents()


def prepare(window, manager, snapshot, builder):
    result = run_current_ui_detached_strategy(runtime_session_manager=manager, captured_session_id=snapshot["session_id"],
        selection_cycle_builder=builder, showdown_context=window._showdown_shadow_context,
        showdown_bridge=window._showdown_shadow_worker, showdown_experimental_ranking=True, defer_showdown_evaluation=True)
    assert result["status"] == "resolved"
    assert result["explanation"]["sampled_simulation"]["status"] == "pending"
    assert window._showdown_shadow_worker._process is None
    window.center_column.llm_advice_panel.set_strategy_explanation(result["explanation"])
    return result


def test_native_background_keeps_qt_events_alive_and_truth_unchanged(window):
    app, window, manager, snapshot, builder = window
    result = prepare(window, manager, snapshot, builder)
    before = manager.capture_runtime_state_snapshot(snapshot["session_id"])
    ledger = manager.read_applied_ledger()
    ticks = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start()
    window._start_showdown_evaluation(result)
    pump(app, lambda: window._showdown_evaluation_thread is None)
    timer.stop()
    text = window.center_column.llm_advice_panel.output_edit.toPlainText()
    assert "미완료" in text and "실험 순위 (기본 추천에 미적용)" in text, text
    assert "네이티브 조건부 표본 평가 완료" in window.statusBar().currentMessage()
    assert len(ticks) >= 3
    assert manager.capture_runtime_state_snapshot(snapshot["session_id"]) == before
    assert manager.read_applied_ledger() == ledger


def test_session_change_discards_background_result(window):
    app, window, manager, snapshot, builder = window
    result = prepare(window, manager, snapshot, builder)
    window._start_showdown_evaluation(result)
    other = deepcopy(snapshot["state"])
    other["session_id"] = "new-live-session"
    # Use the manager's existing session transition authority.
    replacement = BattleObservationRuntimeSessionManager.create("new-live-session", other)
    assert replacement["status"] == "session_ready", replacement
    window._observation_runtime_session_manager = replacement["manager"]
    pump(app, lambda: window._showdown_evaluation_thread is None)
    assert "실험 순위" not in window.center_column.llm_advice_panel.output_edit.toPlainText()


def test_disable_during_execution_cancels_local_process_and_cannot_install_result(window):
    app, window, manager, snapshot, builder = window
    result = prepare(window, manager, snapshot, builder)
    window._start_showdown_evaluation(result)
    bridge = window._showdown_shadow_worker
    pump(app, lambda: bridge._process is not None)
    started = monotonic()
    process = bridge._process
    window.configure_showdown_shadow()
    assert monotonic() - started < 2
    pump(app, lambda: window._showdown_evaluation_thread is None)
    assert process.poll() is not None
    assert bridge._process is None
    with pytest.raises(ShowdownBridgeError, match="showdown_cancelled"):
        bridge.run({})
    assert "실험 순위" not in window.center_column.llm_advice_panel.output_edit.toPlainText()
    assert manager.read_applied_ledger() == {}


def test_actual_strategy_button_runs_existing_selection_producer_and_native_ui_path(window, monkeypatch):
    app, window, manager, snapshot, builder = window
    for column, species in (("team_my", "charizard"), ("team_enemy", "scizor")):
        panel = window._slot_panel(column, 0)
        panel.set_pokemon(window.repo.get(species))
        window.selected_slots[column] = 0
    own = window._slot_panel("team_my", 0)
    own.selected_moves = [window.move_repo.get("flamethrower"), window.move_repo.get("air-slash"), window.move_repo.get("protect"), None]
    own.selected_move_index = 0
    bench = window._slot_panel("team_my", 1)
    bench.set_pokemon(window.repo.get("garchomp"))
    before = manager.capture_runtime_state_snapshot(snapshot["session_id"])
    import ui.main_window as subject
    original = subject.run_current_ui_detached_strategy
    captured = []
    def record(**kwargs):
        build = kwargs["selection_cycle_builder"]
        def record_cycle(*args):
            cycle = build(*args)
            captured.append({"prepared_status": cycle.get("status"), "errors": cycle.get("errors")})
            return cycle
        kwargs["selection_cycle_builder"] = record_cycle
        result = original(**kwargs)
        captured.append(result)
        return result
    monkeypatch.setattr(subject, "run_current_ui_detached_strategy", record)
    window.center_column.llm_advice_panel.deterministic_strategy_button.click()
    assert window._showdown_evaluation_thread is not None, captured
    assert {a["action_id"] for a in captured[-1]["native_evaluation_job"]["selection"]["actions"]} == {
        "attack:flamethrower", "attack:air-slash", "attack:protect", "manual_switch:garchomp"}
    pump(app, lambda: window._showdown_evaluation_thread is None)
    text = window.center_column.llm_advice_panel.output_edit.toPlainText()
    assert "한도 내 표본 승리비율" in text, text
    assert "manual_switch:garchomp" in text, text
    labels = window.center_column.guided_turn_workspace.findChildren(QLabel, "showdownConditionalEvidence")
    assert len(labels) == 4
    assert all("정확 확률 아님" in label.text() for label in labels)
    assert manager.capture_runtime_state_snapshot(snapshot["session_id"]) == before
    assert manager.read_applied_ledger() == {}
    window.configure_showdown_shadow()
    assert "네이티브 가정 평가를 해제" in window.center_column.llm_advice_panel.output_edit.toPlainText()
    assert window.center_column.guided_turn_workspace.candidate_rows == []


def test_rollback_does_not_revive_an_old_default_explanation_after_session_change(window):
    app, window, manager, snapshot, builder = window
    result = prepare(window, manager, snapshot, builder)
    window._start_showdown_evaluation(result)
    pump(app, lambda: window._showdown_evaluation_thread is None)
    assert window._showdown_displayed_explanation is not None
    other = deepcopy(snapshot["state"])
    other["session_id"] = "replacement-session"
    replacement = BattleObservationRuntimeSessionManager.create("replacement-session", other)
    window._observation_runtime_session_manager = replacement["manager"]
    window.configure_showdown_shadow()
    text = window.center_column.llm_advice_panel.output_edit.toPlainText()
    assert "현재 관측에서 기존 전략 분석을 다시 실행" in text
    assert "실험 순위" not in text
    assert window.center_column.guided_turn_workspace.candidate_rows == []
