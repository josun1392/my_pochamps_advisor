"""Decide / Record presentation and explicit ordinary-action authority boundaries."""

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

import ui.main_window as main_window_module
from core.move_repository import MoveView
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_switch_candidates import build_switch_candidate_context_projection
from ui.main_window import MainWindow
from ui.widgets.guided_turn_workspace import GuidedTurnWorkspace


def _window(*, complete: bool = True) -> MainWindow:
    QApplication.instance() or QApplication([])
    window = MainWindow()
    if complete:
        window.my_team_column.panels[0].pokemon_view = window.repo.get("pikachu")
        window.opponent_team_column.panels[0].pokemon_view = window.repo.get("pikachu")
    else:
        window.my_team_column.panels[0].pokemon_view = SimpleNamespace(en="pikachu")
        window.opponent_team_column.panels[0].pokemon_view = SimpleNamespace(en="eevee")
    return window


def _battle(*, complete: bool = True) -> MainWindow:
    window = _window(complete=complete)
    window.center_column.start_battle_button.click()
    return window


def test_garchomp_earthquake_tyranitar_after_ability_and_attack_stage_has_no_priority_gap(monkeypatch) -> None:
    window = _window()
    window.my_team_column.panels[0].pokemon_view = window.repo.get("garchomp")
    window.opponent_team_column.panels[0].pokemon_view = window.repo.get("tyranitar")
    own_panel = window.my_team_column.panels[0]
    own_panel.set_move(0, window.move_repo.get("earthquake"))

    window.center_column.start_battle_button.click()
    own_panel.select_move(0)

    class AbilityDialog:
        def __init__(self, **_kwargs):
            self.current_ability_confirmation = {
                "side": "self",
                "ability": "rough-skin",
                "status": "user_confirmed",
                "source": "user_confirmed_current_ability",
                "confidence": "known",
            }

        def exec(self):
            return QDialog.DialogCode.Accepted

    stage_confirmations = [
        {
            "side": "self",
            "stat": "attack",
            "stage": 0,
            "status": "user_confirmed",
            "source": "user_confirmed_current_stat_stage",
            "confidence": "known",
        },
        {
            "side": "opponent",
            "stat": "defense",
            "stage": 0,
            "status": "user_confirmed",
            "source": "user_confirmed_current_stat_stage",
            "confidence": "known",
        },
    ]

    class StageDialog:
        def __init__(self, **_kwargs):
            self.current_stat_stage_confirmation = stage_confirmations.pop(0)

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module, "CurrentAbilityDialog", AbilityDialog)
    monkeypatch.setattr(main_window_module, "CurrentStatStageDialog", StageDialog)
    window._open_current_ability_dialog()
    window._open_current_stat_stage_dialog()
    window._refresh_guided_turn_workspace()

    assert window.move_repo.get("earthquake").priority == 0
    paths = [
        entry.get("path")
        for entry in window._guided_readiness.get("missing", [])
        if isinstance(entry, dict)
    ]
    assert "self_move_priority" not in paths, window._guided_readiness
    assert "defender.defense_stage" in paths, window._guided_readiness
    assert window._guided_readiness["status"] == "incomplete"
    assert window._guided_readiness["unsupported"] == []
    defender_stage = next(
        entry
        for entry in window._guided_readiness["missing"]
        if entry.get("path") == "defender.defense_stage"
    )
    assert defender_stage["action"] == "current_stat_stage"

    window._open_readiness_input("current_stat_stage")
    window._refresh_guided_turn_workspace()

    after_paths = [
        entry.get("path")
        for entry in window._guided_readiness.get("missing", [])
        if isinstance(entry, dict)
    ]
    assert "defender.defense_stage" not in after_paths, window._guided_readiness
    assert "self_move_priority" not in after_paths, window._guided_readiness
    assert window._guided_readiness["unsupported"] == []
    assert ("opponent", "defense") in window._current_stat_stage_confirmations
    assert window._current_stat_stage_confirmations[("opponent", "defense")]["stage"] == 0
    window.close()


