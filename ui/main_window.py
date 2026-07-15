from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy

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
from core.champions_item_repository import ChampionsItemRepository
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository, MoveView
from core.pokemon_stat_sample_repository import PokemonStatSampleRepository
from core.pokemon_repository import PokemonRepository
from core.search_engine import SearchEngine
from llm.advisor_damage_estimate import (
    attach_opponent_known_move_damage_estimates,
    attach_selected_move_damage_estimate,
)
from llm.advisor_battle_state_context import (
    normalize_user_confirmed_current_field_state,
    normalize_user_confirmed_final_battle_stat,
    normalize_user_confirmed_current_stat_stage,
    normalize_user_confirmed_current_ability,
    normalize_user_confirmed_current_condition,
    validate_explicit_user_item_event_confirmation,
)
from llm.opponent_assumptions import build_opponent_assumptions_payload
from llm.advisor_payload_contract import ADVISOR_KNOWN_LIMITATIONS, ADVISOR_PAYLOAD_MODE
from llm.advisor_client import run_ui_selected_advice
from ui.shortcuts import GlobalShortcuts
from ui.widgets.analysis_panel import AnalysisPanel
from ui.widgets.llm_advice_panel import LLMAdvicePanel
from ui.widgets.item_profile_dialog import (
    default_item_profile_for_role,
    item_button_text,
    ItemProfileDialog,
    legal_item_options_from_repository,
)
from ui.widgets.field_profile_dialog import FieldProfileDialog
from ui.widgets.item_event_dialog import ItemEventDialog
from ui.widgets.current_condition_dialog import CurrentConditionDialog
from ui.widgets.current_ability_dialog import CurrentAbilityDialog
from ui.widgets.current_stat_stage_dialog import CurrentStatStageDialog
from ui.widgets.current_field_state_dialog import CurrentFieldStateDialog
from ui.widgets.current_final_stat_dialog import CurrentFinalStatDialog
from ui.widgets.move_search_box import MoveSearchBox
from ui.widgets.pokemon_panel import PokemonTeamColumn
from ui.widgets.pokemon_search_box import PokemonSearchBox
from ui.widgets.stat_profile_dialog import (
    champions_final_stat_limits,
    validate_final_stats,
    StatProfileDialog,
)


OPPONENT_CANDIDATE_MOVES_LIMIT = 24
SPEED_CONTEXT_MODE = "choice_scarf_effective_speed_v0.30"
SPEED_CONTEXT_LIMITATIONS = [
    "Effective Speed includes only supported speed modifiers.",
    "Choice Scarf speed is modeled only when the item is user-confirmed.",
    "Choice lock is not modeled.",
    "This does not confirm final turn order.",
    "Priority moves are not modeled.",
    "Trick Room is not modeled.",
    "Tailwind is not modeled.",
    "Paralysis is not modeled.",
    "Speed stages are not modeled.",
    "Ability speed effects are not modeled.",
]
SPEED_CONTEXT_UNAVAILABLE_LIMITATIONS = [
    "Effective Speed comparison requires user-confirmed final Speed for both active Pokemon.",
    "Default Speed fallback is not used in v0.30.",
    "This does not confirm final turn order.",
]


def _item_event_identity(event: dict) -> tuple[object, object, object, object]:
    return (event["side"], event["item"], event["event_type"], event.get("turn"))


def _normalize_item_event_session(events: list[dict]) -> list[dict]:
    """Validate, de-duplicate, and order explicit item-event session state."""
    entries: list[tuple[int, dict]] = []
    positions: dict[tuple[object, object, object, object], int] = {}
    for event in events:
        normalized = validate_explicit_user_item_event_confirmation(event)
        key = _item_event_identity(normalized)
        existing_position = positions.get(key)
        if existing_position is None:
            positions[key] = len(entries)
            entries.append((len(entries), normalized))
        else:
            original_index, _ = entries[existing_position]
            entries[existing_position] = (original_index, normalized)

    def sort_key(entry: tuple[int, dict]) -> tuple[int, int, int]:
        original_index, event = entry
        turn = event.get("turn")
        return (1 if turn is None else 0, 0 if turn is None else int(turn), original_index)

    return [event for _, event in sorted(entries, key=sort_key)]


