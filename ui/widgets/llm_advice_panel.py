from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QPushButton, QTextEdit, QVBoxLayout
from ui.strategy_explanation_presentation import present_strategy_explanation, render_strategy_explanation


TURN_PIPELINE_HELP_TEXT = (
    "후보 이벤트, 선후공 보조 정보, UI에 보이는 상대 기술 후보, 현재 포켓몬/HP 스냅샷, "
    "사용자 확인 아이템, 사용자 확인 필드 상태를 LLM 입력에 포함합니다.\n"
    "필드 상태는 날씨/필드/룸/벽/설치물의 사용자 확인 현재 컨텍스트입니다. "
    "이 정보는 확정 결과가 아니며, 상대의 실제 선택 기술이나 숨겨진 아이템/상태/랭크/필드를 추론하지 않습니다. "
    "필드 상태는 턴 수, 만료, 턴 후 결과, 정확한 데미지, 전체 턴 결과를 확정하지 않습니다. "
    "턴 후 HP, 아이템 소모, RNG, 스피드 타이, Quick Claw 발동, 전체 턴 결과를 확정하지 않습니다."
)
TURN_PIPELINE_STATUS_TEXT = (
    "제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보, 현재 포켓몬/HP 스냅샷, "
    "사용자 확인 아이템, 사용자 확인 필드 상태 전달 | 필드 상태는 현재 컨텍스트만 | 확정 결과 아님"
)