def test_minimal_garchomp_earthquake_tyranitar_bypasses_spurious_prankster_readiness() -> None:
    window = _window()
    window.my_team_column.panels[0].pokemon_view = window.repo.get("garchomp")
    window.opponent_team_column.panels[0].pokemon_view = window.repo.get("tyranitar")
    own_panel = window.my_team_column.panels[0]
    own_panel.set_move(0, window.move_repo.get("earthquake"))

    window.center_column.start_battle_button.click()
    own_panel.select_move(0)
    window._refresh_guided_turn_workspace()

    assert window._current_trusted_turn_number == 1
    assert window._guided_considered_action["move_id"] == "earthquake"
    paths = [entry.get("path") for entry in window._guided_readiness.get("missing", [])]
    assert "self.prankster_applied" not in paths
    assert paths
    assert any(
        isinstance(entry.get("action"), str)
        for entry in window._guided_readiness.get("missing", [])
        if isinstance(entry, dict)
    )
    assert window.center_column.guided_turn_workspace.readiness_input_button.isVisibleTo(
        window.center_column.guided_turn_workspace
    )
    window.close()


def test_new_battle_uses_selected_nonzero_active_slot_without_reordering_or_switch_observation() -> None:
    window = _window(complete=False)
    own_ids = ["pikachu", "raichu", "eevee", "vaporeon", "jolteon", "flareon"]
    opponent_ids = ["meowscarada", "garchomp", "rotom", "corviknight", "amoonguss", "torkoal"]
    for slot, pokemon_id in enumerate(own_ids):
        window.my_team_column.panels[slot].pokemon_view = SimpleNamespace(en=pokemon_id)
    for slot, pokemon_id in enumerate(opponent_ids):
        window.opponent_team_column.panels[slot].pokemon_view = SimpleNamespace(en=pokemon_id)
    window.select_slot("team_enemy", 5)
    assert window._observation_runtime_session_manager is None
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    assert manager is not None
    assert window._current_trusted_turn_number == 1
    stage = window.center_column.guided_turn_workspace
    assert stage.header_label.text() == "배틀: 진행 중 · 턴: 1"
    assert stage.phase == "decide"
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 0
    assert state["opponent_side"]["active_slot_index"] == 5
    assert {slot: row["pokemon_id"] for slot, row in state["self_side"]["pokemon"].items()} == dict(enumerate(own_ids))
    assert {slot: row["pokemon_id"] for slot, row in state["opponent_side"]["pokemon"].items()} == dict(enumerate(opponent_ids))
    projection = build_switch_candidate_context_projection(state)
    assert [(row["slot_index"], row["pokemon_id"]) for row in projection["self_pokemon"]] == list(enumerate(own_ids))
    assert manager.read_collection_snapshot()["ordered_observations"] == []
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    window.select_slot("team_enemy", 0)
    assert manager.read_collection_snapshot()["ordered_observations"] == []
    assert manager.read_state()["state"]["opponent_side"]["active_slot_index"] == 5
    for side in ("self_side", "opponent_side"):
        for pokemon in state[side]["pokemon"].values():
            assert all(is_unknown_battle_fact(pokemon[key]) for key in ("current_hp", "max_hp", "known_item", "condition"))
    assert "torkoal" in window.center_column.guided_turn_workspace.situation_label.text().lower()
    window.close()


def test_new_battle_restarts_at_turn_one_and_retires_turn_local_state_without_evidence() -> None:
    window = _battle(complete=False)
    old_session = window._active_session_id()
    window.set_current_turn_number(8)
    window._historical_predictive_action_bindings = {"old": object()}
    window._historical_multi_hit_predictions = {"old": object()}
    window._last_observed_rng_reconciliation = {"old": object()}
    stage = window.center_column.guided_turn_workspace
    stage.set_phase("record")
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    assert window._active_session_id() != old_session
    assert window._current_trusted_turn_number == 1
    assert stage.header_label.text() == "배틀: 진행 중 · 턴: 1"
    assert stage.phase == "decide"
    assert window._historical_predictive_action_bindings == {}
    assert window._historical_multi_hit_predictions == {}
    assert window._last_observed_rng_reconciliation is None
    assert manager.read_collection_snapshot()["ordered_observations"] == []
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    assert not window.read_c6_observed_transition_snapshot()["actor_transitions"]
    window.set_current_turn_number(4)
    assert window._current_trusted_turn_number == 4
    assert stage.header_label.text() == "배틀: 진행 중 · 턴: 4"
    window.close()


