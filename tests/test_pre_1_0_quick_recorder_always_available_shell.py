"""Always-available Quick Recorder presentation over existing strict observers."""

from __future__ import annotations

from copy import deepcopy

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

import ui.main_window as main_window_module
from core.move_repository import MoveView
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from ui.main_window import MainWindow
from ui.widgets.guided_turn_workspace import GuidedTurnWorkspace


def _move(move_id: str = "thunderbolt") -> MoveView:
    return MoveView(move_id, move_id.title(), None, "electric", "special", 40, 100, 20)


def _battle() -> MainWindow:
    QApplication.instance() or QApplication([])
    window = MainWindow()
    window.my_team_column.panels[0].pokemon_view = window.repo.get("pikachu")
    window.opponent_team_column.panels[0].pokemon_view = window.repo.get("pikachu")
    window.center_column.start_battle_button.click()
    return window


def _consider_move(window: MainWindow, move_id: str = "thunderbolt") -> None:
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move(move_id))
    assert window._guided_considered_action["move_id"] == move_id


def _open_recorder(window: MainWindow) -> GuidedTurnWorkspace:
    stage = window.center_column.guided_turn_workspace
    stage.record_phase_button.click()
    assert stage.phase == "record"
    assert not stage.record_stage.isHidden()
    return stage


def _presentation() -> dict:
    return {
        "status": "resolved",
        "overall_status": "uniquely_preferred",
        "preferred_frontier": ["attack:a"],
        "candidates": [
            {
                "candidate_id": "attack:a",
                "label": "Thunderbolt",
                "evidence_class": "exact_outcome",
                "reason_labels": ["test"],
            }
        ],
    }


def test_default_decision_workspace_remains_visible_and_recorder_is_collapsed() -> None:
    window = _battle()
    stage = window.center_column.guided_turn_workspace

    assert window._current_trusted_turn_number == 1
    assert stage.phase == "decide"
    assert stage.stage_stack.currentWidget() is stage.decide_stage
    assert stage.record_stage.isHidden()
    assert not stage.board_scroll.isHidden()
    assert not stage.analysis_button.isHidden()
    assert not stage.next_turn_button.isHidden()
    window.close()


def test_open_and_close_recorder_never_replaces_decision_workspace_or_writes_truth() -> None:
    window = _battle()
    _consider_move(window)
    stage = window.center_column.guided_turn_workspace
    stage.set_recommendation(_presentation())
    manager = window._observation_runtime_session_manager
    before = deepcopy(manager.read_collection_snapshot())

    _open_recorder(window)

    assert stage.stage_stack.currentWidget() is stage.decide_stage
    assert not stage.board_scroll.isHidden()
    assert len(stage.candidate_rows) == 1
    assert "Thunderbolt" in stage.considered_label.text()
    assert "Thunderbolt" in stage.record_ghost_label.text()

    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(2)
    assert stage.record_confirm_button.isEnabled()
    assert manager.read_collection_snapshot() == before

    stage.decide_phase_button.click()

    assert stage.phase == "decide"
    assert stage.record_stage.isHidden()
    assert stage.execution_check.isChecked()
    assert stage.result_combo.currentData() == "accuracy_miss"
    assert len(stage.candidate_rows) == 1
    assert manager.read_collection_snapshot() == before
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    assert not window.read_c6_observed_transition_snapshot()["actor_transitions"]
    window.close()


@pytest.mark.parametrize(
    ("combo_index", "expected_result"),
    [
        (1, "success"),
        (2, "accuracy_miss"),
        (3, "protection_block"),
    ],
)
def test_explicit_commit_reuses_existing_previous_action_result_classes(
    combo_index: int, expected_result: str,
) -> None:
    window = _battle()
    _consider_move(window)
    stage = _open_recorder(window)
    manager = window._observation_runtime_session_manager

    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(combo_index)
    assert manager.read_collection_snapshot()["ordered_observations"] == []

    stage.record_confirm_button.click()

    rows = manager.read_collection_snapshot()["ordered_observations"]
    assert [row["event_kind"] for row in rows] == [
        "executed_move_observed",
        "previous_action_result_observed",
    ]
    assert rows[1]["payload"]["result_class"] == expected_result
    assert stage._recorded
    window.close()


def test_explicit_commit_preserves_execution_confirmed_result_unknown() -> None:
    window = _battle()
    _consider_move(window)
    stage = _open_recorder(window)
    manager = window._observation_runtime_session_manager

    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(4)
    stage.record_confirm_button.click()

    rows = manager.read_collection_snapshot()["ordered_observations"]
    assert any(row["event_kind"] == "executed_move_observed" for row in rows)
    assert all(row.get("payload", {}).get("result_class") != "success" for row in rows)
    assert "결과 미확인" in stage.record_status_label.text()
    window.close()


def test_stale_considered_action_fails_closed_without_observation() -> None:
    window = _battle()
    _consider_move(window)
    stage = _open_recorder(window)
    manager = window._observation_runtime_session_manager
    before = deepcopy(manager.read_collection_snapshot())

    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(1)
    window._guided_considered_action = {
        **window._guided_considered_action,
        "revision": window._guided_considered_action["revision"] + 1,
    }
    stage.record_confirm_button.click()

    assert manager.read_collection_snapshot() == before
    assert "달라졌습니다" in stage.record_status_label.text()
    window.close()


