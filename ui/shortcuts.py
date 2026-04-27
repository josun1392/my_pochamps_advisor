from __future__ import annotations

from typing import Protocol

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QSpinBox, QWidget


class ShortcutTarget(Protocol):
    def select_my_pokemon(self, slot_index: int) -> None:
        ...

    def select_current_move(self, move_index: int) -> None:
        ...

    def focus_next_column(self) -> None:
        ...


class GlobalShortcuts:
    def __init__(self, parent: QWidget, target: ShortcutTarget) -> None:
        self._shortcuts: list[QShortcut] = []

        for slot in range(1, 7):
            shortcut = QShortcut(QKeySequence(str(slot)), parent)
            shortcut.activated.connect(lambda idx=slot - 1: self._select_pokemon(target, idx))
            self._shortcuts.append(shortcut)

        for move_index, key in enumerate(("Q", "W", "E", "R")):
            shortcut = QShortcut(QKeySequence(key), parent)
            shortcut.activated.connect(lambda idx=move_index: self._select_move(target, idx))
            self._shortcuts.append(shortcut)

        tab_shortcut = QShortcut(QKeySequence("Tab"), parent)
        tab_shortcut.activated.connect(lambda: self._focus_next_column(target))
        self._shortcuts.append(tab_shortcut)

    def _select_pokemon(self, target: ShortcutTarget, slot_index: int) -> None:
        if self._should_ignore_shortcut():
            return
        print(f"단축키 입력: {slot_index + 1}번 포켓몬 선택")
        target.select_my_pokemon(slot_index)

    def _select_move(self, target: ShortcutTarget, move_index: int) -> None:
        if self._should_ignore_shortcut():
            return
        print(f"단축키 입력: {move_index + 1}번 기술 선택")
        target.select_current_move(move_index)

    def _focus_next_column(self, target: ShortcutTarget) -> None:
        if self._should_ignore_shortcut():
            return
        print("단축키 입력: 다음 열로 포커스 이동")
        target.focus_next_column()

    def _should_ignore_shortcut(self) -> bool:
        focused = QApplication.focusWidget()
        return isinstance(focused, (QSpinBox, QLineEdit))
