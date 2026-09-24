from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QCompleter, QLineEdit, QVBoxLayout, QWidget

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
        self._completion_to_en_id: dict[str, str] = {}
        self._typed_query = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.input = QLineEdit()
        self.input.setPlaceholderText("포켓몬 검색")
        self.input.textEdited.connect(self._on_user_query_edited)
        self.input.returnPressed.connect(self._confirm_current)

        self.completion_model = QStringListModel(self)
        self.completer = QCompleter(self.completion_model, self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setMaxVisibleItems(8)
        self.completer.activated.connect(self._confirm_completion)
        self.completer.highlighted.connect(self._restore_typed_query)
        self.completer.setWidget(self.input)
        self.input.installEventFilter(self)

        layout.addWidget(self.input)
        self.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #CAD6E2;
                border-radius: 6px;
                padding: 6px 8px;
                background-color: #FFFFFF;
                color: #17202A;
            }
            QAbstractItemView {
                border: 1px solid #CAD6E2;
                background-color: #FFFFFF;
                color: #17202A;
                selection-background-color: #4A90E2;
                selection-color: #FFFFFF;
            }
            """
        )

    def _on_user_query_edited(self, text: str) -> None:
        self._typed_query = text
        self._update_results(text)

    def _restore_typed_query(self, _completion: object) -> None:
        if self.input.text() != self._typed_query:
            self.input.setText(self._typed_query)
            self.input.setCursorPosition(len(self._typed_query))

    def eventFilter(self, watched: object, event: object) -> bool:
        if watched is self.input and isinstance(event, QKeyEvent) and event.type() == QKeyEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down:
                self._move_popup_selection(1)
                return True
            if event.key() == Qt.Key.Key_Up:
                self._move_popup_selection(-1)
                return True
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter} and self._current_en_ids:
                self._confirm_current()
                return True
        return super().eventFilter(watched, event)

    def _move_popup_selection(self, step: int) -> None:
        if not self._current_en_ids:
            return
        popup = self.completer.popup()
        row = popup.currentIndex().row()
        if row < 0:
            row = 0 if step > 0 else len(self._current_en_ids) - 1
        else:
            row = max(0, min(len(self._current_en_ids) - 1, row + step))
        popup.setCurrentIndex(popup.model().index(row, 0))

    def _update_results(self, text: str) -> None:
        self._current_en_ids.clear()
        self._completion_to_en_id.clear()
        if not text.strip():
            self.completion_model.setStringList([])
            self.completer.popup().hide()
            return

        results = [
            result
            for result in self.search_engine.search(text, kind="pokemon", limit=16)
            if self.available_pokemon_ids is None or result.en in self.available_pokemon_ids
        ][:8]
        if not results:
            self.completion_model.setStringList([])
            self.completer.popup().hide()
            return

        labels: list[str] = []
        for result in results:
            label = f"{result.ko} ({result.en})"
            labels.append(label)
            self._current_en_ids.append(result.en)
            self._completion_to_en_id[label] = result.en
        self.completion_model.setStringList(labels)
        self.completer.setCompletionPrefix("")
        self.completer.complete()

    def _confirm_current(self) -> None:
        popup = self.completer.popup()
        index = popup.currentIndex()
        if index.isValid():
            self._confirm_completion(index.data())
            return
        if self._current_en_ids:
            self._select_en_id(self._current_en_ids[0])

    def _confirm_completion(self, completion: str) -> None:
        en_id = self._completion_to_en_id.get(str(completion))
        if en_id is not None:
            self._select_en_id(en_id)

    def _select_en_id(self, en_id: str) -> None:
        self.pokemon_selected.emit(en_id)
        self._typed_query = ""
        self.input.clear()
        self._current_en_ids.clear()
        self._completion_to_en_id.clear()
        self.completion_model.setStringList([])
        self.completer.popup().hide()
