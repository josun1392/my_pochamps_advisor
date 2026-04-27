from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.fast_buttons import FastButtonGroup


class PokemonPanel(QFrame):
    def __init__(self, slot_number: int, is_active: bool = False) -> None:
        super().__init__()
        self.slot_number = slot_number
        self.is_selected = False
        self._current_hp = 100
        self.selected_move_index: int | None = None
        self.move_buttons: list[QPushButton] = []

        self.setFixedHeight(108)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 4, 8, 4)
        root_layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        name_label = QLabel(f"포켓몬 #{slot_number}")
        name_label.setStyleSheet("font-weight: 700; color: #17202A;")

        active_indicator = QLabel("●" if is_active else "○")
        active_indicator.setStyleSheet(
            "color: #2ECC71; font-size: 13px;" if is_active else "color: #B0B8C1; font-size: 13px;"
        )
        active_indicator.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top_row.addWidget(name_label)
        top_row.addStretch()
        top_row.addWidget(active_indicator)
        root_layout.addLayout(top_row)

        middle_row = QHBoxLayout()
        middle_row.setSpacing(6)

        self.hp_bar = QProgressBar()
        self.hp_bar.setRange(0, 100)
        self.hp_bar.setValue(100)
        self.hp_bar.setTextVisible(True)
        self.hp_bar.setFixedHeight(18)
        self.hp_bar.setFormat("%p%")
        self._apply_normal_style()

        self.hp_spinbox = QSpinBox()
        self.hp_spinbox.setRange(0, 100)
        self.hp_spinbox.setValue(100)
        self.hp_spinbox.setSuffix(" %")
        self.hp_spinbox.setFixedWidth(70)
        self.hp_spinbox.setFixedHeight(20)
        self.hp_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.hp_spinbox.setKeyboardTracking(False)
        self.hp_spinbox.valueChanged.connect(self.set_hp)

        middle_row.addWidget(QLabel("HP"))
        middle_row.addWidget(self.hp_bar, 2)
        middle_row.addWidget(self.hp_spinbox)
        root_layout.addLayout(middle_row)

        self.fast_buttons = FastButtonGroup(self.set_hp)
        self.fast_buttons.setFixedHeight(22)
        root_layout.addWidget(self.fast_buttons)

        move_row = QGridLayout()
        move_row.setContentsMargins(0, 0, 0, 0)
        move_row.setHorizontalSpacing(4)
        move_row.setVerticalSpacing(2)

        for index, key in enumerate(("Q", "W", "E", "R")):
            move_button = QPushButton(f"{key} 기술 {index + 1}")
            move_button.setFixedHeight(18)
            move_button.setStyleSheet(self._move_style(active=False))
            move_button.clicked.connect(lambda checked=False, idx=index: self.select_move(idx))
            self.move_buttons.append(move_button)
            move_row.addWidget(move_button, index // 2, index % 2)

        root_layout.addLayout(move_row)
        self.set_selected(False)

    def set_hp(self, value: int) -> None:
        value = max(0, min(100, value))
        self.hp_bar.blockSignals(True)
        self.hp_spinbox.blockSignals(True)

        self.hp_bar.setValue(value)
        self.hp_spinbox.setValue(value)
        self._current_hp = value

        self.hp_bar.blockSignals(False)
        self.hp_spinbox.blockSignals(False)

        self._sync_fast_button_styles(value)
        if value == 0:
            self._apply_ko_style()
        else:
            self._apply_normal_style()
        print(f"HP 직접/동기화 입력: 포켓몬 {self.slot_number}번 / {value}%")

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        border = "2px solid #4A90E2" if selected else "1px solid #D8E0EA"
        self.setStyleSheet(
            f"""
            PokemonPanel {{
                background-color: white;
                border: {border};
                border-radius: 8px;
            }}
            """
        )

    def select_move(self, move_index: int) -> None:
        self.selected_move_index = move_index
        for index, button in enumerate(self.move_buttons):
            button.setStyleSheet(self._move_style(active=index == move_index))
        print(f"기술 선택: 포켓몬 {self.slot_number}번 / {move_index + 1}번 기술")

    @staticmethod
    def _move_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #4A90E2;
                    color: white;
                    border: 1px solid #4A90E2;
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 2px 4px;
                }
                QPushButton:hover {
                    background-color: #6BA8E8;
                }
            """

        return """
            QPushButton {
                background-color: #FFFFFF;
                color: #243447;
                border: 1px solid #CAD6E2;
                border-radius: 4px;
                font-size: 11px;
                padding: 2px 4px;
            }
            QPushButton:hover {
                background-color: #EEF6FF;
                border-color: #6BA8E8;
            }
        """

    def _sync_fast_button_styles(self, value: int) -> None:
        fast_buttons = getattr(self, "fast_buttons", None)
        if fast_buttons is None:
            return

        for hp_value, button in fast_buttons._buttons.items():
            button.setStyleSheet(fast_buttons._button_style(active=hp_value == value))

    def _apply_normal_style(self) -> None:
        self.hp_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #CAD6E2;
                border-radius: 4px;
                background-color: #F7F9FC;
                color: #17202A;
                text-align: center;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #50B36B;
                border-radius: 3px;
            }
            """
        )

    def _apply_ko_style(self) -> None:
        self.hp_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #D64545;
                border-radius: 4px;
                background-color: #FFF1F1;
                color: #17202A;
                text-align: center;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #D64545;
                border-radius: 3px;
            }
            """
        )


class PokemonTeamColumn(QWidget):
    def __init__(self, title: str, selectable: bool) -> None:
        super().__init__()
        self.panels: list[PokemonPanel] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #17202A;")
        layout.addWidget(title_label)

        for slot in range(1, 7):
            panel = PokemonPanel(slot, is_active=slot == 1)
            if selectable and slot == 1:
                panel.set_selected(True)
            self.panels.append(panel)
            layout.addWidget(panel)

        layout.addStretch(1)
