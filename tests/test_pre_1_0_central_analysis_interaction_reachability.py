from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea

from core.ko_mapping_loader import KoMappingLoader
from core.search_engine import SearchEngine, SearchResult
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel
from ui.widgets.move_search_box import MoveSearchBox
from ui.widgets.pokemon_search_box import PokemonSearchBox


class _Search:
    def __init__(self, rows: dict[tuple[str, str], list[SearchResult]]) -> None:
        self.rows = rows

    def search(self, query: str, *, kind: str | None = None, limit: int = 10):
        return list(self.rows.get((query, kind or ""), []))[:limit]


class _MoveRepo:
    def get(self, move_id: str):
        return SimpleNamespace(move_id=move_id, name_en=move_id)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _pokemon_results() -> list[SearchResult]:
    return [
        SearchResult("pokemon", "pikachu", "피카츄", 1.0, "prefix"),
        SearchResult("pokemon", "pidgeot", "피죤투", 1.0, "prefix"),
        SearchResult("pokemon", "sylveon", "님피아", 0.87, "substring"),
    ]


def _move_results() -> list[SearchResult]:
    return [
        SearchResult("move", "thunderbolt", "10만볼트", 1.0, "prefix"),
        SearchResult("move", "thunder-wave", "전기자석파", 0.86, "substring"),
        SearchResult("move", "thunder-punch", "번개펀치", 0.82, "substring"),
    ]


def test_real_cached_broad_pokemon_query_has_multiple_candidates() -> None:
    engine = SearchEngine(KoMappingLoader())
    cached = MainWindow._cached_pokemon_names()
    engine.add_pokemon_entries(cached)

    results = [row for row in engine.search("피", kind="pokemon", limit=16) if row.en in cached]

    assert len(results) >= 2


def test_real_main_window_broad_query_populates_multiple_popup_rows_without_layout_growth() -> None:
    app = _app()
    window = MainWindow()
    box = window.center_column.search_box
    before = box.sizeHint().height()

    box.input.setText("피")
    box.input.textEdited.emit("피")
    app.processEvents()

    assert box.completion_model.rowCount() >= 2
    assert {"pikachu", "pidgeot"}.issubset(set(box._current_en_ids))
    assert box.layout().count() == 1
    assert box.sizeHint().height() == before
    window.close()


def test_pokemon_popup_holds_multiple_results_without_entering_parent_layout() -> None:
    _app()
    box = PokemonSearchBox(_Search({("피", "pokemon"): _pokemon_results()}))
    before = box.sizeHint().height()

    box._update_results("피")

    assert box.completion_model.rowCount() == 3
    assert box.layout().count() == 1
    assert box.layout().itemAt(0).widget() is box.input
    assert box.sizeHint().height() == before
    assert box.completer.maxVisibleItems() == 8


def test_pokemon_keyboard_navigation_and_enter_preserve_selected_signal_contract() -> None:
    app = _app()
    box = PokemonSearchBox(_Search({("p", "pokemon"): _pokemon_results()}))
    selected: list[str] = []
    box.pokemon_selected.connect(selected.append)
    box.show()
    box.input.setFocus()
    QTest.keyClicks(box.input, "p")
    app.processEvents()
    initial_rows = [box.completion_model.data(box.completion_model.index(row, 0)) for row in range(box.completion_model.rowCount())]

    QTest.keyClick(box.input, Qt.Key.Key_Down)
    assert box.input.text() == "p"
    assert selected == []
    assert [box.completion_model.data(box.completion_model.index(row, 0)) for row in range(box.completion_model.rowCount())] == initial_rows
    QTest.keyClick(box.input, Qt.Key.Key_Up)
    assert box.input.text() == "p"
    assert selected == []
    QTest.keyClick(box.input, Qt.Key.Key_Down)
    assert box.input.text() == "p"
    assert selected == []
    QTest.keyClick(box.input, Qt.Key.Key_Return)
    app.processEvents()

    assert selected == ["pidgeot"]
    assert box.input.text() == ""
    assert box.completion_model.rowCount() == 0


