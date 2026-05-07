from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QTextEdit, QVBoxLayout


class LLMAdvicePanel(QFrame):
    advice_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("llmAdvicePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.request_button = QPushButton("이번 턴 추천 받기")
        self.request_button.clicked.connect(self.advice_requested.emit)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_edit.setFont(font)
        self.output_edit.setPlaceholderText("LLM 추천이 여기에 표시됩니다.")

        self.cost_label = QLabel("비용: 아직 호출 없음")
        self.cost_label.setObjectName("llmCostLabel")

        layout.addWidget(self.request_button)
        layout.addWidget(self.output_edit, 1)
        layout.addWidget(self.cost_label)
        self.setStyleSheet(self._build_stylesheet())

    def set_running(self, is_running: bool) -> None:
        self.request_button.setDisabled(is_running)
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
        """
