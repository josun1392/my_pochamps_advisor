from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QLayout, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget
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
    deterministic_strategy_requested = Signal()
    recommendation_readiness_requested = Signal()
    readiness_input_requested = Signal(str)
    field_profile_requested = Signal()
    item_event_requested = Signal()
    item_event_session_reset_requested = Signal()
    current_condition_requested = Signal()
    current_condition_session_reset_requested = Signal()
    status_progression_requested = Signal()
    pending_status_action_result_requested = Signal()
    current_ability_requested = Signal()
    current_persistent_effect_requested = Signal()
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
    contact_status_result_requested = Signal()
    contact_reactive_damage_requested = Signal()
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
        self.request_button.setText("선택 기술 LLM 조언")
        self.request_button.setToolTip("현재 선택한 기술을 중심으로 자유 형식 조언을 받습니다.")
        self.request_button.setAccessibleName("선택 기술 LLM 조언")
        self.structured_request_button = QPushButton("구조화 LLM 추천")
        self.structured_request_button.clicked.connect(self.structured_advice_requested.emit)
        self.structured_request_button.setToolTip("후보 기술 전체를 비교하고 검증된 구조화 추천을 받습니다.")
        self.structured_request_button.setAccessibleName("구조화 LLM 추천")
        self.deterministic_strategy_button = QPushButton("전략 분석")
        self.deterministic_strategy_button.setObjectName("deterministicStrategyButton")
        self.deterministic_strategy_button.setToolTip("현재 런타임 권한으로 오프라인 결정론 전략 분석을 실행합니다. Gemini를 호출하지 않습니다.")
        self.deterministic_strategy_button.setAccessibleName("전략 분석")
        self.deterministic_strategy_button.clicked.connect(self.deterministic_strategy_requested.emit)
        self.readiness_button = QPushButton("필요 정보 확인")
        self.readiness_button.setObjectName("recommendationReadinessButton")
        self.readiness_button.setToolTip("현재 결정론 전략 분석에 실제로 필요한 확인 정보만 표시합니다.")
        self.readiness_button.clicked.connect(self.recommendation_readiness_requested.emit)
        self.readiness_label = QLabel("필요 정보가 아직 확인되지 않았습니다.")
        self.readiness_label.setObjectName("recommendationReadinessLabel")
        self.readiness_label.setWordWrap(True)
        self.readiness_input_button = QPushButton("필요한 정보 입력")
        self.readiness_input_button.setObjectName("recommendationReadinessInputButton")
        self.readiness_input_button.setVisible(False)
        self.readiness_input_button.clicked.connect(self._request_readiness_input)
        self._readiness_action: str | None = None
        self._readiness_extra_input_buttons: list[QPushButton] = []
        self.readiness_input_layout = QVBoxLayout()
        self.readiness_input_layout.setContentsMargins(0, 0, 0, 0)
        self.readiness_input_layout.setSpacing(4)
        self.readiness_input_layout.addWidget(self.readiness_input_button)

        self.field_profile_button = QPushButton("추가 필드 프로필 (위험물/벽)")
        self.field_profile_button.setObjectName("fieldProfileButton")
        self.field_profile_button.setToolTip(
            "Open user-confirmed current field state input. This does not set duration, expiration, "
            "post-turn state, damage precision, or full turn outcome."
        )
        self.field_profile_button.clicked.connect(self.field_profile_requested.emit)

        self.item_event_button = QPushButton("도구 이벤트 기록")
        self.item_event_button.setObjectName("itemEventButton")
        self.item_event_button.setToolTip(
            "Open user-confirmed observed item event input. This does not calculate resolved effects, "
            "exact HP, damage, RNG, or turn order."
        )
        self.item_event_button.clicked.connect(self.item_event_requested.emit)

        self.clear_item_events_button = QPushButton("도구 이벤트 입력 표시 초기화")
        self.clear_item_events_button.setObjectName("clearItemEventsButton")
        self.clear_item_events_button.setToolTip("Clear user-confirmed item events for this battle session.")
        self.clear_item_events_button.clicked.connect(self.item_event_session_reset_requested.emit)

        self.current_condition_button = QPushButton("현재 상태이상")
        self.current_condition_button.setObjectName("currentConditionButton")
        self.current_condition_button.setToolTip(
            "Open user-confirmed current major condition input. This does not resolve events, damage, duration, RNG, or order."
        )
        self.current_condition_button.clicked.connect(self.current_condition_requested.emit)

        self.clear_current_conditions_button = QPushButton("현재 상태이상 입력 표시 초기화")
        self.clear_current_conditions_button.setObjectName("clearCurrentConditionsButton")
        self.clear_current_conditions_button.setToolTip("Clear user-confirmed current conditions for this battle session.")
        self.clear_current_conditions_button.clicked.connect(self.current_condition_session_reset_requested.emit)

        self.status_progression_button = QPushButton("수면·얼음 진행 정보")
        self.status_progression_button.setObjectName("statusProgressionButton")
        self.status_progression_button.setToolTip("Confirm explicit progression knowledge for the current runtime sleep/freeze episode. No duration or attempts are inferred.")
        self.status_progression_button.clicked.connect(self.status_progression_requested.emit)

        self.pending_status_action_result_button = QPushButton("수면·얼음 행동 결과 기록")
        self.pending_status_action_result_button.setObjectName("pendingStatusActionResultButton")
        self.pending_status_action_result_button.setToolTip("Confirm only an actually observed Sleep/Freeze action result. Selection alone records nothing.")
        self.pending_status_action_result_button.clicked.connect(self.pending_status_action_result_requested.emit)

        self.current_ability_button = QPushButton("현재 특성")
        self.current_ability_button.setObjectName("currentAbilityButton")
        self.current_ability_button.setToolTip(
            "Open user-confirmed current ability input. This does not resolve activation, effects, damage, RNG, or order."
        )
        self.current_ability_button.clicked.connect(self.current_ability_requested.emit)

        self.current_persistent_effect_button = QPushButton("지속 효과")
        self.current_persistent_effect_button.setObjectName("currentPersistentEffectButton")
        self.current_persistent_effect_button.setToolTip("Record only an explicit current persistent-effect observation.")
        self.current_persistent_effect_button.clicked.connect(self.current_persistent_effect_requested.emit)

        self.switch_permission_button = QPushButton("교체 가능 여부")
        self.switch_permission_button.setObjectName("switchPermissionButton")
        self.switch_permission_button.clicked.connect(self.switch_permission_requested.emit)

        self.clear_current_abilities_button = QPushButton("현재 특성 입력 표시 초기화")
        self.clear_current_abilities_button.setObjectName("clearCurrentAbilitiesButton")
        self.clear_current_abilities_button.setToolTip("Clear user-confirmed current abilities for this battle session.")
        self.clear_current_abilities_button.clicked.connect(self.current_ability_session_reset_requested.emit)

        self.current_type_button = QPushButton("현재 타입")
        self.current_type_button.setObjectName("currentTypeButton")
        self.current_type_button.setToolTip("Record explicit current type authority; species/base type is not used as a fallback.")
        self.current_type_button.clicked.connect(self.current_type_requested.emit)
        self.clear_current_types_button = QPushButton("현재 타입 입력 표시 초기화")
        self.clear_current_types_button.setObjectName("clearCurrentTypesButton")
        self.clear_current_types_button.clicked.connect(self.current_type_session_reset_requested.emit)

        self.current_stat_stage_button = QPushButton("현재 랭크 변화")
        self.current_stat_stage_button.setToolTip("Open user-confirmed current stat stages. This does not resolve their cause or outcomes.")
        self.current_stat_stage_button.clicked.connect(self.current_stat_stage_requested.emit)
        self.clear_current_stat_stages_button = QPushButton("현재 랭크 입력 표시 초기화")
        self.clear_current_stat_stages_button.clicked.connect(self.current_stat_stage_session_reset_requested.emit)
        self.current_field_state_button = QPushButton("현재 전장 상태")
        self.current_field_state_button.clicked.connect(self.current_field_state_requested.emit)
        self.clear_current_field_state_button = QPushButton("현재 전장 입력 표시 초기화")
        self.clear_current_field_state_button.clicked.connect(self.current_field_state_session_reset_requested.emit)
        self.current_final_stat_button = QPushButton("확정 실능력치 (랭크 제외)")
        self.current_final_stat_button.clicked.connect(self.current_final_stat_requested.emit)
        self.clear_current_final_stats_button = QPushButton("실능력치 입력 표시 초기화")
        self.clear_current_final_stats_button.clicked.connect(self.current_final_stat_session_reset_requested.emit)
        self.current_hp_button = QPushButton("현재 HP")
        self.current_hp_button.clicked.connect(self.current_hp_requested.emit)
        self.clear_current_hp_button = QPushButton("현재 HP 입력 표시 초기화")
        self.clear_current_hp_button.clicked.connect(self.current_hp_session_reset_requested.emit)
        self.current_battle_format_button = QPushButton("배틀 형식")
        self.current_battle_format_button.clicked.connect(self.current_battle_format_requested.emit)
        self.clear_current_battle_format_button = QPushButton("배틀 형식 입력 표시 초기화")
        self.clear_current_battle_format_button.clicked.connect(self.current_battle_format_session_reset_requested.emit)
        self.current_observed_damage_button = QPushButton("직전 실제 피해 기록")
        self.current_observed_damage_button.clicked.connect(self.current_observed_damage_requested.emit)
        self.clear_current_observed_damage_button = QPushButton("직전 피해 입력 표시 초기화")
        self.clear_current_observed_damage_button.clicked.connect(self.current_observed_damage_reset_requested.emit)
        self.contact_status_result_button = QPushButton("접촉 상태효과 결과 기록")
        self.contact_status_result_button.setObjectName("contactStatusResultButton")
        self.contact_status_result_button.setToolTip("Confirm an actually observed contact-status result. Selection alone records nothing.")
        self.contact_status_result_button.clicked.connect(self.contact_status_result_requested.emit)
        self.contact_reactive_damage_button = QPushButton("접촉 반응 피해 기록")
        self.contact_reactive_damage_button.setObjectName("contactReactiveDamageButton")
        self.contact_reactive_damage_button.setToolTip("Confirm actually observed Rough Skin / Iron Barbs / Rocky Helmet damage. The UI does not calculate it.")
        self.contact_reactive_damage_button.clicked.connect(self.contact_reactive_damage_requested.emit)
        self.battle_counter_button = QPushButton("특수 기술 카운터")
        self.battle_counter_button.clicked.connect(self.battle_counter_requested.emit)
        self.clear_battle_counter_button = QPushButton("특수 기술 카운터 입력 표시 초기화")
        self.clear_battle_counter_button.clicked.connect(self.battle_counter_reset_requested.emit)

        self.turn_pipeline_checkbox = QCheckBox("고급 LLM 컨텍스트 포함")
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

        self.recommendation_section_label = self._section_header("추천 준비", "recommendationSectionHeader")
        layout.addWidget(self.recommendation_section_label)
        layout.addWidget(self.readiness_button)
        layout.addWidget(self.readiness_label)
        layout.addLayout(self.readiness_input_layout)
        layout.addWidget(self.deterministic_strategy_button)

        self.auxiliary_scroll_area = QScrollArea()
        self.auxiliary_scroll_area.setObjectName("auxiliaryBattleInputScrollArea")
        self.auxiliary_scroll_area.setWidgetResizable(True)
        self.auxiliary_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.auxiliary_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.auxiliary_controls_widget = QWidget()
        self.auxiliary_controls_widget.setObjectName("auxiliaryBattleInputControls")
        auxiliary_layout = QVBoxLayout(self.auxiliary_controls_widget)
        auxiliary_layout.setContentsMargins(0, 0, 0, 0)
        auxiliary_layout.setSpacing(6)
        auxiliary_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        self.current_state_section_label = self._section_header("현재 상태", "currentStateSectionHeader")
        self.observed_section_label = self._section_header("관측 기록", "observedSectionHeader")
        self.advanced_section_label = self._section_header("고급 / 특수", "advancedSectionHeader")
        self.llm_tools_section_label = self._section_header("LLM 도구", "llmToolsSectionHeader")
        self.reset_section_label = self._section_header("입력 표시 초기화", "resetSectionHeader")

        self._current_state_buttons = [
            self.current_hp_button,
            self.current_condition_button,
            self.current_ability_button,
            self.current_type_button,
            self.current_stat_stage_button,
            self.current_field_state_button,
            self.switch_permission_button,
        ]
        self._observed_event_buttons = [
            self.item_event_button,
            self.current_observed_damage_button,
        ]
        self._advanced_special_buttons = [
            self.status_progression_button,
            self.pending_status_action_result_button,
            self.current_persistent_effect_button,
            self.current_final_stat_button,
            self.current_battle_format_button,
            self.contact_status_result_button,
            self.contact_reactive_damage_button,
            self.battle_counter_button,
        ]
        self._llm_tool_buttons = [
            self.request_button,
            self.structured_request_button,
            self.field_profile_button,
        ]
        self._reset_buttons = [
            self.clear_item_events_button,
            self.clear_current_conditions_button,
            self.clear_current_abilities_button,
            self.clear_current_types_button,
            self.clear_current_stat_stages_button,
            self.clear_current_field_state_button,
            self.clear_current_final_stats_button,
            self.clear_current_hp_button,
            self.clear_current_battle_format_button,
            self.clear_current_observed_damage_button,
            self.clear_battle_counter_button,
        ]
        self._auxiliary_input_buttons = [
            *self._current_state_buttons,
            *self._observed_event_buttons,
            *self._advanced_special_buttons,
            *self._llm_tool_buttons,
            *self._reset_buttons,
        ]
        for button in self._auxiliary_input_buttons:
            button.setMinimumHeight(32)
        for button in self._reset_buttons:
            button.setProperty("resetAction", True)

        auxiliary_layout.addWidget(self.current_state_section_label)
        for button in self._current_state_buttons:
            auxiliary_layout.addWidget(button)

        auxiliary_layout.addWidget(self.observed_section_label)
        for button in self._observed_event_buttons:
            auxiliary_layout.addWidget(button)

        auxiliary_layout.addWidget(self.advanced_section_label)
        for button in self._advanced_special_buttons:
            auxiliary_layout.addWidget(button)

        auxiliary_layout.addWidget(self.llm_tools_section_label)
        for button in self._llm_tool_buttons:
            auxiliary_layout.addWidget(button)
        auxiliary_layout.addWidget(self.turn_pipeline_checkbox)
        self.turn_pipeline_status_label.setWordWrap(True)
        auxiliary_layout.addWidget(self.turn_pipeline_status_label)

        auxiliary_layout.addWidget(self.reset_section_label)
        for button in self._reset_buttons:
            auxiliary_layout.addWidget(button)

        auxiliary_layout.addStretch(1)
        self.auxiliary_scroll_area.setWidget(self.auxiliary_controls_widget)

        layout.addWidget(self.auxiliary_scroll_area, 1)
        layout.addWidget(self.output_edit, 1)
        layout.addWidget(self.cost_label)
        self.setStyleSheet(self._build_stylesheet())

    @staticmethod
    def _section_header(text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setProperty("sectionHeader", True)
        return label

    def turn_pipeline_enabled(self) -> bool:
        return self.turn_pipeline_checkbox.isChecked()

    def set_turn_pipeline_status_enabled(self, enabled: bool) -> None:
        self.turn_pipeline_status_label.setVisible(enabled)

    def set_item_event_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        label = "도구 이벤트 기록" if normalized_count == 0 else f"도구 이벤트 기록 ({normalized_count})"
        self.item_event_button.setText(label)

    def set_current_condition_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        label = "현재 상태이상" if normalized_count == 0 else f"현재 상태이상 ({normalized_count})"
        self.current_condition_button.setText(label)

    def set_status_progression_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        self.status_progression_button.setText("수면·얼음 진행 정보" if normalized_count == 0 else f"수면·얼음 진행 정보 ({normalized_count})")

    def set_current_ability_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        label = "현재 특성" if normalized_count == 0 else f"현재 특성 ({normalized_count})"
        self.current_ability_button.setText(label)

    def set_current_persistent_effect_count(self, count: int) -> None:
        count = max(0, int(count))
        self.current_persistent_effect_button.setText("지속 효과" if count == 0 else f"지속 효과 ({count})")

    def set_current_type_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        self.current_type_button.setText("현재 타입" if normalized_count == 0 else f"현재 타입 ({normalized_count})")

    def set_current_stat_stage_count(self, count: int) -> None:
        normalized_count = max(0, int(count))
        self.current_stat_stage_button.setText("현재 랭크 변화" if normalized_count == 0 else f"현재 랭크 변화 ({normalized_count})")
    def set_current_field_state_count(self, count: int) -> None:
        self.current_field_state_button.setText("현재 전장 상태" if not count else f"현재 전장 상태 ({count})")
    def set_current_final_stat_count(self, count: int) -> None:
        self.current_final_stat_button.setText("확정 실능력치 (랭크 제외)" if not count else f"확정 실능력치 (랭크 제외) ({count})")
    def set_current_hp_count(self, count: int) -> None:
        self.current_hp_button.setText("현재 HP" if not count else f"현재 HP ({count})")
    def set_current_battle_format(self, value: str | None) -> None:
        self.current_battle_format_button.setText("배틀 형식" if value is None else f"배틀 형식 ({value})")
    def set_current_observed_damage(self, value: int | None) -> None:
        self.current_observed_damage_button.setText("직전 실제 피해 기록" if value is None else f"직전 실제 피해 기록 ({value} HP)")
    def set_battle_counter_count(self, value: int | None) -> None:
        self.battle_counter_button.setText("특수 기술 카운터" if value is None else f"특수 기술 카운터 ({value})")

    def set_running(self, is_running: bool) -> None:
        self.request_button.setDisabled(is_running)
        self.structured_request_button.setDisabled(is_running)
        self.deterministic_strategy_button.setDisabled(is_running)
        self.readiness_button.setDisabled(is_running)
        self.readiness_input_button.setDisabled(is_running)
        for button in self._readiness_extra_input_buttons:
            button.setDisabled(is_running)
        self.field_profile_button.setDisabled(is_running)
        self.item_event_button.setDisabled(is_running)
        self.clear_item_events_button.setDisabled(is_running)
        self.current_condition_button.setDisabled(is_running)
        self.clear_current_conditions_button.setDisabled(is_running)
        self.status_progression_button.setDisabled(is_running)
        self.pending_status_action_result_button.setDisabled(is_running)
        self.current_ability_button.setDisabled(is_running)
        self.current_persistent_effect_button.setDisabled(is_running)
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
        self.contact_status_result_button.setDisabled(is_running)
        self.contact_reactive_damage_button.setDisabled(is_running)
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

    @staticmethod
    def _readiness_user_label(label: str, action: str | None) -> str:
        by_action = {
            "current_hp": "현재 HP",
            "current_type": "현재 타입",
            "current_condition": "현재 상태이상",
            "current_stat_stage": "현재 랭크 변화",
            "current_field_state": "현재 전장 상태",
            "current_ability": "현재 특성",
            "current_item": "현재 지닌 도구",
            "field_profile": "추가 필드 프로필 (위험물/벽)",
            "switch_permission": "교체 가능 여부",
            "current_observed_damage": "직전 실제 피해",
        }
        if action in by_action:
            return by_action[action]
        special = {
            "Toxic progression authority missing": "독성 진행 정보",
            "Opponent move/result authority missing": "상대 기술/결과 관측 정보",
            "Required deterministic authority is unavailable": "추가 결정론 권한 정보",
        }
        return special.get(label, label)

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
            raw_label = entry.get("label")
            action = entry.get("action")
            if not isinstance(raw_label, str):
                continue
            label = self._readiness_user_label(raw_label, action if isinstance(action, str) else None)
            if label in seen_labels:
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
            "선택한 기술의 일부 메커니즘은 아직 지원되지 않습니다."
            if entry == "This selected mechanic is not supported yet" else entry
            for entry in unsupported if isinstance(entry, str)
        ))
        if status == "ready":
            text = "전략 분석에 필요한 확인 정보가 준비되었습니다."
        elif status == "incomplete":
            sections = ["추가 확인 정보가 필요합니다."]
            if actionable_labels:
                sections.append("입력 가능: " + "; ".join(actionable_labels))
            if unavailable_labels:
                sections.append("현재 직접 입력 경로 없음: " + "; ".join(unavailable_labels))
            if unsupported_labels:
                sections.append("지원 범위: " + "; ".join(unsupported_labels))
            text = " ".join(sections)
        elif status == "unsupported":
            text = "선택한 기술에 아직 지원되지 않는 메커니즘이 있습니다."
            if unsupported_labels:
                text += " " + "; ".join(unsupported_labels)
        else:
            text = "현재 선택에서는 필요 정보를 확인할 수 없습니다."
        self.readiness_label.setText(text)
        self._set_readiness_actions(actions)

    def clear_recommendation_readiness(self) -> None:
        self._set_readiness_actions([])
        self.readiness_label.setText("현재 선택의 필요 정보가 아직 확인되지 않았습니다.")


    def _set_readiness_actions(self, actions: list[tuple[str, str]]) -> None:
        for button in self._readiness_extra_input_buttons:
            self.readiness_input_layout.removeWidget(button)
            button.deleteLater()
        self._readiness_extra_input_buttons = []
        self._readiness_action = actions[0][1] if actions else None
        self.readiness_input_button.setText(
            f"입력하기: {actions[0][0]}" if actions else "필요한 정보 입력"
        )
        self.readiness_input_button.setVisible(bool(actions))
        for label, action in actions[1:]:
            button = QPushButton(f"입력하기: {label}")
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
            QLabel[sectionHeader="true"] {
                color: #334155;
                font-size: 12px;
                font-weight: 800;
                padding-top: 8px;
                padding-bottom: 2px;
            }
            QPushButton[resetAction="true"] {
                background-color: #E5EAF0;
                color: #45566B;
                border: 1px solid #CAD3DF;
                font-weight: 600;
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
