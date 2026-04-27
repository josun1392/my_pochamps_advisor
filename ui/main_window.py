from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from ui.shortcuts import GlobalShortcuts
from ui.widgets.analysis_panel import AnalysisPanel
from ui.widgets.pokemon_panel import PokemonTeamColumn


class AnalysisColumn(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("columnFrame")
        self.is_active = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title_label = QLabel("AI 분석")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #17202A;")

        self.analysis_panel = AnalysisPanel()
        layout.addWidget(title_label)
        layout.addWidget(self.analysis_panel, 1)

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self.setProperty("active", active)
        self.setStyleSheet(self._build_stylesheet(active))
        self.analysis_panel.set_active(active)

    @staticmethod
    def _build_stylesheet(active: bool) -> str:
        border = "2px solid #4A90E2" if active else "1px solid #CCCCCC"
        return f"""
            QFrame#columnFrame {{
                background-color: #FFFFFF;
                border: {border};
                border-radius: 8px;
            }}
        """


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pokemon Copilot v0.1 (Phase 1)")
        self.setMinimumSize(1280, 720)

        self.selected_my_slot = 0
        self._active_column_name = "team_my"

        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #EEF2F6;")
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.my_team_column = PokemonTeamColumn("내 팀", selectable=True)
        self.center_column = AnalysisColumn()
        self.opponent_team_column = PokemonTeamColumn("상대 팀", selectable=False)
        self.columns = {
            "team_my": self.my_team_column,
            "analysis": self.center_column,
            "team_enemy": self.opponent_team_column,
        }
        self._column_names = list(self.columns.keys())
        self._column_labels = {
            "team_my": "내 팀",
            "analysis": "AI 분석",
            "team_enemy": "상대 팀",
        }

        layout.addWidget(self.my_team_column, 33)
        layout.addWidget(self.center_column, 34)
        layout.addWidget(self.opponent_team_column, 33)

        self.shortcuts = GlobalShortcuts(self, self)
        self.set_active_column(self._active_column_name)

    def select_my_pokemon(self, slot_index: int) -> None:
        if not 0 <= slot_index < len(self.my_team_column.panels):
            return

        self.selected_my_slot = slot_index
        for index, panel in enumerate(self.my_team_column.panels):
            panel.set_selected(index == slot_index)
        print(f"현재 선택된 내 포켓몬: {slot_index + 1}번")

    def select_current_move(self, move_index: int) -> None:
        current_panel = self.my_team_column.panels[self.selected_my_slot]
        current_panel.select_move(move_index)

    def focus_next_column(self) -> None:
        current_index = self._column_names.index(self._active_column_name)
        next_index = (current_index + 1) % len(self._column_names)
        self.set_active_column(self._column_names[next_index])

    def set_active_column(self, target_column_name: str) -> None:
        if target_column_name not in self._column_names:
            return

        for column_name, column in self.columns.items():
            is_active = column_name == target_column_name
            column.set_active(is_active)
            column.style().unpolish(column)
            column.style().polish(column)

        self._active_column_name = target_column_name
        print(f"[FOCUS] Active column: {target_column_name}")
