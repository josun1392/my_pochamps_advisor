from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QTextEdit, QVBoxLayout


class AnalysisPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("analysisPanel")
        self.is_active = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_edit.setFont(font)
        self.output_edit.setPlainText("아직 전략 분석 결과가 없습니다.")
        self.output_edit.setStyleSheet(
            """
            QTextEdit {
                color: #17202A;
                background-color: #F8FAFC;
                border: 1px solid #D8E0EA;
                border-radius: 8px;
                padding: 8px;
            }
            """
        )

        layout.addWidget(self.output_edit, 1)

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self.setProperty("active", active)
        self.setStyleSheet(self._build_stylesheet())

    @staticmethod
    def _build_stylesheet() -> str:
        return """
            QFrame#analysisPanel {
                background-color: transparent;
                border: none;
            }
        """