def test_active_identity_change_prevents_wrong_owner_recording() -> None:
    window = _battle()
    _consider_move(window)
    stage = _open_recorder(window)
    old_manager = window._observation_runtime_session_manager
    state = old_manager.read_state()["state"]
    state["self_side"]["pokemon"][1] = {
        **deepcopy(state["self_side"]["pokemon"][0]),
        "pokemon_id": "eevee",
    }
    state["self_side"]["active_slot_index"] = 1
    recreated = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert recreated["status"] == "session_ready"
    window._observation_runtime_session_manager = recreated["manager"]
    manager = window._observation_runtime_session_manager

    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(1)
    stage.record_confirm_button.click()

    assert manager.read_collection_snapshot()["ordered_observations"] == []
    assert "활성 포켓몬이 달라졌습니다" in stage.record_status_label.text()
    window.close()


def test_quick_recorder_shortcuts_keep_existing_mainwindow_entry_points(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        MainWindow,
        "_open_pokemon_switch_confirmation",
        lambda self: calls.append("switch"),
    )
    monkeypatch.setattr(
        MainWindow,
        "_open_current_hp_dialog",
        lambda self: calls.append("hp"),
    )
    monkeypatch.setattr(
        MainWindow,
        "_open_current_condition_dialog",
        lambda self: calls.append("condition"),
    )

    window = _battle()
    stage = _open_recorder(window)
    stage.switch_button.click()
    stage.current_hp_button.click()
    stage.condition_button.click()

    assert calls == ["switch", "hp", "condition"]
    window.close()


def test_successful_record_invalidates_stale_recommendation_without_auto_analysis(monkeypatch) -> None:
    window = _battle()
    _consider_move(window)
    stage = window.center_column.guided_turn_workspace
    stage.set_recommendation(_presentation())
    window._guided_analysis_basis = window._guided_current_basis()
    window._guided_analysis_text = "분석 완료"
    analysis_calls: list[bool] = []
    monkeypatch.setattr(
        window,
        "_start_deterministic_strategy_analysis",
        lambda: analysis_calls.append(True),
    )

    _open_recorder(window)
    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(1)
    stage.record_confirm_button.click()

    assert analysis_calls == []
    assert stage.candidate_rows == []
    assert "다시 분석" in stage.analysis_label.text()
    window.close()


def test_explicit_next_turn_remains_available_and_unknown_outcome_can_advance(monkeypatch) -> None:
    window = _battle()
    _consider_move(window)
    stage = _open_recorder(window)
    manager = window._observation_runtime_session_manager
    before = deepcopy(manager.read_collection_snapshot())

    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *_args: QMessageBox.StandardButton.Cancel,
    )
    stage.next_turn_button.click()
    assert window._current_trusted_turn_number == 1

    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    stage.next_turn_button.click()

    assert window._current_trusted_turn_number == 2
    assert stage.phase == "decide"
    assert stage.record_stage.isHidden()
    assert not stage.execution_check.isChecked()
    assert stage.result_combo.currentData() == "unselected"
    assert stage.candidate_rows == []
    assert manager.read_collection_snapshot() == before
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    assert not window.read_c6_observed_transition_snapshot()["actor_transitions"]
    window.close()


def test_expanded_recorder_has_resizable_usable_height_without_hiding_decision_area() -> None:
    window = _battle()
    _consider_move(window)
    stage = _open_recorder(window)

    assert stage.decision_splitter.orientation() == Qt.Orientation.Vertical
    assert stage.decision_splitter.count() == 2
    assert stage.decision_splitter.widget(0) is stage.decision_content
    assert stage.decision_splitter.widget(1) is stage.record_stage
    assert stage.record_stage.minimumHeight() >= 220
    assert stage.record_body_scroll.minimumHeight() >= 185
    assert stage.board_scroll.minimumHeight() >= 180
    assert not stage.board_scroll.isHidden()
    assert not stage.next_turn_button.isHidden()

    stage.decision_splitter.setSizes([300, 260])
    sizes = stage.decision_splitter.sizes()
    assert len(sizes) == 2 and sizes[0] > 0 and sizes[1] > 0

    stage.decide_phase_button.click()
    assert stage.record_stage.isHidden()
    stage.record_phase_button.click()
    reopened = stage.decision_splitter.sizes()
    assert reopened[0] > 0 and reopened[1] > 0
    window.close()


def test_normal_desktop_geometry_keeps_recorder_and_recommendation_readable() -> None:
    app = QApplication.instance() or QApplication([])
    window = _battle()
    _consider_move(window)
    window.resize(1280, 720)
    window.show()
    app.processEvents()

    stage = _open_recorder(window)
    app.processEvents()

    assert stage.record_stage.height() >= 220
    assert stage.record_body_scroll.height() >= 185
    assert stage.board_scroll.height() >= 180
    assert stage.next_turn_button.isVisibleTo(window)
    assert stage.record_confirm_button.isVisibleTo(window)
    assert stage.result_combo.isVisibleTo(window)
    assert stage.execution_check.isVisibleTo(window)
    window.close()
