from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class AnalysisPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_edit.setFont(font)
        self.output_edit.setPlainText(
            """━━━ 추천 옵션 ━━━

[A] 지진 (확정 데미지)  ★ 추천
  + 65~78% 데미지 (확정 2타)
  + 상대 기절 압박
  - 비행 타입 등장 시 무효

[B] U턴 (모멘텀 확보)
  + 상대 변경 강제
  + 다음 턴 유리한 매치업
  - 즉시 데미지 부족 (12~15%)

[C] 보호 (정보 수집)
  + 상대 의도 파악
  - 1턴 손실

━━━ 상대 행동 예측 ━━━
보호      65%
교체      25%
공격      10%

━━━ 위험 신호 ━━━
! 상대 트릭룸 셋업 가능성 높음
! 다음 턴 스카프 랜드로스 교체 주의"""
        )
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
