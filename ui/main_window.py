from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from ui.shortcuts import GlobalShortcuts
from ui.widgets.analysis_panel import AnalysisPanel
from ui.widgets.pokemon_panel import PokemonTeamColumn


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pokemon Copilot v0.1 (Phase 1)")
        self.setMinimumSize(1280, 720)

        self.selected_my_slot = 0
        self.focused_column_index = 0

        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #EEF2F6;")
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.my_team_column = PokemonTeamColumn("내 팀", selectable=True)
        self.center_column = self._build_center_column()
        self.opponent_team_column = PokemonTeamColumn("상대 팀", selectable=False)
        self.columns = [self.my_team_column, self.center_column, self.opponent_team_column]
        for index, column in enumerate(self.columns):
            column.setObjectName(f"column{index}")

        layout.addWidget(self.my_team_column, 33)
        layout.addWidget(self.center_column, 34)
        layout.addWidget(self.opponent_team_column, 33)

        self.shortcuts = GlobalShortcuts(self, self)
        self._update_column_focus()

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
        self.focused_column_index = (self.focused_column_index + 1) % len(self.columns)
        self._update_column_focus()
        labels = ("내 팀", "AI 분석", "상대 팀")
        print(f"현재 포커스 열: {labels[self.focused_column_index]}")

    def _build_center_column(self) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title_label = QLabel("AI 분석")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #17202A;")

        layout.addWidget(title_label)
        layout.addWidget(AnalysisPanel(), 1)
        return column

    def _update_column_focus(self) -> None:
        for index, column in enumerate(self.columns):
            border = "2px solid #4A90E2" if index == self.focused_column_index else "1px solid #D8E0EA"
            column.setStyleSheet(
                f"""
                QWidget#column{index} {{
                    background-color: #FFFFFF;
                    border: {border};
                    border-radius: 8px;
                }}
                """
            )
