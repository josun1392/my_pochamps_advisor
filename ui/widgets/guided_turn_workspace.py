"""Presentation-only Decide / Record stage over the existing battle contracts."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSplitter, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)


def _section(text: str, name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    label.setStyleSheet("font-size: 15px; font-weight: 700; color: #17202A;")
    return label


class GuidedTurnWorkspace(QFrame):
    """All draft and phase state here is local; only final signals reach MainWindow."""

    analysis_requested = Signal()
    current_hp_requested = Signal()
    next_turn_requested = Signal()
    readiness_input_requested = Signal(str)
    record_commit_requested = Signal(object)
    switch_requested = Signal()
    condition_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("guidedTurnWorkspace")
        self.setStyleSheet("#guidedTurnWorkspace { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; }")
        self.phase = "decide"
        self._readiness_action: str | None = None
        self._dismissed_readiness_basis: object = object()
        self._considered_key: tuple | None = None
        self._considered_action: dict | None = None
        self._recorded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(7)
        header = QHBoxLayout()
        self.header_label = QLabel("배틀: 비활성 · 턴: 미확인")
        self.header_label.setObjectName("guidedTurnHeaderLabel")
        self.header_label.setStyleSheet("font-weight: 700; color: #334155;")
        self.decide_phase_button = QPushButton("기록 닫기")
        self.decide_phase_button.setObjectName("decidePhaseButton")
        self.record_phase_button = QPushButton("빠른 기록")
        self.record_phase_button.setObjectName("recordPhaseButton")
        self.decide_phase_button.clicked.connect(lambda: self.set_phase("decide"))
        self.record_phase_button.clicked.connect(lambda: self.set_phase("record"))
        header.addWidget(self.header_label, 1)
        header.addWidget(self.decide_phase_button)
        header.addWidget(self.record_phase_button)
        layout.addLayout(header)

        self.situation_label = QLabel("내 포켓몬: 미확인 (HP 미확인)  VS  상대: 미확인 (HP 미확인)")
        self.situation_label.setObjectName("guidedSituationLabel")
        self.situation_label.setWordWrap(True)
        self.situation_label.setStyleSheet("padding: 8px; background: white; border: 1px solid #D8E0EA; border-radius: 6px;")
        layout.addWidget(self.situation_label)

        self.stage_stack = QStackedWidget()
        self.stage_stack.setObjectName("battleStageStack")
        self.decide_stage = QWidget()
        decide = QVBoxLayout(self.decide_stage)
        decide.setContentsMargins(0, 0, 0, 0)
        decide.setSpacing(6)

        self.decision_splitter = QSplitter(Qt.Orientation.Vertical)
        self.decision_splitter.setObjectName("decisionQuickRecorderSplitter")
        self.decision_splitter.setChildrenCollapsible(False)
        self.decision_splitter.setHandleWidth(6)
        self.decision_content = QWidget()
        decision = QVBoxLayout(self.decision_content)
        decision.setContentsMargins(0, 0, 0, 0)
        decision.setSpacing(6)
        decision.addWidget(_section("이번 턴 추천", "decideStageTitle"))
        self.considered_label = QLabel("고려 중: 없음 · 내 포켓몬의 기술을 선택할 수 있습니다.")
        self.considered_label.setObjectName("guidedConsideredLabel")
        decision.addWidget(self.considered_label)
        self.analysis_label = QLabel("아직 분석하지 않음")
        self.analysis_label.setObjectName("guidedAnalysisLabel")
        self.analysis_label.setWordWrap(True)
        decision.addWidget(self.analysis_label)
        self.board_scroll = QScrollArea()
        self.board_scroll.setObjectName("recommendationBoard")
        self.board_scroll.setWidgetResizable(True)
        self.board_scroll.setMinimumHeight(180)
        self.board_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.board_widget = QWidget()
        self.board_layout = QVBoxLayout(self.board_widget)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(6)
        self.board_scroll.setWidget(self.board_widget)
        self.candidate_rows: list[QFrame] = []
        self.set_board_state("전략 분석을 실행하면 평가 가능한 행동이 여기에 표시됩니다.")
        decision.addWidget(self.board_scroll, 1)
        self.readiness_label = QLabel("필요 정보는 현재 상황에 맞춰 표시됩니다.")
        self.readiness_label.setObjectName("guidedReadinessLabel")
        self.readiness_label.setWordWrap(True)
        decision.addWidget(self.readiness_label)
        readiness_actions = QHBoxLayout()
        self.readiness_input_button = QPushButton("현재 정보 입력")
        self.readiness_input_button.setObjectName("guidedReadinessInputButton")
        self.readiness_input_button.hide()
        self.readiness_input_button.clicked.connect(self._request_readiness_input)
        self.readiness_skip_button = QPushButton("모름으로 유지")
        self.readiness_skip_button.setObjectName("guidedReadinessSkipButton")
        self.readiness_skip_button.hide()
        self.readiness_skip_button.clicked.connect(self._dismiss_readiness)
        readiness_actions.addWidget(self.readiness_input_button)
        readiness_actions.addWidget(self.readiness_skip_button)
        readiness_actions.addStretch(1)
        decision.addLayout(readiness_actions)
        self.analysis_button = QPushButton("전략 분석")
        self.analysis_button.setObjectName("guidedStrategyButton")
        self.analysis_button.setMinimumHeight(36)
        self.analysis_button.clicked.connect(self.analysis_requested.emit)
        decision.addWidget(self.analysis_button)

        self.record_stage = QFrame()
        self.record_stage.setObjectName("quickRecorder")
        self.record_stage.setMinimumHeight(220)
        self.record_stage.setStyleSheet(
            "QFrame#quickRecorder { background: #FFFFFF; border: 1px solid #D8E0EA; border-radius: 6px; }"
        )
        record = QVBoxLayout(self.record_stage)
        record.setContentsMargins(8, 8, 8, 8)
        record.setSpacing(8)

        self.record_body_scroll = QScrollArea()
        self.record_body_scroll.setObjectName("recordBodyScroll")
        self.record_body_scroll.setWidgetResizable(True)
        self.record_body_scroll.setMinimumHeight(185)
        self.record_body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.record_body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.record_body_widget = QWidget()
        record_body = QVBoxLayout(self.record_body_widget)
        record_body.setContentsMargins(0, 0, 0, 0)
        record_body.setSpacing(8)
        record_body.addWidget(_section("실제 결과 기록", "recordStageTitle"))
        self.record_ghost_label = QLabel("고려했던 기술: 없음")
        self.record_ghost_label.setObjectName("recordGhostLabel")
        record_body.addWidget(self.record_ghost_label)
        self.execution_check = QCheckBox("이 기술이 실제로 실행된 것을 확인했습니다")
        self.execution_check.setObjectName("recordExecutionCheck")
        self.execution_check.toggled.connect(self._update_record_commit_enabled)
        record_body.addWidget(self.execution_check)
        self.result_combo = QComboBox()
        self.result_combo.setObjectName("recordResultCombo")
        self.result_combo.addItem("결과를 선택하세요", "unselected")
        self.result_combo.addItem("기술 성공", "success")
        self.result_combo.addItem("정확도 실패 / 빗나감", "accuracy_miss")
        self.result_combo.addItem("보호에 막힘", "protection_block")
        self.result_combo.addItem("실행은 확인했지만 결과는 모름", None)
        self.result_combo.currentIndexChanged.connect(self._update_record_commit_enabled)
        record_body.addWidget(self.result_combo)
        draft_actions = QHBoxLayout()
        self.record_confirm_button = QPushButton("기록 확정")
        self.record_confirm_button.setObjectName("recordConfirmButton")
        self.record_confirm_button.setEnabled(False)
        self.record_confirm_button.clicked.connect(self._commit_record_draft)
        self.record_clear_button = QPushButton("초안 지우기")
        self.record_clear_button.setObjectName("recordClearButton")
        self.record_clear_button.clicked.connect(self.clear_record_draft)
        draft_actions.addWidget(self.record_confirm_button)
        draft_actions.addWidget(self.record_clear_button)
        record_body.addLayout(draft_actions)
        self.record_status_label = QLabel("실행을 확인하지 않았다면 기록하지 않아도 됩니다.")
        self.record_status_label.setObjectName("recordStatusLabel")
        self.record_status_label.setWordWrap(True)
        record_body.addWidget(self.record_status_label)
        secondary = QHBoxLayout()
        self.current_hp_button = QPushButton("현재 HP 입력")
        self.current_hp_button.setObjectName("guidedCurrentHPButton")
        self.current_hp_button.clicked.connect(self.current_hp_requested.emit)
        self.switch_button = QPushButton("교체 기록")
        self.switch_button.setObjectName("guidedSwitchButton")
        self.switch_button.clicked.connect(self.switch_requested.emit)
        self.condition_button = QPushButton("상태이상 상세")
        self.condition_button.setObjectName("guidedConditionButton")
        self.condition_button.clicked.connect(self.condition_requested.emit)
        for button in (self.current_hp_button, self.switch_button, self.condition_button):
            secondary.addWidget(button)
        record_body.addLayout(secondary)
        record_body.addStretch(1)
        self.record_body_scroll.setWidget(self.record_body_widget)
        record.addWidget(self.record_body_scroll, 1)

        self.decision_splitter.addWidget(self.decision_content)
        self.decision_splitter.addWidget(self.record_stage)
        self.decision_splitter.setStretchFactor(0, 3)
        self.decision_splitter.setStretchFactor(1, 2)
        self.decision_splitter.setSizes([360, 240])
        self._recorder_split_sizes = [360, 240]
        decide.addWidget(self.decision_splitter, 1)

        self.next_turn_button = QPushButton("다음 턴 (미기록 허용)")
        self.next_turn_button.setObjectName("guidedNextTurnButton")
        self.next_turn_button.setMinimumHeight(36)
        self.next_turn_button.clicked.connect(self.next_turn_requested.emit)
        decide.addWidget(self.next_turn_button)

        self.stage_stack.addWidget(self.decide_stage)
        layout.addWidget(self.stage_stack, 3)

        self.details_tabs = QTabWidget()
        self.details_tabs.setObjectName("battleDetailsTabs")
        probability = QWidget()
        probability_layout = QVBoxLayout(probability)
        self.probability_label = QLabel("표시할 정확한 확률이 없습니다. 분석 후 계산 가능한 결과만 표시합니다.")
        self.probability_label.setObjectName("guidedProbabilityLabel")
        self.probability_label.setWordWrap(True)
        probability_layout.addWidget(self.probability_label)
        probability_layout.addStretch(1)
        self.details_tabs.addTab(probability, "확률")
        layout.addWidget(self.details_tabs, 1)
        self.set_phase("decide")

    def install_details(self, explanation: QWidget, advanced: QWidget) -> None:
        self.details_tabs.addTab(explanation, "설명")
        self.details_tabs.addTab(advanced, "고급 입력")

    def set_phase(self, phase: str) -> None:
        """Compatibility API: phase is presentation focus, never battle truth."""
        if phase not in {"decide", "record"}:
            return
        self.phase = phase
        recorder_open = phase == "record"
        self.stage_stack.setCurrentWidget(self.decide_stage)
        if recorder_open:
            self.record_stage.show()
            self.decision_splitter.setSizes(self._recorder_split_sizes)
        else:
            if not self.record_stage.isHidden():
                sizes = self.decision_splitter.sizes()
                if len(sizes) == 2 and all(size > 0 for size in sizes):
                    self._recorder_split_sizes = sizes
            self.record_stage.hide()
        self.decide_phase_button.setVisible(recorder_open)
        self.record_phase_button.setEnabled(not recorder_open)

    def set_considered_action(self, action: dict | None) -> None:
        key = ((action.get("session_id"), action.get("turn_number"), action.get("owner_slot"),
                action.get("owner_id"), action.get("move_slot"), action.get("move_id"), action.get("revision"))
               if isinstance(action, dict) else None)
        if key != self._considered_key:
            self._considered_key = key
            self._considered_action = dict(action) if isinstance(action, dict) else None
            self.clear_record_draft()
        name = action.get("name") if isinstance(action, dict) else None
        self.considered_label.setText(f"고려 중: {name}" if name else "고려 중: 없음 · 내 포켓몬의 기술을 선택할 수 있습니다.")
        self.record_ghost_label.setText(f"고려했던 기술: {name} (아직 기록되지 않음)" if name else "고려했던 기술: 없음")
        self._update_record_commit_enabled()

    def clear_record_draft(self) -> None:
        self.execution_check.setChecked(False)
        self.result_combo.setCurrentIndex(0)
        self.record_confirm_button.setEnabled(False)

    def _update_record_commit_enabled(self, *_args) -> None:
        self.record_confirm_button.setEnabled(
            not self._recorded and self._considered_action is not None and self.execution_check.isChecked()
            and self.result_combo.currentData() != "unselected"
        )

    def _commit_record_draft(self) -> None:
        if not self.record_confirm_button.isEnabled() or self._considered_action is None:
            return
        self.record_commit_requested.emit({"considered": dict(self._considered_action),
                                           "result_class": self.result_combo.currentData()})

    def set_record_status(self, *, recorded: bool, result_known: bool = True) -> None:
        self._recorded = recorded
        self.record_status_label.setText(
            ("실행/결과 관측됨" if result_known else "실행 관측됨 · 결과 미확인")
            if recorded else "실행을 확인하지 않았다면 기록하지 않아도 됩니다."
        )
        self.next_turn_button.setText("내 행동 기록됨 · 다음 턴" if recorded else "다음 턴 (미기록 허용)")
        if recorded:
            self.clear_record_draft()

    def set_board_state(self, message: str) -> None:
        for row in self.candidate_rows:
            self.board_layout.removeWidget(row)
            row.deleteLater()
        self.candidate_rows = []
        if not hasattr(self, "board_empty_label"):
            self.board_empty_label = QLabel()
            self.board_empty_label.setObjectName("recommendationEmptyLabel")
            self.board_empty_label.setWordWrap(True)
            self.board_layout.addWidget(self.board_empty_label)
        self.board_empty_label.setText(message)
        self.board_empty_label.show()

    def set_recommendation(self, presentation: Mapping) -> None:
        if presentation.get("status") != "resolved":
            self.set_board_state("현재 상황은 완전히 분석하지 못했습니다.")
            return
        candidates = presentation.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            self.set_board_state("평가 가능한 행동이 없습니다. 자세한 내용은 설명을 확인하세요.")
            return
        self.set_board_state("")
        overall = presentation.get("overall_status")
        frontier = presentation.get("preferred_frontier", [])
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            card = QFrame()
            card.setObjectName("recommendationCandidateRow")
            card.setStyleSheet("QFrame#recommendationCandidateRow { background: white; border: 1px solid #D8E0EA; border-radius: 6px; }")
            body = QVBoxLayout(card)
            body.setContentsMargins(9, 7, 9, 7)
            body.setSpacing(2)
            is_frontier = candidate.get("candidate_id") in frontier
            comparable = overall in {"uniquely_preferred", "tied_preferred_set"}
            marker = "★ 분석상 선호 · " if is_frontier and comparable else ""
            title = QLabel(marker + str(candidate.get("label") or candidate.get("candidate_id") or "이름 미확인"))
            title.setStyleSheet("font-weight: 700; color: #17202A;")
            body.addWidget(title)
            incomplete = candidate.get("incomplete_reason") or candidate.get("evidence_class") in {"incomplete", "unsupported"}
            state = "분석 불완전 / 미평가" if incomplete else "평가 정보 있음"
            if not comparable and is_frontier:
                state += " · 비교 불완전"
            details = candidate.get("reason_labels") or candidate.get("uncertainty_labels") or []
            reason = details[0] if isinstance(details, list) and details and isinstance(details[0], str) else None
            subtitle = QLabel(state + (f" · {reason}" if reason else ""))
            subtitle.setWordWrap(True)
            body.addWidget(subtitle)
            self.board_layout.addWidget(card)
            self.candidate_rows.append(card)
        self.board_empty_label.setVisible(not self.candidate_rows)

    def set_probability_metrics(self, metrics: Mapping | None) -> None:
        lines = ["범위: 즉시 내 행동 결과 (상대 행동 및 턴 종료 효과 제외)"]
        if isinstance(metrics, Mapping):
            for candidate_id, row in metrics.items():
                if not isinstance(candidate_id, str) or not isinstance(row, Mapping):
                    continue
                if (row.get("status") != "resolved" or row.get("schema_version") != "exact-outcome-descriptive-metrics-v1"
                        or row.get("horizon") != "immediate_action_consequence" or row.get("candidate_id") != candidate_id):
                    continue
                for side, key, label in (("target", "ko_probability", "상대 즉시 기절"),
                                         ("own", "self_faint_probability", "내 즉시 기절")):
                    group = row.get(side)
                    probability = group.get(key) if isinstance(group, Mapping) and group.get("status") == "resolved" else None
                    numerator = probability.get("numerator") if isinstance(probability, Mapping) else None
                    denominator = probability.get("denominator") if isinstance(probability, Mapping) else None
                    if (isinstance(numerator, int) and not isinstance(numerator, bool) and
                            isinstance(denominator, int) and not isinstance(denominator, bool) and
                            denominator > 0 and 0 <= numerator <= denominator):
                        lines.append(f"{candidate_id} · {label}: {numerator}/{denominator}")
        self.probability_label.setText("\n".join(lines) if len(lines) > 1 else
                                       "표시할 정확한 확률이 없습니다. 분석 후 계산 가능한 결과만 표시합니다.")

    def set_readiness(self, text: str, action: str | None = None,
                      action_label: str | None = None, basis: object = None,
                      *, allow_unknown: bool = False) -> None:
        self._readiness_action = action
        dismissed = allow_unknown and self._dismissed_readiness_basis == basis
        self.readiness_label.setText("모르는 정보는 입력하지 않아도 됩니다." if dismissed else text)
        self.readiness_input_button.setText(f"{action_label} 입력" if action_label else "현재 정보 입력")
        self.readiness_input_button.setVisible(action is not None and not dismissed)
        self.readiness_skip_button.setVisible(allow_unknown and not dismissed)
        self._readiness_basis = basis

    def _dismiss_readiness(self) -> None:
        self._dismissed_readiness_basis = getattr(self, "_readiness_basis", None)
        self.readiness_label.setText("모르는 정보는 입력하지 않아도 됩니다.")
        self.readiness_input_button.hide()
        self.readiness_skip_button.hide()

    def _request_readiness_input(self) -> None:
        if self._readiness_action is not None:
            self.readiness_input_requested.emit(self._readiness_action)