def _move(move_id: str) -> MoveView:
    return MoveView(move_id, move_id.title(), None, "electric", "special", 40, 100, 20)


def _presentation(*, overall: str = "tied_preferred_set") -> dict:
    return {"status": "resolved", "overall_status": overall,
            "preferred_frontier": ["attack:a", "attack:b"],
            "candidates": [
                {"candidate_id": "attack:a", "label": "기술 A", "evidence_class": "exact_outcome", "reason_labels": ["근거 A"]},
                {"candidate_id": "attack:b", "label": "기술 B", "evidence_class": "exact_outcome"},
                {"candidate_id": "attack:c", "label": "기술 C", "evidence_class": "incomplete", "incomplete_reason": "missing"},
            ]}


def test_center_uses_wide_decide_record_stage_and_retains_advanced() -> None:
    window = _window()
    center = window.center_column
    stage = center.guided_turn_workspace
    layout = window.centralWidget().layout()
    assert (layout.stretch(0), layout.stretch(1), layout.stretch(2)) == (25, 50, 25)
    assert stage.phase == "decide" and stage.stage_stack.currentWidget() is stage.decide_stage
    assert stage.board_scroll.minimumHeight() >= 240
    assert [stage.details_tabs.tabText(i) for i in range(stage.details_tabs.count())] == ["확률", "설명", "고급 입력"]
    assert stage.details_tabs.widget(2) is center.llm_advice_panel
    assert center.llm_advice_panel.current_state_section_label.text() == "현재 상태"
    assert center.llm_advice_panel.observed_section_label.text() == "관측 기록"
    assert center.llm_advice_panel.advanced_section_label.text() == "고급 / 특수"
    assert center.llm_advice_panel.llm_tools_section_label.text() == "LLM 도구"
    assert center.llm_advice_panel.reset_section_label.text() == "입력 표시 초기화"
    assert "추천 옵션" not in center.analysis_panel.output_edit.toPlainText()
    assert "87%" not in stage.probability_label.text()
    assert not hasattr(stage, "readiness_button")
    assert not hasattr(stage, "result_button")
    assert center.search_box is not None and center.move_search_box is not None
    assert window.my_team_column.panels and window.opponent_team_column.panels
    window.close()


def test_phase_change_is_only_presentation() -> None:
    window = _battle()
    stage = window.center_column.guided_turn_workspace
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()
    stage.record_phase_button.click()
    assert stage.phase == "record" and stage.stage_stack.currentWidget() is stage.record_stage
    stage.decide_phase_button.click()
    assert stage.phase == "decide"
    assert manager.read_collection_snapshot() == before
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    window.close()


def test_incomplete_ui_metadata_does_not_block_lifecycle_or_readiness() -> None:
    window = _battle(complete=False)
    stage = window.center_column.guided_turn_workspace
    assert window._active_session_id() == "ui-session-1"
    assert stage.header_label.text() == "배틀: 진행 중 · 턴: 1"
    assert "HP 미확인" in stage.situation_label.text()
    assert window._guided_readiness["status"] == "unavailable"
    window.set_current_turn_number(1)
    assert "턴: 1" in stage.header_label.text()
    assert "권한" not in stage.readiness_label.text()
    assert not window._observation_runtime_session_manager.read_collection_snapshot()["ordered_observations"]
    window.close()


def test_runtime_hp_only_and_complete_view_readiness(monkeypatch) -> None:
    window = _battle()
    stage = window.center_column.guided_turn_workspace
    assert stage.situation_label.text().count("HP 미확인") == 2
    assert "100/100" not in stage.situation_label.text()
    assert window._recommendation_readiness_owner == (window._active_session_id(), 0, "pikachu")
    window.set_current_turn_number(1)

    class HPDialog:
        def __init__(self, **_kwargs):
            self.current_hp_confirmations = [{"side": "self", "current_hp": 40, "maximum_hp": 100,
                                              "status": "user_confirmed", "source": "user_confirmed_current_hp"}]

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module, "CurrentHPDialog", HPDialog)
    window._open_current_hp_dialog()
    window._refresh_guided_turn_workspace()
    assert "HP 40/100" in stage.situation_label.text()
    assert "상대: pikachu (HP 미확인)" in stage.situation_label.text()
    window.close()


