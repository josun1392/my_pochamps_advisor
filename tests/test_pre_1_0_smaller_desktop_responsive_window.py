from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QScrollArea

from ui.main_window import MainWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dual_type_view(name: str):
    return SimpleNamespace(
        ko="누리레느",
        en=name,
        base_stats={
            "hp": 80,
            "attack": 74,
            "defense": 74,
            "special-attack": 126,
            "special-defense": 116,
            "speed": 60,
        },
        types_ko=["물", "페어리"],
    )


def _inside(widget, owner) -> bool:
    top_left = widget.mapTo(owner, widget.rect().topLeft())
    bottom_right = widget.mapTo(owner, widget.rect().bottomRight())
    return (
        top_left.x() >= 0
        and top_left.y() >= 0
        and bottom_right.x() < owner.width()
        and bottom_right.y() < owner.height()
    )


def _team_scroll(column) -> QScrollArea:
    scrolls = column.findChildren(QScrollArea)
    assert len(scrolls) == 1
    return scrolls[0]


def test_main_window_accepts_small_desktop_targets_and_preserves_three_columns() -> None:
    app = _app()
    startup = MainWindow()
    assert (startup.width(), startup.height()) == (1280, 720)
    assert (startup.minimumWidth(), startup.minimumHeight()) == (1120, 650)
    startup.close()

    for width, height in ((1280, 720), (1366, 768), (1500, 980)):
        window = MainWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        assert window.minimumWidth() <= 1280
        assert window.minimumHeight() <= 720
        window.resize(width, height)
        window.show()
        app.processEvents()
        assert window.width() == width
        assert window.height() == height
        assert window.my_team_column.isVisible()
        assert window.center_column.isVisible()
        assert window.opponent_team_column.isVisible()
        assert window.center_column.width() > window.my_team_column.width()
        assert window.center_column.width() > window.opponent_team_column.width()
        left_ratio = window.center_column.width() / window.my_team_column.width()
        right_ratio = window.center_column.width() / window.opponent_team_column.width()
        assert 1.7 <= left_ratio <= 2.3
        assert 1.7 <= right_ratio <= 2.3
        window.close()
        app.processEvents()


def test_1280x720_team_columns_fit_horizontally_and_scroll_to_last_card() -> None:
    app = _app()
    window = MainWindow()
    for column_name, pokemon_id in (("team_my", "primarina"), ("team_enemy", "azumarill")):
        column = window.columns[column_name]
        for index, panel in enumerate(column.panels):
            panel.set_pokemon(_dual_type_view(f"{pokemon_id}-{index}"))

    window.resize(1280, 720)
    window.show()
    app.processEvents()

    for column in (window.my_team_column, window.opponent_team_column):
        scroll = _team_scroll(column)
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert scroll.horizontalScrollBar().maximum() == 0
        assert scroll.verticalScrollBar().maximum() > 0

        first = column.panels[0]
        for widget in (first.item_button, first.stats_button, first.active_indicator, *first.move_buttons):
            assert widget.isVisible()
            assert _inside(widget, first)

        last = column.panels[-1]
        scroll.ensureWidgetVisible(last)
        app.processEvents()
        assert scroll.verticalScrollBar().value() > 0
        top = last.mapTo(scroll.viewport(), last.rect().topLeft()).y()
        bottom = last.mapTo(scroll.viewport(), last.rect().bottomRight()).y()
        assert top < scroll.viewport().height()
        assert bottom >= 0

    window.close()


def test_1280x720_decide_record_and_details_controls_remain_reachable() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 720)
    window.show()
    app.processEvents()

    center = window.center_column
    guided = center.guided_turn_workspace

    for widget in (
        center.search_box,
        center.move_search_box,
        center.start_battle_button,
        center.set_turn_button,
        guided.header_label,
        guided.decide_phase_button,
        guided.record_phase_button,
        guided.situation_label,
        guided.considered_label,
        guided.analysis_label,
        guided.board_scroll,
        guided.readiness_label,
        guided.analysis_button,
        guided.details_tabs,
    ):
        assert widget.isVisible()
        assert _inside(widget, center)

    assert [guided.details_tabs.tabText(i) for i in range(guided.details_tabs.count())] == [
        "확률",
        "설명",
        "고급 입력",
    ]
    for index in range(guided.details_tabs.count()):
        guided.details_tabs.setCurrentIndex(index)
        app.processEvents()
        assert guided.details_tabs.currentIndex() == index

    guided.set_phase("record")
    app.processEvents()

    assert guided.record_body_scroll.isVisible()
    assert guided.record_body_scroll.widget() is guided.record_body_widget
    assert not guided.record_body_scroll.isAncestorOf(guided.next_turn_button)
    # Scrolling is a fallback capability, not a required overflow state at every
    # 1280x720 headless geometry.
    next_top_left = guided.next_turn_button.mapTo(guided.record_stage, guided.next_turn_button.rect().topLeft())
    next_bottom_right = guided.next_turn_button.mapTo(guided.record_stage, guided.next_turn_button.rect().bottomRight())
    assert next_top_left.y() >= 0
    assert next_bottom_right.y() < guided.record_stage.height()

    for widget in (
        guided.execution_check,
        guided.result_combo,
        guided.record_confirm_button,
        guided.record_clear_button,
        guided.current_hp_button,
        guided.switch_button,
        guided.condition_button,
    ):
        guided.record_body_scroll.ensureWidgetVisible(widget)
        app.processEvents()
        top = widget.mapTo(guided.record_body_scroll.viewport(), widget.rect().topLeft()).y()
        bottom = widget.mapTo(guided.record_body_scroll.viewport(), widget.rect().bottomRight()).y()
        assert top < guided.record_body_scroll.viewport().height()
        assert bottom >= 0

    emitted: list[str] = []
    guided.next_turn_requested.connect(lambda: emitted.append("next"))
    QTest.mouseClick(guided.next_turn_button, Qt.MouseButton.LeftButton)
    assert emitted == ["next"]

    window.close()


