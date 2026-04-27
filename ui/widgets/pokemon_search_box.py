from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from core.search_engine import SearchEngine


class PokemonSearchBox(QWidget):
    pokemon_selected = Signal(str)

    def __init__(
        self,
        search_engine: SearchEngine,
        available_pokemon_ids: set[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.search_engine = search_engine
        self.available_pokemon_ids = available_pokemon_ids
        self._current_en_ids: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.input = QLineEdit()
        self.input.setPlaceholderText("포켓몬 검색")
        self.input.textChanged.connect(self._update_results)
        self.input.returnPressed.connect(self._confirm_current)
        self.input.installEventFilter(self)

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(140)
        self.results_list.hide()
        self.results_list.itemClicked.connect(self._confirm_item)

        layout.addWidget(self.input)
        layout.addWidget(self.results_list)
        self.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #CAD6E2;
                border-radius: 6px;
                padding: 6px 8px;
                background-color: #FFFFFF;
                color: #17202A;
            }
            QListWidget {
                border: 1px solid #CAD6E2;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #17202A;
                padding: 2px;
            }
            QListWidget::item {
                padding: 5px 6px;
            }
            QListWidget::item:selected {
                background-color: #4A90E2;
                color: #FFFFFF;
            }
            """
        )

    def eventFilter(self, watched: object, event: object) -> bool:
        if watched is self.input and isinstance(event, QKeyEvent):
            if event.type() == QKeyEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Down:
                    self._move_selection(1)
                    return True
                if event.key() == Qt.Key.Key_Up:
                    self._move_selection(-1)
                    return True
        return super().eventFilter(watched, event)

    def _update_results(self, text: str) -> None:
        self.results_list.clear()
        self._current_en_ids.clear()
        if not text.strip():
            self.results_list.hide()
            return

        results = [
            result
            for result in self.search_engine.search(text, kind="pokemon", limit=16)
            if self.available_pokemon_ids is None or result.en in self.available_pokemon_ids
        ][:8]
        if not results:
            self.results_list.hide()
            return

        for result in results:
            item = QListWidgetItem(f"{result.ko} ({result.en})")
            self.results_list.addItem(item)
            self._current_en_ids.append(result.en)
        self.results_list.setCurrentRow(0)
        self.results_list.show()

    def _move_selection(self, step: int) -> None:
        if not self._current_en_ids:
            return
        current_row = self.results_list.currentRow()
        next_row = max(0, min(len(self._current_en_ids) - 1, current_row + step))
        self.results_list.setCurrentRow(next_row)

    def _confirm_current(self) -> None:
        row = self.results_list.currentRow()
        if not 0 <= row < len(self._current_en_ids):
            return
        self._select_en_id(self._current_en_ids[row])

    def _confirm_item(self, item: QListWidgetItem) -> None:
        row = self.results_list.row(item)
        if 0 <= row < len(self._current_en_ids):
            self._select_en_id(self._current_en_ids[row])

    def _select_en_id(self, en_id: str) -> None:
        self.pokemon_selected.emit(en_id)
        self.input.clear()
        self.results_list.hide()