def _normalize_current_condition_session(conditions: object) -> dict[str, dict]:
    if not isinstance(conditions, dict):
        return {}
    normalized: dict[str, dict] = {}
    for side, condition in conditions.items():
        try:
            candidate = normalize_user_confirmed_current_condition(condition)
        except ValueError:
            continue
        if candidate["side"] == side:
            normalized[side] = candidate
    return normalized


def _normalize_current_ability_session(abilities: object) -> dict[str, dict]:
    if not isinstance(abilities, dict):
        return {}
    normalized: dict[str, dict] = {}
    for side, ability in abilities.items():
        try:
            candidate = normalize_user_confirmed_current_ability(ability)
        except ValueError:
            continue
        if candidate["side"] == side:
            normalized[side] = candidate
    return normalized


def _normalize_current_stat_stage_session(stages: object) -> dict[tuple[str, str], dict]:
    if not isinstance(stages, dict):
        return {}
    normalized: dict[tuple[str, str], dict] = {}
    for key, stage in stages.items():
        try:
            candidate = normalize_user_confirmed_current_stat_stage(stage)
        except ValueError:
            continue
        if key == (candidate["side"], candidate["stat"]):
            normalized[key] = candidate
    return normalized


class LLMAdviceWorker(QObject):
    finished = Signal(str, dict)
    failed = Signal(str)

    def __init__(
        self,
        battle_input: dict,
        *,
        enable_turn_pipeline: bool = False,
        enable_turn_order_context: bool = False,
        enable_opponent_move_context: bool = False,
        enable_battle_state_context: bool = False,
    ) -> None:
        super().__init__()
        self._battle_input = battle_input
        self._enable_turn_pipeline = enable_turn_pipeline
        self._enable_turn_order_context = enable_turn_order_context
        self._enable_opponent_move_context = enable_opponent_move_context
        self._enable_battle_state_context = enable_battle_state_context

    @Slot()
    def run(self) -> None:
        try:
            recommendation, usage, summary = run_ui_selected_advice(
                self._battle_input,
                enable_turn_pipeline=self._enable_turn_pipeline,
                enable_turn_order_context=self._enable_turn_order_context,
                enable_opponent_move_context=self._enable_opponent_move_context,
                enable_battle_state_context=self._enable_battle_state_context,
            )
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
        if "API_KEY_INVALID" in message or "API key not valid" in message:
            return "API key가 유효하지 않습니다. Google AI Studio에서 복사한 키를 다시 확인해주세요."
        if (
            "GEMINI_API_KEY" in message
            or "GOOGLE_API_KEY" in message
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
        self.champions_item_repo = ChampionsItemRepository()
        try:
            self.pokemon_stat_sample_repo = PokemonStatSampleRepository()
        except Exception:
            self.pokemon_stat_sample_repo = None
        for move_id, name_en in self.champions_move_pool_repo.iter_move_search_entries():
            self.search_engine.add_entry("move", move_id, name_en)

        self.selected_slots = {
            "team_my": 0,
            "team_enemy": 0,
        }
        self._active_column_name = "team_my"
        self._llm_thread: QThread | None = None
        self._llm_worker: LLMAdviceWorker | None = None
        self._field_profiles: dict | None = None
        self._item_event_confirmations: list[dict] = []
        self._current_condition_confirmations: dict[str, dict] = {}
        self._current_ability_confirmations: dict[str, dict] = {}
        self._current_stat_stage_confirmations: dict[tuple[str, str], dict] = {}
        self._current_field_state_confirmation: dict | None = None
        self._current_final_stat_confirmations: dict[tuple[str, str], dict] = {}

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
        self.center_column.llm_advice_panel.field_profile_requested.connect(self._open_field_profile_dialog)
        self.center_column.llm_advice_panel.item_event_requested.connect(self._open_item_event_dialog)
        self.center_column.llm_advice_panel.item_event_session_reset_requested.connect(
            self._clear_item_event_confirmations
        )
        self.center_column.llm_advice_panel.current_condition_requested.connect(
            self._open_current_condition_dialog
        )
        self.center_column.llm_advice_panel.current_condition_session_reset_requested.connect(
            self._clear_current_condition_confirmations
        )
        self.center_column.llm_advice_panel.current_ability_requested.connect(self._open_current_ability_dialog)
        self.center_column.llm_advice_panel.current_ability_session_reset_requested.connect(
            self._clear_current_ability_confirmations
        )
        self.center_column.llm_advice_panel.current_stat_stage_requested.connect(self._open_current_stat_stage_dialog)
        self.center_column.llm_advice_panel.current_stat_stage_session_reset_requested.connect(
            self._clear_current_stat_stage_confirmations
        )
        self.center_column.llm_advice_panel.current_field_state_requested.connect(
            self._open_current_field_state_dialog
        )
        self.center_column.llm_advice_panel.current_field_state_session_reset_requested.connect(
            self._clear_current_field_state_confirmation
        )
        self.center_column.llm_advice_panel.current_final_stat_requested.connect(self._open_current_final_stat_dialog)
        self.center_column.llm_advice_panel.current_final_stat_session_reset_requested.connect(self._clear_current_final_stat_confirmations)
        self._update_item_event_summary()
        self._update_current_condition_summary()
        self._update_current_ability_summary()
        self._update_current_stat_stage_summary()
        self._update_current_field_state_summary()
        self._update_current_final_stat_summary()
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
    def _open_field_profile_dialog(self) -> None:
        dialog = FieldProfileDialog(current_profiles=self._field_profiles, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._field_profiles = dialog.field_profiles

    @Slot()
    def _open_item_event_dialog(self) -> None:
        current_events = getattr(self, "_item_event_confirmations", [])
        dialog = ItemEventDialog(current_events=current_events, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        events = dialog.item_event_confirmations
        if events is None:
            return
        try:
            self._item_event_confirmations = _normalize_item_event_session(events)
            self._update_item_event_summary()
        except ValueError as exc:
            try:
                self.statusBar().showMessage(f"Failed | {exc}")
            except RuntimeError:
                pass

    @Slot()
    def _clear_item_event_confirmations(self) -> None:
        """Explicitly clear the session-local events at a new-battle boundary."""
        self._item_event_confirmations = []
        self._update_item_event_summary()

    @Slot()
    def _open_current_condition_dialog(self) -> None:
        current_conditions = getattr(self, "_current_condition_confirmations", {})
        dialog = CurrentConditionDialog(current_conditions=current_conditions, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        condition = dialog.current_condition_confirmation
        if condition is None:
            return
        try:
            normalized = normalize_user_confirmed_current_condition(condition)
        except ValueError as exc:
            try:
                self.statusBar().showMessage(f"Failed | {exc}")
            except (AttributeError, RuntimeError):
                pass
            return
        self._current_condition_confirmations = {
            **_normalize_current_condition_session(current_conditions),
            normalized["side"]: normalized,
        }
        self._update_current_condition_summary()

    @Slot()
    def _clear_current_condition_confirmations(self) -> None:
        self._current_condition_confirmations = {}
        self._update_current_condition_summary()

    @Slot()
    def _open_current_ability_dialog(self) -> None:
        current_abilities = getattr(self, "_current_ability_confirmations", {})
        dialog = CurrentAbilityDialog(current_abilities=current_abilities, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ability = dialog.current_ability_confirmation
        if ability is None:
            return
        try:
            normalized = normalize_user_confirmed_current_ability(ability)
        except ValueError as exc:
            try:
                self.statusBar().showMessage(f"Failed | {exc}")
            except (AttributeError, RuntimeError):
                pass
            return
        self._current_ability_confirmations = {
            **_normalize_current_ability_session(current_abilities),
            normalized["side"]: normalized,
        }
        self._update_current_ability_summary()

    @Slot()
    def _clear_current_ability_confirmations(self) -> None:
        self._current_ability_confirmations = {}
        self._update_current_ability_summary()

    @Slot()
    def _open_current_stat_stage_dialog(self) -> None:
        current_stages = getattr(self, "_current_stat_stage_confirmations", {})
        dialog = CurrentStatStageDialog(current_stages=current_stages, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        stage = dialog.current_stat_stage_confirmation
        if stage is None:
            return
        try:
            normalized = normalize_user_confirmed_current_stat_stage(stage)
        except ValueError:
            return
        self._current_stat_stage_confirmations = {
            **_normalize_current_stat_stage_session(current_stages),
            (normalized["side"], normalized["stat"]): normalized,
        }
        self._update_current_stat_stage_summary()

    @Slot()
    def _clear_current_stat_stage_confirmations(self) -> None:
        self._current_stat_stage_confirmations = {}
        self._update_current_stat_stage_summary()

    @Slot()
    def _open_current_field_state_dialog(self) -> None:
        current_field = getattr(self, "_current_field_state_confirmation", None)
        dialog = CurrentFieldStateDialog(current_field=current_field, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        snapshot = dialog.current_field_state_confirmation
        if snapshot is None:
            return
        try:
            self._current_field_state_confirmation = normalize_user_confirmed_current_field_state(snapshot)
        except ValueError:
            return
        self._update_current_field_state_summary()

    @Slot()
    def _clear_current_field_state_confirmation(self) -> None:
        self._current_field_state_confirmation = None
        self._update_current_field_state_summary()

    @Slot()
    def _open_current_final_stat_dialog(self) -> None:
        dialog = CurrentFinalStatDialog(current_stats=getattr(self, "_current_final_stat_confirmations", {}), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.current_final_stat_confirmation is None:
            return
        try:
            entry = normalize_user_confirmed_final_battle_stat(dialog.current_final_stat_confirmation)
        except ValueError:
            return
        self._current_final_stat_confirmations[(entry["side"], entry["stat"])] = entry
        self._update_current_final_stat_summary()

    @Slot()
    def _clear_current_final_stat_confirmations(self) -> None:
        self._current_final_stat_confirmations = {}
        self._update_current_final_stat_summary()

    def _update_item_event_summary(self) -> None:
        try:
            panel = self.center_column.llm_advice_panel
            panel.set_item_event_count(len(self._item_event_confirmations))
        except (AttributeError, RuntimeError):
            pass

    def _update_current_condition_summary(self) -> None:
        try:
            panel = self.center_column.llm_advice_panel
            panel.set_current_condition_count(len(self._current_condition_confirmations))
        except (AttributeError, RuntimeError):
            pass

    def _update_current_ability_summary(self) -> None:
        try:
            panel = self.center_column.llm_advice_panel
            panel.set_current_ability_count(len(self._current_ability_confirmations))
        except (AttributeError, RuntimeError):
            pass

    def _update_current_stat_stage_summary(self) -> None:
        try:
            self.center_column.llm_advice_panel.set_current_stat_stage_count(len(self._current_stat_stage_confirmations))
        except (AttributeError, RuntimeError):
            pass

    def _update_current_field_state_summary(self) -> None:
        try:
            snapshot = getattr(self, "_current_field_state_confirmation", None)
            count = 0
            if isinstance(snapshot, dict):
                count = 2 + len(snapshot.get("global_effects", [])) + len(snapshot.get("side_effects", []))
            self.center_column.llm_advice_panel.set_current_field_state_count(count)
        except (AttributeError, RuntimeError):
            pass

    def _update_current_final_stat_summary(self) -> None:
        try:
            self.center_column.llm_advice_panel.set_current_final_stat_count(len(self._current_final_stat_confirmations))
        except (AttributeError, RuntimeError):
            pass

    @Slot()
    def _start_llm_advice(self) -> None:
        if self._llm_thread is not None:
            return

        panel = self.center_column.llm_advice_panel
        enable_turn_pipeline = panel.turn_pipeline_enabled()
        enable_turn_order_context = enable_turn_pipeline
        enable_opponent_move_context = enable_turn_pipeline
        enable_battle_state_context = enable_turn_pipeline
        try:
            battle_input = self._build_llm_battle_input(
                include_item_event_confirmations=enable_battle_state_context,
                include_current_condition_confirmations=enable_battle_state_context,
                include_current_ability_confirmations=enable_battle_state_context,
                include_current_stat_stage_confirmations=enable_battle_state_context,
                include_current_field_state_confirmation=enable_battle_state_context,
                include_current_final_stat_confirmations=enable_battle_state_context,
            )
        except ValueError as exc:
            message = str(exc)
            panel.set_error(message)
            self.statusBar().showMessage(f"Failed | {message}")
            return

        panel.set_running(True)
        panel.set_turn_pipeline_status_enabled(enable_turn_pipeline)
        self.statusBar().showMessage("Analyzing...")

        self._llm_thread = QThread(self)
        self._llm_worker = LLMAdviceWorker(
            battle_input,
            enable_turn_pipeline=enable_turn_pipeline,
            enable_turn_order_context=enable_turn_order_context,
            enable_opponent_move_context=enable_opponent_move_context,
            enable_battle_state_context=enable_battle_state_context,
        )
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

    def _build_llm_battle_input(
        self,
        *,
        include_item_event_confirmations: bool = False,
        include_current_condition_confirmations: bool = False,
        include_current_ability_confirmations: bool = False,
        include_current_stat_stage_confirmations: bool = False,
        include_current_field_state_confirmation: bool = False,
        include_current_final_stat_confirmations: bool = False,
    ) -> dict:
        my_slot_index = self.selected_slots.get("team_my")
        opponent_slot_index = self.selected_slots.get("team_enemy")
        if my_slot_index is None:
            raise ValueError("\uB0B4 \uD3EC\uCF13\uBAAC\uC744 \uBA3C\uC800 \uC120\uD0DD\uD574\uC8FC\uC138\uC694.")
        if opponent_slot_index is None:
            raise ValueError("\uC0C1\uB300 \uD3EC\uCF13\uBAAC\uC744 \uBA3C\uC800 \uC120\uD0DD\uD574\uC8FC\uC138\uC694.")

        my_panel = self._slot_panel("team_my", my_slot_index)
        opponent_panel = self._slot_panel("team_enemy", opponent_slot_index)
        stat_profiles = {
            "my_active": _stat_profile_payload(my_panel),
            "opponent_active": _stat_profile_payload(opponent_panel),
        }
        item_profiles = {
            "my_active": _item_profile_payload(my_panel, role_key="my_active"),
            "opponent_active": _item_profile_payload(opponent_panel, role_key="opponent_active"),
        }
        pokemon_payloads = {
            "my_active": self._panel_to_llm_payload(my_panel, my_slot_index),
            "opponent_active": self._panel_to_llm_payload(opponent_panel, opponent_slot_index),
        }
        battle_input = {
            "scenario": {
                "mode": ADVISOR_PAYLOAD_MODE,
                "format_note": "Selected Pokemon identity plus default-assumption damage estimates for user-confirmed moves; no full battle state.",
                "known_limitations": list(ADVISOR_KNOWN_LIMITATIONS),
            },
            "pokemon": pokemon_payloads,
            "stat_profiles": stat_profiles,
            "item_profiles": item_profiles,
            "opponent_assumptions": build_opponent_assumptions_payload(
                pokemon_payloads.get("opponent_active"),
                getattr(self, "pokemon_stat_sample_repo", None),
            ),
            "speed_context": _speed_context_payload(stat_profiles, item_profiles),
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
        field_profiles = getattr(self, "_field_profiles", None)
        if field_profiles is not None:
            battle_input["field_profiles"] = deepcopy(field_profiles)
        if include_item_event_confirmations:
            confirmations = getattr(self, "_item_event_confirmations", [])
            normalized_confirmations = []
            if isinstance(confirmations, list):
                valid_confirmations = []
                for confirmation in confirmations:
                    try:
                        valid_confirmations.append(
                            validate_explicit_user_item_event_confirmation(confirmation)
                        )
                    except ValueError:
                        continue
                normalized_confirmations = _normalize_item_event_session(valid_confirmations)
            if normalized_confirmations:
                battle_input["item_event_confirmations"] = normalized_confirmations
        if include_current_condition_confirmations:
            conditions = _normalize_current_condition_session(
                getattr(self, "_current_condition_confirmations", {})
            )
            ordered_conditions = [conditions[side] for side in ("self", "opponent") if side in conditions]
            if ordered_conditions:
                battle_input["current_condition_confirmations"] = ordered_conditions
        if include_current_ability_confirmations:
            abilities = _normalize_current_ability_session(
                getattr(self, "_current_ability_confirmations", {})
            )
            ordered_abilities = [abilities[side] for side in ("self", "opponent") if side in abilities]
            if ordered_abilities:
                battle_input["current_ability_confirmations"] = ordered_abilities
        if include_current_stat_stage_confirmations:
            stages = _normalize_current_stat_stage_session(getattr(self, "_current_stat_stage_confirmations", {}))
            ordered_stages = [stages[key] for key in sorted(stages, key=lambda key: (("self", "opponent").index(key[0]), key[1]))]
            if ordered_stages:
                battle_input["current_stat_stage_confirmations"] = ordered_stages
        if include_current_field_state_confirmation:
            snapshot = getattr(self, "_current_field_state_confirmation", None)
            if isinstance(snapshot, dict):
                try:
                    battle_input["current_field_state_confirmation"] = (
                        normalize_user_confirmed_current_field_state(snapshot)
                    )
                except ValueError:
                    pass
        if include_current_final_stat_confirmations:
            entries = []
            for entry in getattr(self, "_current_final_stat_confirmations", {}).values():
                try:
                    entries.append(normalize_user_confirmed_final_battle_stat(entry))
                except ValueError:
                    continue
            if entries:
                battle_input["current_final_stat_confirmations"] = entries
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
                panel.item_profile_requested.connect(
                    lambda slot, name=column_name: self._on_item_profile_requested(name, slot)
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

    @Slot(str, int)
    def _on_item_profile_requested(self, column_name: str, slot_index: int) -> None:
        panel = self._slot_panel(column_name, slot_index)
        self.select_slot(column_name, slot_index)
        view = getattr(panel, "pokemon_view", None)
        if view is None:
            self.statusBar().showMessage("Failed | Select a Pokemon first.")
            return
        role_key = "opponent_active" if column_name == "team_enemy" else "my_active"
        dialog = ItemProfileDialog(
            pokemon_name=view.ko or view.en,
            current_profile=getattr(panel, "item_profile", None),
            role_key=role_key,
            item_options=self._legal_item_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        panel.set_item_profile(
            dialog.item_profile,
            item_button_text(dialog.item_profile, role_key=role_key),
        )
        profile = _item_profile_payload(panel, role_key=role_key)
        item_id = profile.get("item_id")
        if profile.get("status") == "user_confirmed" and isinstance(item_id, str):
            self.statusBar().showMessage(f"Item set | {view.ko or view.en}: {item_id}")
        elif profile.get("status") == "none":
            self.statusBar().showMessage(f"Item set | {view.ko or view.en}: no item")
        elif profile.get("status") == "unknown":
            self.statusBar().showMessage(f"Item set | {view.ko or view.en}: unknown")
        else:
            self.statusBar().showMessage(f"Item reset | {view.ko or view.en}")

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

    def _legal_item_options(self) -> list[dict]:
        return legal_item_options_from_repository(self.champions_item_repo)

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


def _item_profile_payload(panel, *, role_key: str) -> dict:
    profile = getattr(panel, "item_profile", None)
    if isinstance(profile, dict):
        return dict(profile)
    return default_item_profile_for_role(role_key)


def _speed_context_payload(stat_profiles: dict, item_profiles: dict | None = None) -> dict:
    my_speed = _confirmed_raw_speed(stat_profiles.get("my_active"))
    opponent_speed = _confirmed_raw_speed(stat_profiles.get("opponent_active"))
    if my_speed is None or opponent_speed is None:
        return {
            "mode": SPEED_CONTEXT_MODE,
            "available": False,
            "reason": "insufficient_confirmed_final_stats",
            "limitations": list(SPEED_CONTEXT_UNAVAILABLE_LIMITATIONS),
            "is_final_turn_order": False,
        }

    item_profiles = item_profiles if isinstance(item_profiles, dict) else {}
    my_modifiers = _speed_modifiers_for_item(item_profiles.get("my_active"))
    opponent_modifiers = _speed_modifiers_for_item(item_profiles.get("opponent_active"))
    my_effective_speed = _effective_speed(my_speed, my_modifiers)
    opponent_effective_speed = _effective_speed(opponent_speed, opponent_modifiers)
    raw_relation = _speed_relation(my_speed, opponent_speed)
    effective_relation = _speed_relation(my_effective_speed, opponent_effective_speed)

    return {
        "mode": SPEED_CONTEXT_MODE,
        "available": True,
        "my_active": {
            "raw_speed": my_speed,
            "effective_speed": my_effective_speed,
            "source": "user_confirmed_final_stats",
            "is_user_confirmed": True,
            "speed_modifiers": my_modifiers,
        },
        "opponent_active": {
            "raw_speed": opponent_speed,
            "effective_speed": opponent_effective_speed,
            "source": "user_confirmed_final_stats",
            "is_user_confirmed": True,
            "speed_modifiers": opponent_modifiers,
        },
        "comparison": {
            "raw_speed_relation": raw_relation,
            "raw_speed_margin": abs(my_speed - opponent_speed),
            "raw_speed_tie": my_speed == opponent_speed,
            "effective_speed_relation": effective_relation,
            "effective_speed_margin": abs(my_effective_speed - opponent_effective_speed),
            "effective_speed_tie": my_effective_speed == opponent_effective_speed,
            "speed_margin": abs(my_speed - opponent_speed),
            "speed_tie": my_speed == opponent_speed,
        },
        "limitations": list(SPEED_CONTEXT_LIMITATIONS),
        "is_final_turn_order": False,
    }


def _confirmed_raw_speed(profile: object) -> int | None:
    if not isinstance(profile, dict):
        return None
    if profile.get("status") != "user_confirmed_final_stats" or profile.get("source") != "user_input":
        return None
    final_stats = profile.get("final_stats")
    if not isinstance(final_stats, dict):
        return None
    speed = final_stats.get("spe")
    return speed if isinstance(speed, int) and speed > 0 else None


def _speed_modifiers_for_item(profile: object) -> list[dict]:
    if not isinstance(profile, dict):
        return []
    if profile.get("status") != "user_confirmed" or profile.get("item_id") != "choice-scarf":
        return []
    return [
        {
            "source": "item",
            "item_id": "choice-scarf",
            "name_en": str(profile.get("name_en") or "Choice Scarf"),
            "modifier": 1.5,
            "applied": True,
            "unsupported_effects": ["choice_lock"],
        }
    ]


def _effective_speed(raw_speed: int, speed_modifiers: list[dict]) -> int:
    value = raw_speed
    for modifier in speed_modifiers:
        if modifier.get("item_id") == "choice-scarf" and modifier.get("applied") is True:
            value = (value * 3) // 2
    return value


def _speed_relation(my_speed: int, opponent_speed: int) -> str:
    if my_speed > opponent_speed:
        return "my_active_faster"
    if my_speed < opponent_speed:
        return "opponent_active_faster"
    return "speed_tie"


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