def test_pokemon_popup_mouse_activation_preserves_selected_signal_contract() -> None:
    app = _app()
    box = PokemonSearchBox(_Search({("피", "pokemon"): _pokemon_results()}))
    selected: list[str] = []
    box.pokemon_selected.connect(selected.append)
    box.show()
    box.input.setText("피")
    box.input.textEdited.emit("피")
    app.processEvents()

    popup = box.completer.popup()
    index = popup.model().index(1, 0)
    popup.setCurrentIndex(index)
    rect = popup.visualRect(index)
    QTest.mouseClick(popup.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
    app.processEvents()

    assert selected == ["pidgeot"]
    assert box.input.text() == ""
    assert box.completion_model.rowCount() == 0
    assert not box.completer.popup().isVisible()


def test_move_popup_matches_pokemon_popup_and_preserves_candidate_filtering() -> None:
    app = _app()
    box = MoveSearchBox(_Search({("m", "move"): _move_results()}), _MoveRepo())
    box.set_available_move_ids({"thunderbolt", "thunder-wave"})
    selected: list[str] = []
    box.move_selected.connect(lambda move: selected.append(move.move_id))
    box.show()
    box.input.setFocus()
    before = box.sizeHint().height()
    QTest.keyClicks(box.input, "m")
    app.processEvents()

    assert box.completion_model.rowCount() == 2
    assert box.layout().count() == 1
    assert box.sizeHint().height() == before
    initial_rows = [box.completion_model.data(box.completion_model.index(row, 0)) for row in range(box.completion_model.rowCount())]

    QTest.keyClick(box.input, Qt.Key.Key_Down)
    assert box.input.text() == "m"
    assert selected == []
    assert [box.completion_model.data(box.completion_model.index(row, 0)) for row in range(box.completion_model.rowCount())] == initial_rows
    QTest.keyClick(box.input, Qt.Key.Key_Up)
    assert box.input.text() == "m"
    assert selected == []
    QTest.keyClick(box.input, Qt.Key.Key_Down)
    assert box.input.text() == "m"
    assert selected == []
    QTest.keyClick(box.input, Qt.Key.Key_Return)
    app.processEvents()

    assert selected == ["thunder-wave"]


def test_move_popup_mouse_activation_uses_same_selection_contract() -> None:
    app = _app()
    box = MoveSearchBox(_Search({("전", "move"): _move_results()}), _MoveRepo())
    box.set_available_move_ids({"thunderbolt", "thunder-wave", "thunder-punch"})
    selected: list[str] = []
    box.move_selected.connect(lambda move: selected.append(move.move_id))
    box.show()
    box.input.setText("전")
    box.input.textEdited.emit("전")
    app.processEvents()

    popup = box.completer.popup()
    index = popup.model().index(2, 0)
    popup.setCurrentIndex(index)
    rect = popup.visualRect(index)
    QTest.mouseClick(popup.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
    app.processEvents()

    assert selected == ["thunder-punch"]
    assert box.input.text() == ""
    assert box.completion_model.rowCount() == 0
    assert not box.completer.popup().isVisible()


def test_llm_advice_dense_auxiliary_controls_are_scroll_contained_and_reachable() -> None:
    app = _app()
    panel = LLMAdvicePanel()
    panel.resize(480, 700)
    panel.show()
    app.processEvents()

    assert isinstance(panel.auxiliary_scroll_area, QScrollArea)
    assert panel.auxiliary_scroll_area.widget() is panel.auxiliary_controls_widget
    assert len(panel._auxiliary_input_buttons) == 29
    assert all(button.parentWidget() is panel.auxiliary_controls_widget for button in panel._auxiliary_input_buttons)
    assert all(button.minimumHeight() >= 32 for button in panel._auxiliary_input_buttons)
    assert all(button.height() >= 32 for button in panel._auxiliary_input_buttons)

    assert panel.request_button.parentWidget() is panel
    assert panel.structured_request_button.parentWidget() is panel
    assert panel.deterministic_strategy_button.parentWidget() is panel
    assert panel.output_edit.parentWidget() is panel

    scroll = panel.auxiliary_scroll_area.verticalScrollBar()
    assert scroll.maximum() > 0
    panel.auxiliary_scroll_area.ensureWidgetVisible(panel.clear_battle_counter_button)
    app.processEvents()
    assert scroll.value() > 0


def test_llm_advice_representative_control_text_and_signal_behavior_survive_scroll_wrap() -> None:
    _app()
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.current_hp_requested.connect(lambda: emitted.append("hp"))

    assert panel.current_hp_button.text() == "Current HP"
    assert panel.current_hp_button in panel._auxiliary_input_buttons
    panel.current_hp_button.click()

    assert emitted == ["hp"]
    assert all(isinstance(button, QPushButton) and button.text() for button in panel._auxiliary_input_buttons)


def test_main_window_normal_and_large_desktop_sizes_keep_auxiliary_buttons_usable() -> None:
    app = _app()
    window = MainWindow()
    window.show()

    for width, height in ((1500, 980), (1920, 1080)):
        window.resize(width, height)
        app.processEvents()
        panel = window.center_column.llm_advice_panel
        assert panel.current_hp_button.height() >= 32
        assert panel.clear_battle_counter_button.height() >= 32
        assert panel.auxiliary_scroll_area.verticalScrollBar().maximum() > 0

    window.close()