def test_considered_move_is_local_and_replaces_draft_without_evidence() -> None:
    window = _battle()
    window.set_current_turn_number(1)
    stage = window.center_column.guided_turn_workspace
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move("thunderbolt"))
    first = dict(window._guided_considered_action)
    assert first["move_slot"] == 1 and "고려 중" in stage.considered_label.text()
    stage.set_phase("record")
    assert "아직 기록되지 않음" in stage.record_ghost_label.text()
    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(1)
    assert stage.record_confirm_button.isEnabled()
    panel.set_move(1, _move("quick-attack"))
    assert window._guided_considered_action["move_id"] == "quick-attack"
    assert window._guided_considered_action["revision"] > first["revision"]
    assert not stage.execution_check.isChecked() and not stage.record_confirm_button.isEnabled()
    assert manager.read_collection_snapshot() == before
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    window.close()


def test_board_uses_only_presented_candidates_and_tied_frontier() -> None:
    QApplication.instance() or QApplication([])
    stage = GuidedTurnWorkspace()
    assert stage.candidate_rows == []
    stage.set_recommendation(_presentation())
    assert len(stage.candidate_rows) == 3
    titles = [row.layout().itemAt(0).widget().text() for row in stage.candidate_rows]
    assert titles[:2] == ["★ 분석상 선호 · 기술 A", "★ 분석상 선호 · 기술 B"]
    assert titles[2] == "기술 C"
    assert "분석 불완전" in stage.candidate_rows[2].layout().itemAt(1).widget().text()
    assert "87%" not in " ".join(titles)
    stage.set_board_state("상태가 변경되어 다시 분석이 필요합니다.")
    assert stage.candidate_rows == [] and "다시 분석" in stage.board_empty_label.text()


def test_explicit_strategy_updates_board_and_failed_retry_clears_star(monkeypatch) -> None:
    window = _battle()
    window.set_current_turn_number(1)
    window.my_team_column.panels[0].set_move(0, _move("thunderbolt"))
    stage = window.center_column.guided_turn_workspace
    calls = []
    outcomes = [{"status": "resolved", "explanation": {"schema_version": "test"}}, {"status": "unsupported"}]
    monkeypatch.setattr(main_window_module, "run_current_ui_detached_strategy",
                        lambda **_kwargs: calls.append(True) or outcomes.pop(0))
    panel = window.center_column.llm_advice_panel
    monkeypatch.setattr(panel, "set_strategy_explanation", lambda _explanation: _presentation())
    assert calls == []
    stage.analysis_button.click()
    assert calls == [True] and len(stage.candidate_rows) == 3
    stage.analysis_button.click()
    assert calls == [True, True]
    assert stage.candidate_rows == [] and "분석을 완료" in stage.board_empty_label.text()
    assert "★" not in stage.board_empty_label.text()
    assert "분석을 완료" in window.center_column.analysis_panel.output_edit.toPlainText()
    window.close()


def test_runtime_or_move_change_retires_board_and_explanation() -> None:
    window = _battle()
    window.set_current_turn_number(1)
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move("thunderbolt"))
    stage = window.center_column.guided_turn_workspace
    window._guided_analysis_basis = window._guided_current_basis()
    window._guided_analysis_text = "분석 완료"
    stage.set_recommendation(_presentation())
    panel.set_move(1, _move("quick-attack"))
    assert stage.candidate_rows == []
    assert "다시 분석" in stage.analysis_label.text()
    assert "이전 전략 분석" in window.center_column.analysis_panel.output_edit.toPlainText()
    window.close()


