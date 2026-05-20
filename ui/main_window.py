from __future__ import annotations

import json
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository, MoveView
from core.pokemon_repository import PokemonRepository
from core.search_engine import SearchEngine
from llm.advisor_damage_estimate import (
    attach_opponent_known_move_damage_estimates,
    attach_selected_move_damage_estimate,
)
from llm.advisor_payload_contract import ADVISOR_KNOWN_LIMITATIONS, ADVISOR_PAYLOAD_MODE
from llm.advisor_client import run_ui_selected_advice
from ui.shortcuts import GlobalShortcuts
from ui.widgets.analysis_panel import AnalysisPanel
from ui.widgets.llm_advice_panel import LLMAdvicePanel
from ui.widgets.move_search_box import MoveSearchBox
from ui.widgets.pokemon_panel import PokemonTeamColumn
from ui.widgets.pokemon_search_box import PokemonSearchBox
from ui.widgets.stat_profile_dialog import (
    champions_final_stat_limits,
    validate_final_stats,
    StatProfileDialog,
)


OPPONENT_CANDIDATE_MOVES_LIMIT = 24


class LLMAdviceWorker(QObject):
    finished = Signal(str, dict)
    failed = Signal(str)

    def __init__(self, battle_input: dict) -> None:
        super().__init__()
        self._battle_input = battle_input

    @Slot()
    def run(self) -> None:
        try:
            recommendation, usage, summary = run_ui_selected_advice(self._battle_input)
        except requests.Timeout:
            self.failed.emit("\uC694\uCCAD \uC2DC\uAC04\uC774 \uCD08\uACFC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.")
            return
        except RuntimeError as exc:
            self.failed.emit(self._friendly_runtime_error(str(exc)))
            return
        except (KeyError, IndexError, TypeError, ValueError):
            self.failed.emit("LLM \uC751\uB2F5 \uD615\uC2DD\uC744 \uC77D\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.")
            return
        except Exception as exc:  # pragma: no cover - final UI safety net
            self.failed.emit(f"LLM \uCD94\uCC9C \uC0DD\uC131\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4: {exc}")
            return

        self.finished.emit(recommendation, {"usage": usage, "summary": summary})

    @staticmethod
    def _friendly_runtime_error(message: str) -> str:
        if (
            "GEMINI_API_KEY" in message
            or "GOOGLE_API_KEY" in message
            or "API_KEY_INVALID" in message
            or "API Key not found" in message
        ):
            return "API key\uAC00 \uC124\uC815\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4."
        if "Gemini API returned HTTP" in message:
            return message.replace("Gemini API returned HTTP", "Gemini API \uC624\uB958: status code", 1)
        return message


