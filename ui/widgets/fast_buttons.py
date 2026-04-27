from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class FastButtonGroup(QWidget):
    def __init__(self, on_hp_changed: Callable[[int], None]) -> None:
        super().__init__()
        self._on_hp_changed = on_hp_changed
        self._buttons: dict[int, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        for value, label in ((100, "100%"), (75, "75%"), (50, "50%"), (25, "25%"), (0, "KO")):
            button = QPushButton(label)
            button.setFixedHeight(22)
            button.setStyleSheet(self._button_style(active=False))
            button.clicked.connect(lambda checked=False, hp=value: self.set_hp(hp))
            layout.addWidget(button)
            self._buttons[value] = button

        self.set_hp(100)

    def set_hp(self, hp: int) -> None:
        self._on_hp_changed(hp)
        for value, button in self._buttons.items():
            button.setStyleSheet(self._button_style(active=value == hp))
        print(f"빠른 HP 버튼 선택: {hp}%")

    @staticmethod
    def _button_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #4A90E2;
                    color: white;
                    border: 1px solid #4A90E2;
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 1px 4px;
                }
                QPushButton:hover {
                    background-color: #6BA8E8;
                }
            """

        return """
            QPushButton {
                background-color: #F4F7FA;
                color: #243447;
                border: 1px solid #CAD6E2;
                border-radius: 4px;
                font-size: 11px;
                padding: 1px 4px;
            }
            QPushButton:hover {
                background-color: #D9EBFF;
                border-color: #6BA8E8;
            }
        """