def test_contextual_readiness_skip_and_input_route_are_read_only(monkeypatch) -> None:
    window = _battle()
    stage = window.center_column.guided_turn_workspace
    window._guided_basis = window._guided_current_basis()
    window._guided_readiness = {"status": "incomplete", "missing": [{"label": "Current HP needed", "action": "current_hp"}]}
    window._refresh_guided_turn_workspace()
    assert "현재 HP" in stage.readiness_label.text()
    assert stage.readiness_input_button.text() == "현재 HP 입력"
    before = window._observation_runtime_session_manager.read_collection_snapshot()
    stage.readiness_skip_button.click()
    assert "모르는 정보" in stage.readiness_label.text()
    assert window._observation_runtime_session_manager.read_collection_snapshot() == before
    stage.set_readiness("현재 HP를 알고 있다면 입력하세요.", "current_hp", "현재 HP", basis="new")

    class CancelHPDialog:
        def __init__(self, **_kwargs): pass
        def exec(self): return QDialog.DialogCode.Rejected

    monkeypatch.setattr(main_window_module, "CurrentHPDialog", CancelHPDialog)
    stage.readiness_input_button.click()
    assert window._observation_runtime_session_manager.read_collection_snapshot() == before
    window.close()


def test_record_ghost_draft_clear_and_final_commit_use_existing_observer(monkeypatch) -> None:
    window = _battle()
    window.set_current_turn_number(1)
    window.my_team_column.panels[0].set_move(0, _move("thunderbolt"))
    stage = window.center_column.guided_turn_workspace
    stage.set_phase("record")
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()
    assert "아직 기록되지 않음" in stage.record_ghost_label.text()
    assert not stage.record_confirm_button.isEnabled()
    stage.execution_check.setChecked(True)
    assert not stage.record_confirm_button.isEnabled()
    stage.result_combo.setCurrentIndex(2)
    assert stage.result_combo.currentData() == "accuracy_miss"
    assert stage.record_confirm_button.isEnabled()
    assert manager.read_collection_snapshot() == before
    stage.record_clear_button.click()
    assert manager.read_collection_snapshot() == before
    called = []
    monkeypatch.setattr(window, "_confirm_previous_action_history", lambda **kwargs: called.append(kwargs) or {"status": "resolved"})
    monkeypatch.setattr(main_window_module.QInputDialog, "getItem", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("technical dialog opened")))
    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(2)
    stage.record_confirm_button.click()
    assert called == [{"side": "self", "execution_move_id": "thunderbolt",
                       "selected_move_id": "thunderbolt", "result_class": "accuracy_miss"}]
    assert stage._recorded and not stage.record_confirm_button.isEnabled()
    assert stage.result_combo.itemData(1) == "success"
    assert stage.result_combo.itemData(3) == "protection_block"
    assert stage.result_combo.itemData(4) is None
    window.close()


def test_record_unknown_result_is_distinct_and_next_turn_is_explicit(monkeypatch) -> None:
    window = _battle()
    stage = window.center_column.guided_turn_workspace
    stage.set_phase("record")
    assert window._current_trusted_turn_number == 1
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move("thunderbolt"))
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()
    monkeypatch.setattr(main_window_module.QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Cancel)
    stage.next_turn_button.click()
    assert window._current_trusted_turn_number == 1
    monkeypatch.setattr(main_window_module.QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Yes)
    stage.next_turn_button.click()
    assert window._current_trusted_turn_number == 2
    assert stage.phase == "decide" and window._guided_considered_action is None
    assert stage.candidate_rows == [] and manager.read_collection_snapshot() == before
    window.close()


def test_turn_change_retires_move_highlight_but_preserves_assignment_and_all_other_slots() -> None:
    window = _battle()
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move("thunderbolt"))
    panel.selected_moves[1] = _move("quick-attack")
    assigned = list(panel.selected_moves)
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()
    assert window._guided_considered_action["move_id"] == "thunderbolt"
    assert "background-color: #4A90E2" in panel.move_buttons[0].styleSheet()

    window.set_current_turn_number(2)

    assert window._guided_considered_action is None
    assert panel.selected_move_index is None
    assert panel.selected_moves == assigned
    assert panel.move_buttons[0].text() == "Thunderbolt"
    assert "background-color: #4A90E2" not in panel.move_buttons[0].styleSheet()
    assert manager.read_collection_snapshot() == before
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    assert not window.read_c6_observed_transition_snapshot()["actor_transitions"]

    panel.select_move(0)
    assert window._guided_considered_action["move_id"] == "thunderbolt"
    assert window._guided_considered_action["turn_number"] == 2
    assert "background-color: #4A90E2" in panel.move_buttons[0].styleSheet()
    window.close()


