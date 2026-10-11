"""Explicit human capture of a visible battle decision boundary."""
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout


class BattleDecisionPhaseDialog(QDialog):
    def __init__(self, *, turn_number=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Battle Decision Phase")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("현재 게임에서 확인한 행동 단계와 턴을 기록하세요."))
        form = QFormLayout()
        self.phase_combo = QComboBox()
        for label, value in (("확인한 단계 선택", None), ("기술 선택", "move_selection"),
                ("기절 후 교체", "faint_replacement"), ("기술 사용 중 교체", "pivot_replacement")):
            self.phase_combo.addItem(label, value)
        self.side_combo = QComboBox()
        for label, value in (("교체할 쪽 선택", None), ("내 쪽", ["self"]), ("상대 쪽", ["opponent"]), ("양쪽", ["self", "opponent"])):
            self.side_combo.addItem(label, value)
        self.turn_spin = QSpinBox()
        self.turn_spin.setRange(0, 999)
        self.turn_spin.setSpecialValueText("현재 턴 확인")
        self.turn_spin.setValue(turn_number if type(turn_number) is int and 1 <= turn_number <= 999 else 0)
        form.addRow("현재 턴", self.turn_spin)
        form.addRow("행동 단계", self.phase_combo)
        form.addRow("교체 요청", self.side_combo)
        layout.addLayout(form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.phase_combo.currentIndexChanged.connect(self._update)
        self.side_combo.currentIndexChanged.connect(self._update)
        self.turn_spin.valueChanged.connect(self._update)
        self._update()

    def _update(self):
        move = self.phase_combo.currentData() == "move_selection"
        self.side_combo.setEnabled(not move)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.confirmation is not None)

    @property
    def confirmation(self):
        phase = self.phase_combo.currentData()
        sides = ["self", "opponent"] if phase == "move_selection" else self.side_combo.currentData()
        if phase is None or sides is None or self.turn_spin.value() < 1: return None
        return {"phase": phase, "requesting_sides": list(sides), "turn_number": self.turn_spin.value()}
