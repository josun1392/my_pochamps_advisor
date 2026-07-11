from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QPushButton, QTextEdit, QVBoxLayout


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
    field_profile_requested = Signal()
    item_event_requested = Signal()
    item_event_session_reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("llmAdvicePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.request_button = QPushButton("이번 턴 추천 받기")
        self.request_button.clicked.connect(self.advice_requested.emit)

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
        layout.addWidget(self.field_profile_button)
        layout.addWidget(self.item_event_button)
        layout.addWidget(self.clear_item_events_button)
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

    def set_running(self, is_running: bool) -> None:
        self.request_button.setDisabled(is_running)
        self.field_profile_button.setDisabled(is_running)
        self.item_event_button.setDisabled(is_running)
        self.clear_item_events_button.setDisabled(is_running)
        self.turn_pipeline_checkbox.setDisabled(is_running)
        if is_running:
            self.output_edit.setPlainText("분석 중...")
            self.cost_label.setText("비용: 분석 중...")

    def set_advice_text(self, text: str) -> None:
        self.output_edit.setPlainText(text)

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