class LLMAdvicePanel(QFrame):
    advice_requested = Signal()
    structured_advice_requested = Signal()
    recommendation_readiness_requested = Signal()
    readiness_input_requested = Signal(str)
    field_profile_requested = Signal()
    item_event_requested = Signal()
    item_event_session_reset_requested = Signal()
    current_condition_requested = Signal()
    current_condition_session_reset_requested = Signal()
    current_ability_requested = Signal()
    switch_permission_requested = Signal()
    current_ability_session_reset_requested = Signal()
    current_type_requested = Signal()
    current_type_session_reset_requested = Signal()
    current_stat_stage_requested = Signal()
    current_stat_stage_session_reset_requested = Signal()
    current_field_state_requested = Signal()
    current_field_state_session_reset_requested = Signal()
    current_final_stat_requested = Signal()
    current_final_stat_session_reset_requested = Signal()
    current_hp_requested = Signal()
    current_hp_session_reset_requested = Signal()
    current_battle_format_requested = Signal()
    current_battle_format_session_reset_requested = Signal()
    current_observed_damage_requested = Signal()
    current_observed_damage_reset_requested = Signal()
    battle_counter_requested = Signal()
    battle_counter_reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("llmAdvicePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.request_button = QPushButton("이번 턴 추천 받기")
        self.request_button.clicked.connect(self.advice_requested.emit)
        self.request_button.setText("기존 선택 기술 조언")
        self.request_button.setToolTip("현재 선택한 기술을 중심으로 자유 형식 조언을 받습니다.")
        self.request_button.setAccessibleName("기존 선택 기술 조언")
        self.structured_request_button = QPushButton("구조화 추천 받기")
        self.structured_request_button.clicked.connect(self.structured_advice_requested.emit)
        self.structured_request_button.setToolTip("후보 기술 전체를 비교하고 검증된 구조화 추천을 받습니다.")
        self.structured_request_button.setAccessibleName("구조화 추천 받기")
        self.readiness_button = QPushButton("Check recommendation readiness")
        self.readiness_button.setObjectName("recommendationReadinessButton")
        self.readiness_button.setToolTip("Show only material trusted authority missing from the current deterministic recommendation.")
        self.readiness_button.clicked.connect(self.recommendation_readiness_requested.emit)
        self.readiness_label = QLabel("Recommendation readiness has not been checked.")
        self.readiness_label.setObjectName("recommendationReadinessLabel")
        self.readiness_label.setWordWrap(True)
        self.readiness_input_button = QPushButton("Open needed input")
        self.readiness_input_button.setObjectName("recommendationReadinessInputButton")
        self.readiness_input_button.setVisible(False)
        self.readiness_input_button.clicked.connect(self._request_readiness_input)
        self._readiness_action: str | None = None
        self._readiness_extra_input_buttons: list[QPushButton] = []
        self.readiness_input_layout = QVBoxLayout()
        self.readiness_input_layout.setContentsMargins(0, 0, 0, 0)
        self.readiness_input_layout.setSpacing(4)
        self.readiness_input_layout.addWidget(self.readiness_input_button)

        self.field_profile_button = QPushButton("Field state")
        self.field_profile_button.setObjectName("fieldProfileButton")
        self.field_profile_button.setToolTip(
            "Open user-confirmed current field state input. This does not set duration, expiration, "
            "post-turn state, damage precision, or full turn outcome."
        )
        self.field_profile_button.clicked.connect(self.field_profile_requested.emit)

        self.item_event_button = QPushButton("Item event")
        self.item_event_button.setObjectName("itemEventButton")
        self.item_event_button.setToolTip(
            "Open user-confirmed observed item event input. This does not calculate resolved effects, "
            "exact HP, damage, RNG, or turn order."
        )
        self.item_event_button.clicked.connect(self.item_event_requested.emit)

        self.clear_item_events_button = QPushButton("Clear item events")
        self.clear_item_events_button.setObjectName("clearItemEventsButton")
        self.clear_item_events_button.setToolTip("Clear user-confirmed item events for this battle session.")
        self.clear_item_events_button.clicked.connect(self.item_event_session_reset_requested.emit)

        self.current_condition_button = QPushButton("Condition")
        self.current_condition_button.setObjectName("currentConditionButton")
        self.current_condition_button.setToolTip(
            "Open user-confirmed current major condition input. This does not resolve events, damage, duration, RNG, or order."
        )
        self.current_condition_button.clicked.connect(self.current_condition_requested.emit)

        self.clear_current_conditions_button = QPushButton("Clear current conditions")
        self.clear_current_conditions_button.setObjectName("clearCurrentConditionsButton")
        self.clear_current_conditions_button.setToolTip("Clear user-confirmed current conditions for this battle session.")
        self.clear_current_conditions_button.clicked.connect(self.current_condition_session_reset_requested.emit)

        self.current_ability_button = QPushButton("Ability")
        self.current_ability_button.setObjectName("currentAbilityButton")
        self.current_ability_button.setToolTip(
            "Open user-confirmed current ability input. This does not resolve activation, effects, damage, RNG, or order."
        )
        self.current_ability_button.clicked.connect(self.current_ability_requested.emit)

        self.switch_permission_button = QPushButton("교체 가능 여부")
        self.switch_permission_button.setObjectName("switchPermissionButton")
        self.switch_permission_button.clicked.connect(self.switch_permission_requested.emit)

        self.clear_current_abilities_button = QPushButton("Clear current abilities")
        self.clear_current_abilities_button.setObjectName("clearCurrentAbilitiesButton")
        self.clear_current_abilities_button.setToolTip("Clear user-confirmed current abilities for this battle session.")
        self.clear_current_abilities_button.clicked.connect(self.current_ability_session_reset_requested.emit)

        self.current_type_button = QPushButton("Current type")
        self.current_type_button.setObjectName("currentTypeButton")
        self.current_type_button.setToolTip("Record explicit current type authority; species/base type is not used as a fallback.")
        self.current_type_button.clicked.connect(self.current_type_requested.emit)
        self.clear_current_types_button = QPushButton("Clear current types")
        self.clear_current_types_button.setObjectName("clearCurrentTypesButton")
        self.clear_current_types_button.clicked.connect(self.current_type_session_reset_requested.emit)

        self.current_stat_stage_button = QPushButton("Stat stages")
        self.current_stat_stage_button.setToolTip("Open user-confirmed current stat stages. This does not resolve their cause or outcomes.")
        self.current_stat_stage_button.clicked.connect(self.current_stat_stage_requested.emit)
        self.clear_current_stat_stages_button = QPushButton("Clear current stat stages")
        self.clear_current_stat_stages_button.clicked.connect(self.current_stat_stage_session_reset_requested.emit)
        self.current_field_state_button = QPushButton("Field state")
        self.current_field_state_button.clicked.connect(self.current_field_state_requested.emit)
        self.clear_current_field_state_button = QPushButton("Clear field state")
        self.clear_current_field_state_button.clicked.connect(self.current_field_state_session_reset_requested.emit)
        self.current_final_stat_button = QPushButton("Final stats")
        self.current_final_stat_button.clicked.connect(self.current_final_stat_requested.emit)
        self.clear_current_final_stats_button = QPushButton("Clear final stats")
        self.clear_current_final_stats_button.clicked.connect(self.current_final_stat_session_reset_requested.emit)
        self.current_hp_button = QPushButton("Current HP")
        self.current_hp_button.clicked.connect(self.current_hp_requested.emit)
        self.clear_current_hp_button = QPushButton("Clear current HP")
        self.clear_current_hp_button.clicked.connect(self.current_hp_session_reset_requested.emit)
        self.current_battle_format_button = QPushButton("Battle Format")
        self.current_battle_format_button.clicked.connect(self.current_battle_format_requested.emit)
        self.clear_current_battle_format_button = QPushButton("Clear battle format")
        self.clear_current_battle_format_button.clicked.connect(self.current_battle_format_session_reset_requested.emit)
        self.current_observed_damage_button = QPushButton("Previous Damage")
        self.current_observed_damage_button.clicked.connect(self.current_observed_damage_requested.emit)
        self.clear_current_observed_damage_button = QPushButton("Clear previous damage")
        self.clear_current_observed_damage_button.clicked.connect(self.current_observed_damage_reset_requested.emit)
        self.battle_counter_button = QPushButton("Battle counters")
        self.battle_counter_button.clicked.connect(self.battle_counter_requested.emit)
        self.clear_battle_counter_button = QPushButton("Clear battle counters")
        self.clear_battle_counter_button.clicked.connect(self.battle_counter_reset_requested.emit)

        self.turn_pipeline_checkbox = QCheckBox("제한 컨텍스트 포함")
        self.turn_pipeline_checkbox.setObjectName("turnPipelineDevFlag")
        self.turn_pipeline_checkbox.setToolTip(TURN_PIPELINE_HELP_TEXT)
        self.turn_pipeline_checkbox.toggled.connect(self.set_turn_pipeline_status_enabled)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_edit.setFont(font)
        self.output_edit.setPlaceholderText("LLM 추천이 여기에 표시됩니다.")

        self.cost_label = QLabel("비용: 아직 호출 없음")
        self.cost_label.setObjectName("llmCostLabel")

        self.turn_pipeline_status_label = QLabel(TURN_PIPELINE_STATUS_TEXT)
        self.turn_pipeline_status_label.setObjectName("turnPipelineStatusLabel")
        self.turn_pipeline_status_label.setVisible(False)

        layout.addWidget(self.request_button)
        layout.addWidget(self.structured_request_button)
        layout.addWidget(self.readiness_button)
        layout.addWidget(self.readiness_label)
        layout.addLayout(self.readiness_input_layout)
        layout.addWidget(self.field_profile_button)
        layout.addWidget(self.item_event_button)
        layout.addWidget(self.clear_item_events_button)
        layout.addWidget(self.current_condition_button)
        layout.addWidget(self.clear_current_conditions_button)
        layout.addWidget(self.current_ability_button)
        layout.addWidget(self.switch_permission_button)
        layout.addWidget(self.clear_current_abilities_button)
        layout.addWidget(self.current_type_button)
        layout.addWidget(self.clear_current_types_button)
        layout.addWidget(self.current_stat_stage_button)
        layout.addWidget(self.clear_current_stat_stages_button)
        layout.addWidget(self.current_field_state_button)
        layout.addWidget(self.clear_current_field_state_button)
        layout.addWidget(self.current_final_stat_button)
        layout.addWidget(self.clear_current_final_stats_button)
        layout.addWidget(self.current_hp_button)
        layout.addWidget(self.clear_current_hp_button)
        layout.addWidget(self.current_battle_format_button)
        layout.addWidget(self.clear_current_battle_format_button)
        layout.addWidget(self.current_observed_damage_button)
        layout.addWidget(self.clear_current_observed_damage_button)
        layout.addWidget(self.battle_counter_button)
        layout.addWidget(self.clear_battle_counter_button)
        layout.addWidget(self.turn_pipeline_checkbox)
        layout.addWidget(self.turn_pipeline_status_label)
        layout.addWidget(self.output_edit, 1)
        layout.addWidget(self.cost_label)
        self.setStyleSheet(self._build_stylesheet())

    def turn_pipeline_enabled(self) -> bool:
        return self.turn_pipeline_checkbox.isChecked()

    def set_turn_pipeline_status_enabled(self, enabled: bool) -> None:
        self.turn_pipeline_status_label.setVisible(enabled)

    def set_item_event_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        label = "Item event" if normalized_count == 0 else f"Item event ({normalized_count})"
        self.item_event_button.setText(label)

    def set_current_condition_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        label = "Condition" if normalized_count == 0 else f"Condition ({normalized_count})"
        self.current_condition_button.setText(label)

    def set_current_ability_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        label = "Ability" if normalized_count == 0 else f"Ability ({normalized_count})"
        self.current_ability_button.setText(label)

    def set_current_type_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        self.current_type_button.setText("Current type" if normalized_count == 0 else f"Current type ({normalized_count})")

    def set_current_stat_stage_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        self.current_stat_stage_button.setText("Stat stages" if normalized_count == 0 else f"Stat stages ({normalized_count})")
    def set_current_field_state_count(self, count: int) -> None:
        self.current_field_state_button.setText("Field state" if not count else f"Field state ({count})")
    def set_current_final_stat_count(self, count: int) -> None:
        self.current_final_stat_button.setText("Final stats" if not count else f"Final stats ({count})")
    def set_current_hp_count(self, count: int) -> None:
        self.current_hp_button.setText("Current HP" if not count else f"Current HP ({count})")
    def set_current_battle_format(self, value: str | None) -> None:
        self.current_battle_format_button.setText("Battle Format" if value is None else f"Battle Format ({value})")
    def set_current_observed_damage(self, value: int | None) -> None:
        self.current_observed_damage_button.setText("Previous Damage" if value is None else f"Previous Damage ({value} HP)")
    def set_battle_counter_count(self, value: int | None) -> None:
        self.battle_counter_button.setText("Battle counters" if value is None else f"Battle counters ({value})")

    def set_running(self, is_running: bool) -> None:
        self.request_button.setDisabled(is_running)
        self.structured_request_button.setDisabled(is_running)
        self.readiness_button.setDisabled(is_running)
        self.readiness_input_button.setDisabled(is_running)
        for button in self._readiness_extra_input_buttons:
            button.setDisabled(is_running)
        self.field_profile_button.setDisabled(is_running)
        self.item_event_button.setDisabled(is_running)
        self.clear_item_events_button.setDisabled(is_running)
        self.current_condition_button.setDisabled(is_running)
        self.clear_current_conditions_button.setDisabled(is_running)
        self.current_ability_button.setDisabled(is_running)
        self.switch_permission_button.setDisabled(is_running)
        self.clear_current_abilities_button.setDisabled(is_running)
        self.current_type_button.setDisabled(is_running)
        self.clear_current_types_button.setDisabled(is_running)
        self.current_stat_stage_button.setDisabled(is_running)
        self.clear_current_stat_stages_button.setDisabled(is_running)
        self.current_field_state_button.setDisabled(is_running)
        self.clear_current_field_state_button.setDisabled(is_running)
        self.current_final_stat_button.setDisabled(is_running)
        self.clear_current_final_stats_button.setDisabled(is_running)
        self.current_hp_button.setDisabled(is_running)
        self.clear_current_hp_button.setDisabled(is_running)
        self.current_battle_format_button.setDisabled(is_running)
        self.clear_current_battle_format_button.setDisabled(is_running)
        self.current_observed_damage_button.setDisabled(is_running)
        self.clear_current_observed_damage_button.setDisabled(is_running)
        self.battle_counter_button.setDisabled(is_running)
        self.clear_battle_counter_button.setDisabled(is_running)
        self.turn_pipeline_checkbox.setDisabled(is_running)
        if is_running:
            self.output_edit.setPlainText("분석 중...")
            self.cost_label.setText("비용: 분석 중...")

    def set_advice_text(self, text: str) -> None:
        self.output_edit.setPlainText(text)

    def set_strategy_explanation(self, explanation: dict) -> dict:
        """Present a precomputed strategy explanation without invoking strategy or providers."""
        presentation = present_strategy_explanation(explanation=explanation)
        self.output_edit.setPlainText(render_strategy_explanation(presentation=presentation))
        return presentation

    def set_recommendation_readiness(self, readiness: dict) -> None:
        status = readiness.get("status") if isinstance(readiness, dict) else "unavailable"
        missing = readiness.get("missing") if isinstance(readiness, dict) else []
        unsupported = readiness.get("unsupported") if isinstance(readiness, dict) else []
        actionable_labels: list[str] = []
        unavailable_labels: list[str] = []
        actions: list[tuple[str, str]] = []
        seen_labels: set[str] = set()
        seen_actions: set[str] = set()
        for entry in missing if isinstance(missing, list) else []:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            action = entry.get("action")
            if not isinstance(label, str) or label in seen_labels:
                continue
            seen_labels.add(label)
            if isinstance(action, str):
                actionable_labels.append(label)
                if action not in seen_actions:
                    seen_actions.add(action)
                    actions.append((label, action))
            else:
                unavailable_labels.append(label)
        unsupported_labels = list(dict.fromkeys(
            entry for entry in unsupported if isinstance(entry, str)
        ))
        if status == "ready":
            text = "Deterministic recommendation readiness: ready."
        elif status == "incomplete":
            sections = ["Deterministic recommendation readiness: incomplete."]
            if actionable_labels:
                sections.append("Can confirm: " + "; ".join(actionable_labels))
            if unavailable_labels:
                sections.append("Still unavailable: " + "; ".join(unavailable_labels))
            if unsupported_labels:
                sections.append("Unsupported: " + "; ".join(unsupported_labels))
            text = " ".join(sections)
        elif status == "unsupported":
            text = "Deterministic recommendation has an unsupported mechanic."
            if unsupported_labels:
                text += " Unsupported: " + "; ".join(unsupported_labels)
        else:
            text = "Recommendation readiness is unavailable for the current selection."
        self.readiness_label.setText(text)
        self._set_readiness_actions(actions)

    def clear_recommendation_readiness(self) -> None:
        self._set_readiness_actions([])
        self.readiness_label.setText("Recommendation readiness has not been checked for this selection.")

    def _set_readiness_actions(self, actions: list[tuple[str, str]]) -> None:
        for button in self._readiness_extra_input_buttons:
            self.readiness_input_layout.removeWidget(button)
            button.deleteLater()
        self._readiness_extra_input_buttons = []
        self._readiness_action = actions[0][1] if actions else None
        self.readiness_input_button.setText(
            f"Open: {actions[0][0]}" if actions else "Open needed input"
        )
        self.readiness_input_button.setVisible(bool(actions))
        for label, action in actions[1:]:
            button = QPushButton(f"Open: {label}")
            button.setObjectName("recommendationReadinessExtraInputButton")
            button.clicked.connect(lambda _checked=False, route=action: self.readiness_input_requested.emit(route))
            self.readiness_input_layout.addWidget(button)
            self._readiness_extra_input_buttons.append(button)

    def _request_readiness_input(self) -> None:
        if self._readiness_action is not None:
            self.readiness_input_requested.emit(self._readiness_action)

    def set_mode_advice_text(self, mode: str, text: str) -> None:
        heading = "[구조화 추천]" if mode == "structured" else "[기존 조언]"
        self.output_edit.setPlainText(f"{heading}\n{text}")

    def set_cost_text(self, text: str) -> None:
        self.cost_label.setText(text)

    def set_error(self, message: str) -> None:
        self.output_edit.setPlainText(message)
        self.cost_label.setText("비용: 호출 실패")

    def clear(self) -> None:
        self.output_edit.clear()
        self.cost_label.setText("비용: 아직 호출 없음")

    @staticmethod
    def _build_stylesheet() -> str:
        return """
            QFrame#llmAdvicePanel {
                background-color: transparent;
                border: none;
            }
            QTextEdit {
                color: #17202A;
                background-color: #F8FAFC;
                border: 1px solid #D8E0EA;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton {
                background-color: #2F6FDB;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 10px;
                font-weight: 700;
            }
            QPushButton:disabled {
                background-color: #9CA9BA;
            }
            QLabel#llmCostLabel {
                color: #45566B;
                font-size: 11px;
            }
            QCheckBox#turnPipelineDevFlag {
                color: #334155;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#turnPipelineStatusLabel {
                color: #7A4E00;
                font-size: 11px;
                font-weight: 600;
            }
        """
