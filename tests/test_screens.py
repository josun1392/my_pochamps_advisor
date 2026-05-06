from __future__ import annotations

from advisor.damage.field import SideField
from advisor.damage.q12 import M_SCREEN_DOUBLES, M_SCREEN_SINGLES, Q12_ONE
from advisor.damage.screens import screen_modifier


def test_no_screen_is_neutral() -> None:
    assert screen_modifier(SideField(), True, False, False) == Q12_ONE


def test_reflect_physical_singles() -> None:
    assert screen_modifier(SideField(reflect=True), True, False, False) == M_SCREEN_SINGLES


def test_reflect_physical_doubles() -> None:
    assert screen_modifier(SideField(reflect=True), True, False, True) == M_SCREEN_DOUBLES


def test_reflect_special_is_neutral() -> None:
    assert screen_modifier(SideField(reflect=True), False, False, True) == Q12_ONE


def test_light_screen_special_doubles() -> None:
    assert screen_modifier(SideField(light_screen=True), False, False, True) == M_SCREEN_DOUBLES


def test_aurora_veil_applies_to_physical_and_special() -> None:
    side = SideField(aurora_veil=True)

    assert screen_modifier(side, True, False, False) == M_SCREEN_SINGLES
    assert screen_modifier(side, False, False, False) == M_SCREEN_SINGLES


def test_critical_ignores_screens() -> None:
    assert screen_modifier(SideField(aurora_veil=True), True, True, True) == Q12_ONE


def test_aurora_veil_does_not_stack_with_reflect() -> None:
    side = SideField(reflect=True, aurora_veil=True)

    assert screen_modifier(side, True, False, True) == M_SCREEN_DOUBLES