class AnalysisColumn(QFrame):
    def __init__(
        self,
        search_engine: SearchEngine,
        available_pokemon_ids: set[str],
        move_repository: MoveRepository,
    ) -> None:
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
        self.move_search_box = MoveSearchBox(search_engine, move_repository)
        self.analysis_panel = AnalysisPanel()
        self.llm_advice_panel = LLMAdvicePanel()
        layout.addWidget(title_label)
        layout.addWidget(self.search_box)
        layout.addWidget(self.move_search_box)
        layout.addWidget(self.analysis_panel, 1)
        layout.addWidget(self.llm_advice_panel, 1)

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
        self.setWindowTitle("Master Ball Advisor v0.14")
        self.setMinimumSize(1500, 980)
        self.resize(1500, 980)

        self.cache = CacheManager()
        self.ko_loader = KoMappingLoader()
        self.search_engine = SearchEngine(self.ko_loader)
        cached_pokemon_names = self._cached_pokemon_names()
        self.search_engine.add_pokemon_entries(cached_pokemon_names)
        self.repo = PokemonRepository(self.cache, self.ko_loader)
        self.move_repo = MoveRepository(self.cache, self.ko_loader)
        self.champions_move_pool_repo = ChampionsMovePoolRepository()
        for move_id, name_en in self.champions_move_pool_repo.iter_move_search_entries():
            self.search_engine.add_entry("move", move_id, name_en)

        self.selected_slots = {
            "team_my": 0,
            "team_enemy": 0,
        }
        self._active_column_name = "team_my"
        self._llm_thread: QThread | None = None
        self._llm_worker: LLMAdviceWorker | None = None

        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #EEF2F6;")
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.my_team_column = PokemonTeamColumn("내 팀", selectable=True)
        self.center_column = AnalysisColumn(
            self.search_engine,
            set(cached_pokemon_names),
            self.move_repo,
        )
        self.opponent_team_column = PokemonTeamColumn("상대 팀", selectable=True)
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

        layout.addWidget(self.my_team_column, 35)
        layout.addWidget(self.center_column, 30)
        layout.addWidget(self.opponent_team_column, 35)

        self._connect_slot_clicks()
        self.center_column.search_box.pokemon_selected.connect(self._on_pokemon_selected)
        self.center_column.move_search_box.move_selected.connect(self._on_move_selected)
        self.center_column.llm_advice_panel.advice_requested.connect(self._start_llm_advice)
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
        self._sync_move_search_candidates()

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
        self._refresh_move_selection_styles()
        print(f"[FOCUS] Active column: {target_column_name}")

    def select_slot(self, column_name: str, slot_index: int) -> None:
        team_column = self._team_column(column_name)
        if team_column is None or not 0 <= slot_index < len(team_column.panels):
            return

        self.selected_slots[column_name] = slot_index
        self.set_active_column(column_name)
        for index, panel in enumerate(team_column.panels):
            panel.set_selected(index == slot_index)
        self._refresh_move_selection_styles()
        self._sync_move_search_candidates()

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
        self._sync_move_search_candidates()
        print(f"포켓몬 바인딩 완료: {view.ko} ({view.en})")


    @Slot(object)
    def _on_move_selected(self, move: MoveView) -> None:
        slot = self._active_slot()
        if slot is None or slot.selected_move_index is None:
            self.statusBar().showMessage("Failed | Select a move slot first.")
            return
        slot.set_move(slot.selected_move_index, move)
        self.statusBar().showMessage(f"Move set | {move.name_ko or move.name_en}")

    @Slot()
    def _start_llm_advice(self) -> None:
        if self._llm_thread is not None:
            return

        panel = self.center_column.llm_advice_panel
        try:
            battle_input = self._build_llm_battle_input()
        except ValueError as exc:
            message = str(exc)
            panel.set_error(message)
            self.statusBar().showMessage(f"Failed | {message}")
            return

        panel.set_running(True)
        self.statusBar().showMessage("Analyzing...")

        self._llm_thread = QThread(self)
        self._llm_worker = LLMAdviceWorker(battle_input)
        self._llm_worker.moveToThread(self._llm_thread)

        self._llm_thread.started.connect(self._llm_worker.run)
        self._llm_worker.finished.connect(self._on_llm_advice_finished)
        self._llm_worker.failed.connect(self._on_llm_advice_failed)
        self._llm_worker.finished.connect(self._llm_thread.quit)
        self._llm_worker.failed.connect(self._llm_thread.quit)
        self._llm_thread.finished.connect(self._llm_worker.deleteLater)
        self._llm_thread.finished.connect(self._cleanup_llm_worker)
        self._llm_thread.start()

    @Slot(str, dict)
    def _on_llm_advice_finished(self, recommendation: str, payload: dict) -> None:
        panel = self.center_column.llm_advice_panel
        panel.set_running(False)
        panel.set_advice_text(recommendation)

        usage = payload.get("usage", {})
        summary = payload.get("summary", {})
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        cost = float(summary.get("estimated_cost_usd", 0.0))
        cost_text = self._format_cost_text(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            pricing_status=str(summary.get("pricing_status", "")),
        )
        if summary.get("token_logging_error"):
            status_text = f"Done | {cost_text} | cost logging failed"
        else:
            status_text = f"Done | {cost_text}"
        panel.set_cost_text(f"\uBE44\uC6A9: {cost_text}")
        self.statusBar().showMessage(status_text)

    @staticmethod
    def _format_cost_text(
        *,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        pricing_status: str,
    ) -> str:
        usage_text = f"input {input_tokens} / output {output_tokens}"
        if pricing_status == "free_tier_zero_cost":
            return f"Free tier | {usage_text} | ${cost:.7f}"
        if pricing_status == "paid_tier_estimated_cost":
            return f"Paid estimate | {usage_text} | ${cost:.7f}"
        if pricing_status == "unknown_model_or_unknown_pricing":
            return f"Pricing unknown | {usage_text}"
        return f"{usage_text} | ${cost:.7f}"

    @Slot(str)
    def _on_llm_advice_failed(self, message: str) -> None:
        panel = self.center_column.llm_advice_panel
        panel.set_running(False)
        panel.set_error(message)
        self.statusBar().showMessage(f"Failed | {message}")

    @Slot()
    def _cleanup_llm_worker(self) -> None:
        if self._llm_thread is not None:
            self._llm_thread.deleteLater()
        self._llm_thread = None
        self._llm_worker = None

    def _build_llm_battle_input(self) -> dict:
        my_slot_index = self.selected_slots.get("team_my")
        opponent_slot_index = self.selected_slots.get("team_enemy")
        if my_slot_index is None:
            raise ValueError("\uB0B4 \uD3EC\uCF13\uBAAC\uC744 \uBA3C\uC800 \uC120\uD0DD\uD574\uC8FC\uC138\uC694.")
        if opponent_slot_index is None:
            raise ValueError("\uC0C1\uB300 \uD3EC\uCF13\uBAAC\uC744 \uBA3C\uC800 \uC120\uD0DD\uD574\uC8FC\uC138\uC694.")

        my_panel = self._slot_panel("team_my", my_slot_index)
        opponent_panel = self._slot_panel("team_enemy", opponent_slot_index)
        battle_input = {
            "scenario": {
                "mode": ADVISOR_PAYLOAD_MODE,
                "format_note": "Selected Pokemon identity plus default-assumption damage estimates for user-confirmed moves; no full battle state.",
                "known_limitations": list(ADVISOR_KNOWN_LIMITATIONS),
            },
            "pokemon": {
                "my_active": self._panel_to_llm_payload(my_panel, my_slot_index),
                "opponent_active": self._panel_to_llm_payload(opponent_panel, opponent_slot_index),
            },
            "stat_profiles": {
                "my_active": _stat_profile_payload(my_panel),
                "opponent_active": _stat_profile_payload(opponent_panel),
            },
            "moves": {
                "my_selected_move_index": my_panel.selected_move_index,
                "my_available_moves": self._panel_moves_payload(my_panel),
                "my_selected_move": self._selected_move_payload(my_panel),
                "opponent_available_moves": [],
                "opponent_selected_move": None,
                "opponent_selected_move_index": opponent_panel.selected_move_index,
                "move_data_status": "four_move_damage_comparison_v0.10",
                "notes": [
                    "Only user-confirmed move slots are included.",
                    "Empty move slots are omitted.",
                    "Cache learnsets are used only as search candidates.",
                    "User-confirmed move damage estimates use default assumptions only.",
                    "Opponent known move damage estimates use default assumptions only.",
                ],
            },
            "opponent_moves": self._opponent_moves_payload(opponent_panel),
        }
        return attach_opponent_known_move_damage_estimates(
            attach_selected_move_damage_estimate(battle_input)
        )

    @staticmethod
    def _panel_moves_payload(panel) -> list[dict]:
        moves = []
        for index, move in enumerate(panel.selected_moves):
            if move is not None:
                moves.append(_move_payload(move, index))
        return moves

    @staticmethod
    def _selected_move_payload(panel) -> dict | None:
        index = panel.selected_move_index
        if index is None or not 0 <= index < len(panel.selected_moves):
            return None
        move = panel.selected_moves[index]
        if move is None:
            return None
        return _move_payload(move, index)

    def _opponent_moves_payload(self, opponent_panel) -> dict:
        known_moves = [
            {**move_payload, "source": "user_confirmed"}
            for move_payload in self._panel_moves_payload(opponent_panel)
        ]
        known_move_ids = {
            move["move_id"]
            for move in known_moves
            if isinstance(move.get("move_id"), str) and move.get("move_id")
        }

        view = getattr(opponent_panel, "pokemon_view", None)
        if view is None:
            candidate_status = {
                "status": "unknown",
                "reason": "No opponent Pokemon is selected.",
            }
            candidate_moves: list[dict] = []
        else:
            candidate_status = self.champions_move_pool_repo.status_for_pokemon(view.en)
            candidate_moves = self._opponent_candidate_moves(view.en, known_move_ids)

        return {
            "status": _opponent_moves_status(
                known_moves=known_moves,
                candidate_moves=candidate_moves,
                candidate_source_status=str(candidate_status.get("status", "unknown")),
            ),
            "known_moves": known_moves,
            "candidate_moves": candidate_moves,
            "candidate_moves_limit": OPPONENT_CANDIDATE_MOVES_LIMIT,
            "candidate_source_status": candidate_status,
            "unknown_moves": {
                "has_user_confirmed_moves": bool(known_moves),
                "candidate_source_status": candidate_status.get("status", "unknown"),
                "reason": (
                    "No opponent moves have been user-confirmed."
                    if not known_moves
                    else "Opponent moves are partially user-confirmed."
                ),
            },
            "limitations": [
                "Known opponent moves are user-confirmed only.",
                "Candidate moves are possible moves, not confirmed opponent moves.",
                "Do not assume the opponent has a candidate move unless user-confirmed.",
                "Opponent known move damage estimates use default assumptions only.",
                "Candidate move damage is not calculated in v0.14.",
            ],
        }

    def _opponent_candidate_moves(self, pokemon_id: str, known_move_ids: set[str]) -> list[dict]:
        move_ids = sorted(self.champions_move_pool_repo.get_allowed_move_ids_for_pokemon(pokemon_id))
        candidates: list[dict] = []
        for move_id in move_ids:
            if move_id in known_move_ids:
                continue
            try:
                move = self.move_repo.get(move_id)
            except RuntimeError:
                continue
            payload = _move_payload(move, slot_index=-1)
            payload.pop("slot", None)
            payload["source"] = "champions_movepool"
            payload["confidence"] = "possible_not_confirmed"
            candidates.append(payload)
            if len(candidates) >= OPPONENT_CANDIDATE_MOVES_LIMIT:
                break
        return candidates

    def _slot_panel(self, column_name: str, slot_index: int):
        team_column = self._team_column(column_name)
        if team_column is None or not 0 <= slot_index < len(team_column.panels):
            raise ValueError("\uC120\uD0DD\uB41C \uD3EC\uCF13\uBAAC \uC815\uBCF4\uB97C \uC77D\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.")
        return team_column.panels[slot_index]

    @staticmethod
    def _panel_to_llm_payload(panel, slot_index: int) -> dict:
        view = getattr(panel, "pokemon_view", None)
        if view is None:
            raise ValueError("\uC120\uD0DD\uB41C \uD3EC\uCF13\uBAAC \uC815\uBCF4\uB97C \uC77D\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.")
        if not view.types_en or not view.base_stats:
            raise ValueError("\uD3EC\uCF13\uBAAC \uAE30\uBCF8 \uC815\uBCF4\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4.")
        return {
            "slot_index": slot_index,
            "name_en": view.en,
            "name_ko": view.ko,
            "types": list(view.types_en),
            "types_ko": list(view.types_ko),
            "base_stats": dict(view.base_stats),
            "abilities": list(view.abilities_en),
            "abilities_ko": list(view.abilities_ko),
            "hp_percent": panel.current_hp_percent,
            "selected_move_index": panel.selected_move_index,
        }

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
            for slot_index, panel in enumerate(team_column.panels):
                panel.slot_clicked.connect(
                    lambda slot_index, name=column_name: self.select_slot(name, slot_index)
                )
                panel.move_slot_selected.connect(
                    lambda move_index, name=column_name, slot=slot_index: self._on_move_slot_selected(
                        name,
                        slot,
                        move_index,
                    )
                )
                panel.stat_profile_requested.connect(
                    lambda slot, name=column_name: self._on_stat_profile_requested(name, slot)
                )

    @Slot(str, int, int)
    def _on_move_slot_selected(self, column_name: str, slot_index: int, move_index: int) -> None:
        del move_index
        self.select_slot(column_name, slot_index)
        self._sync_move_search_candidates()

    @Slot(str, int)
    def _on_stat_profile_requested(self, column_name: str, slot_index: int) -> None:
        panel = self._slot_panel(column_name, slot_index)
        self.select_slot(column_name, slot_index)
        view = getattr(panel, "pokemon_view", None)
        if view is None:
            self.statusBar().showMessage("Failed | Select a Pokemon first.")
            return
        dialog = StatProfileDialog(
            pokemon_name=view.ko or view.en,
            current_stats=getattr(panel, "final_stats", None),
            base_stats=view.base_stats,
            stat_limits=champions_final_stat_limits(view.base_stats),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        panel.set_final_stats(dialog.final_stats)
        if dialog.final_stats is None:
            self.statusBar().showMessage(f"Stats cleared | {view.ko or view.en}")
        else:
            self.statusBar().showMessage(f"Stats set | {view.ko or view.en}")

    def _refresh_move_selection_styles(self) -> None:
        for column_name, team_column in (
            ("team_my", self.my_team_column),
            ("team_enemy", self.opponent_team_column),
        ):
            visible_slot_index = (
                self.selected_slots.get(column_name)
                if column_name == self._active_column_name
                else None
            )
            for slot_index, panel in enumerate(team_column.panels):
                panel.refresh_move_selection_style(show_selected=slot_index == visible_slot_index)

    def _sync_move_search_candidates(self) -> None:
        slot = self._active_slot()
        view = getattr(slot, "pokemon_view", None) if slot is not None else None
        if view is None:
            self.center_column.move_search_box.set_available_move_ids(
                set(),
                empty_message="Select a Pokemon first",
            )
            return
        available_move_ids, empty_message = _move_search_candidates_for_view(
            view,
            self.champions_move_pool_repo,
        )
        self.center_column.move_search_box.set_available_move_ids(
            available_move_ids,
            empty_message=empty_message,
        )
        if empty_message is not None:
            self.statusBar().showMessage(f"Move search unavailable | {view.ko}: Champions sample fixture missing")

    @staticmethod
    def _cached_pokemon_names() -> dict[str, str | None]:
        names: dict[str, str | None] = {}
        pokemon_dir = Path("data/cache/pokemon")
        for path in pokemon_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            entity_id = data.get("entity_id")
            name_data = data.get("name")
            if isinstance(name_data, dict):
                name = entity_id
                name_ko = name_data.get("ko")
            else:
                name = entity_id
                name_ko = None
            if isinstance(name, str):
                names[name] = name_ko if isinstance(name_ko, str) else None
        return names


def _move_payload(move: MoveView, slot_index: int) -> dict:
    return {
        "slot": slot_index,
        "move_id": move.move_id,
        "name_en": move.name_en,
        "name_ko": move.name_ko,
        "type": move.type,
        "category": move.category,
        "power": move.power,
        "accuracy": move.accuracy,
        "pp": move.pp,
    }


def _stat_profile_payload(panel) -> dict:
    final_stats = validate_final_stats(getattr(panel, "final_stats", None))
    if final_stats is None:
        return {
            "status": "default_assumption",
            "source": "system_default",
            "level": 50,
            "final_stats": None,
            "evs": None,
            "ivs": "31 all",
            "nature": "neutral",
            "item": None,
            "notes": [
                "No user-confirmed final stats are available.",
                "Damage estimates use the default stat profile.",
            ],
        }
    return {
        "status": "user_confirmed_final_stats",
        "source": "user_input",
        "level": 50,
        "final_stats": final_stats,
        "evs": None,
        "ivs": None,
        "nature": None,
        "item": None,
        "notes": [
            "Final stats are user-provided.",
            "EV/IV/nature breakdown is not connected.",
        ],
    }


def _opponent_moves_status(
    *,
    known_moves: list[dict],
    candidate_moves: list[dict],
    candidate_source_status: str,
) -> str:
    has_known = bool(known_moves)
    has_candidates = bool(candidate_moves)
    if has_known and has_candidates:
        return "known_and_candidates"
    if has_known:
        return "known_only"
    if has_candidates:
        return "candidates_only"
    if candidate_source_status == "unavailable_missing_champions_movepool":
        return "unavailable_missing_champions_movepool"
    return "unknown"


def _move_search_candidates_for_view(
    view,
    champions_move_pool_repo: ChampionsMovePoolRepository,
) -> tuple[set[str], str | None]:
    move_ids = champions_move_pool_repo.get_allowed_move_ids_for_pokemon(view.en)
    if move_ids:
        return move_ids, None
    return set(), "Champions moves unavailable"
