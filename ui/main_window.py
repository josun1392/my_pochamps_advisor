from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from core.cache_manager import CacheManager
from core.ko_mapping_loader import KoMappingLoader
from core.pokemon_repository import PokemonRepository
from core.search_engine import SearchEngine
from ui.shortcuts import GlobalShortcuts
from ui.widgets.analysis_panel import AnalysisPanel
from ui.widgets.pokemon_panel import PokemonTeamColumn
from ui.widgets.pokemon_search_box import PokemonSearchBox


class AnalysisColumn(QFrame):
    def __init__(self, search_engine: SearchEngine, available_pokemon_ids: set[str]) -> None:
        super().__init__()
        self.setObjectName("columnFrame")
        self.is_active = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title_label = QLabel("AI 분석")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #17202A;")

        self.search_box = PokemonSearchBox(search_engine, available_pokemon_ids)
        self.analysis_panel = AnalysisPanel()
        layout.addWidget(title_label)
        layout.addWidget(self.search_box)
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

        self.cache = CacheManager()
        self.ko_loader = KoMappingLoader()
        self.search_engine = SearchEngine(self.ko_loader)
        self.repo = PokemonRepository(self.cache, self.ko_loader)

        self.selected_slots = {
            "team_my": 0,
            "team_enemy": None,
        }
        self._active_column_name = "team_my"

        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #EEF2F6;")
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.my_team_column = PokemonTeamColumn("내 팀", selectable=True)
        self.center_column = AnalysisColumn(self.search_engine, self._cached_pokemon_names())
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

        self._connect_slot_clicks()
        self.center_column.search_box.pokemon_selected.connect(self._on_pokemon_selected)
        self.shortcuts = GlobalShortcuts(self, self)
        self.set_active_column(self._active_column_name)

    def select_my_pokemon(self, slot_index: int) -> None:
        if not 0 <= slot_index < len(self.my_team_column.panels):
            return

        self.select_slot("team_my", slot_index)
        print(f"현재 선택된 내 포켓몬: {slot_index + 1}번")

    def select_current_move(self, move_index: int) -> None:
        current_panel = self.my_team_column.panels[self.selected_slots["team_my"] or 0]
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

    def select_slot(self, column_name: str, slot_index: int) -> None:
        team_column = self._team_column(column_name)
        if team_column is None or not 0 <= slot_index < len(team_column.panels):
            return

        self.selected_slots[column_name] = slot_index
        self.set_active_column(column_name)
        for index, panel in enumerate(team_column.panels):
            panel.set_selected(index == slot_index)

    def _on_pokemon_selected(self, en_id: str) -> None:
        slot = self._active_slot()
        if slot is None:
            print("활성화된 포켓몬 슬롯이 없습니다.")
            return

        try:
            view = self.repo.get(en_id)
        except RuntimeError as exc:
            print(f"포켓몬 바인딩 실패: {exc}")
            return

        slot.set_pokemon(view)
        print(f"포켓몬 바인딩 완료: {view.ko} ({view.en})")

    def _active_slot(self):
        team_column = self._team_column(self._active_column_name)
        selected_slot = self.selected_slots.get(self._active_column_name)
        if team_column is None or selected_slot is None:
            return None
        return team_column.panels[selected_slot]

    def _team_column(self, column_name: str) -> PokemonTeamColumn | None:
        if column_name == "team_my":
            return self.my_team_column
        if column_name == "team_enemy":
            return self.opponent_team_column
        return None

    def _connect_slot_clicks(self) -> None:
        for column_name, team_column in (
            ("team_my", self.my_team_column),
            ("team_enemy", self.opponent_team_column),
        ):
            for panel in team_column.panels:
                panel.slot_clicked.connect(
                    lambda slot_index, name=column_name: self.select_slot(name, slot_index)
                )

    def _cached_pokemon_names(self) -> set[str]:
        names: set[str] = set()
        pokemon_dir = self.cache.cache_root / "pokemon"
        for path in pokemon_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)
            except (OSError, json.JSONDecodeError):
                continue
            name = data.get("name") if isinstance(data, dict) else None
            if isinstance(name, str):
                names.add(name)
        return names