def test_record_body_scrolls_when_the_body_viewport_is_actually_constrained() -> None:
    app = _app()
    window = MainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.resize(1280, 720)
    window.show()
    guided = window.center_column.guided_turn_workspace
    guided.set_phase("record")
    guided.record_body_scroll.setFixedHeight(90)
    app.processEvents()

    scroll = guided.record_body_scroll.verticalScrollBar()
    assert scroll.maximum() > 0
    assert not guided.record_body_scroll.isAncestorOf(guided.next_turn_button)

    guided.record_body_scroll.ensureWidgetVisible(guided.condition_button)
    app.processEvents()
    assert scroll.value() > 0
    top = guided.condition_button.mapTo(
        guided.record_body_scroll.viewport(), guided.condition_button.rect().topLeft()
    ).y()
    bottom = guided.condition_button.mapTo(
        guided.record_body_scroll.viewport(), guided.condition_button.rect().bottomRight()
    ).y()
    assert top < guided.record_body_scroll.viewport().height()
    assert bottom >= 0
    window.close()


def test_record_next_turn_is_visible_at_1366x768_and_large_window() -> None:
    app = _app()
    for size in ((1366, 768), (1500, 980)):
        window = MainWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        window.resize(*size)
        window.show()
        guided = window.center_column.guided_turn_workspace
        guided.set_phase("record")
        app.processEvents()
        top = guided.next_turn_button.mapTo(guided.record_stage, guided.next_turn_button.rect().topLeft()).y()
        bottom = guided.next_turn_button.mapTo(guided.record_stage, guided.next_turn_button.rect().bottomRight()).y()
        assert top >= 0
        assert bottom < guided.record_stage.height()
        assert not guided.record_body_scroll.isAncestorOf(guided.next_turn_button)
        window.close()


def test_resize_only_has_no_battle_truth_or_evidence_side_effects() -> None:
    app = _app()
    window = MainWindow()
    window.my_team_column.panels[0].pokemon_view = SimpleNamespace(en="pikachu")
    window.opponent_team_column.panels[0].pokemon_view = SimpleNamespace(en="eevee")
    session_id = window.begin_new_battle()
    assert session_id == "ui-session-1"
    manager = window._observation_runtime_session_manager
    assert manager is not None
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    app.processEvents()

    before = {
        "selected_slots": deepcopy(window.selected_slots),
        "active_column": window._active_column_name,
        "trusted_turn": window._current_trusted_turn_number,
        "runtime": manager.capture_runtime_state_snapshot(session_id),
        "observations": manager.read_collection_snapshot(),
        "ledger": manager.read_applied_ledger(),
        "decision_owners": dict(window._c6_decision_capture_owners),
        "transition_owners": dict(window._c6_transition_capture_owners),
        "considered_action": deepcopy(window._guided_considered_action),
        "battle_sequence": window._battle_session_sequence,
    }

    for size in ((1280, 720), (1366, 768), (1500, 980), (1280, 720)):
        window.resize(*size)
        app.processEvents()

    after = {
        "selected_slots": deepcopy(window.selected_slots),
        "active_column": window._active_column_name,
        "trusted_turn": window._current_trusted_turn_number,
        "runtime": manager.capture_runtime_state_snapshot(session_id),
        "observations": manager.read_collection_snapshot(),
        "ledger": manager.read_applied_ledger(),
        "decision_owners": dict(window._c6_decision_capture_owners),
        "transition_owners": dict(window._c6_transition_capture_owners),
        "considered_action": deepcopy(window._guided_considered_action),
        "battle_sequence": window._battle_session_sequence,
    }
    assert after == before

    window.close()