def test_no_record_next_turn_retires_stale_move_highlight(monkeypatch) -> None:
    window = _battle()
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move("thunderbolt"))
    stage = window.center_column.guided_turn_workspace
    stage.set_phase("record")
    before = window._observation_runtime_session_manager.read_collection_snapshot()
    monkeypatch.setattr(main_window_module.QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Yes)

    stage.next_turn_button.click()

    assert window._current_trusted_turn_number == 2
    assert window._guided_considered_action is None
    assert panel.selected_move_index is None
    assert panel.selected_moves[0].move_id == "thunderbolt"
    assert "background-color: #4A90E2" not in panel.move_buttons[0].styleSheet()
    assert window._observation_runtime_session_manager.read_collection_snapshot() == before
    window.close()


def test_new_battle_same_turn_one_retires_move_highlight_without_clearing_assignment() -> None:
    window = _battle()
    panel = window.my_team_column.panels[0]
    panel.set_move(0, _move("thunderbolt"))
    first_session = window._active_session_id()
    assert window._current_trusted_turn_number == 1
    assert "background-color: #4A90E2" in panel.move_buttons[0].styleSheet()

    window.center_column.start_battle_button.click()

    assert window._active_session_id() != first_session
    assert window._current_trusted_turn_number == 1
    assert window._guided_considered_action is None
    assert panel.selected_move_index is None
    assert panel.selected_moves[0].move_id == "thunderbolt"
    assert panel.move_buttons[0].text() == "Thunderbolt"
    assert "background-color: #4A90E2" not in panel.move_buttons[0].styleSheet()
    assert not window._observation_runtime_session_manager.read_collection_snapshot()["ordered_observations"]
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    assert not window.read_c6_observed_transition_snapshot()["actor_transitions"]
    window.close()


def test_inline_final_confirm_writes_only_existing_previous_action_events() -> None:
    window = _battle()
    window.set_current_turn_number(1)
    window.my_team_column.panels[0].set_move(0, _move("thunderbolt"))
    stage = window.center_column.guided_turn_workspace
    stage.set_phase("record")
    manager = window._observation_runtime_session_manager
    assert not manager.read_collection_snapshot()["ordered_observations"]
    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(2)
    assert not manager.read_collection_snapshot()["ordered_observations"]
    stage.record_confirm_button.click()
    rows = manager.read_collection_snapshot()["ordered_observations"]
    assert [row["event_kind"] for row in rows] == ["executed_move_observed", "previous_action_result_observed"]
    assert rows[1]["payload"]["result_class"] == "accuracy_miss"
    assert stage._recorded
    window.close()


def test_confirmed_execution_with_unknown_result_does_not_claim_success() -> None:
    window = _battle()
    window.set_current_turn_number(1)
    window.my_team_column.panels[0].set_move(0, _move("thunderbolt"))
    stage = window.center_column.guided_turn_workspace
    stage.set_phase("record")
    stage.execution_check.setChecked(True)
    stage.result_combo.setCurrentIndex(4)
    stage.record_confirm_button.click()
    rows = window._observation_runtime_session_manager.read_collection_snapshot()["ordered_observations"]
    assert any(row["event_kind"] == "executed_move_observed" for row in rows)
    assert all(row.get("payload", {}).get("result_class") != "success" for row in rows)
    assert "결과 미확인" in stage.record_status_label.text()
    window.close()


def test_exact_probability_tab_has_scope_and_no_invented_numbers() -> None:
    QApplication.instance() or QApplication([])
    stage = GuidedTurnWorkspace()
    assert "표시할 정확한 확률이 없습니다" in stage.probability_label.text()
    stage.set_probability_metrics({"attack:a": {
        "status": "resolved", "schema_version": "exact-outcome-descriptive-metrics-v1",
        "horizon": "immediate_action_consequence", "candidate_id": "attack:a",
        "target": {"status": "resolved", "ko_probability": {"numerator": 4, "denominator": 5}},
        "own": {"status": "resolved", "self_faint_probability": {"numerator": 0, "denominator": 1}},
    }})
    assert "즉시 내 행동 결과" in stage.probability_label.text()
    assert "상대 즉시 기절: 4/5" in stage.probability_label.text()
    assert "내 즉시 기절: 0/1" in stage.probability_label.text()
    stage.set_probability_metrics(None)
    assert "4/5" not in stage.probability_label.text()
