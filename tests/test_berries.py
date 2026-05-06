from __future__ import annotations

from advisor.damage.item_modifiers import defender_berry_mod
from advisor.damage.items import get_item
from advisor.damage.q12 import Q12_ONE, M_HALF


def test_occa_berry_halves_super_effective_fire() -> None:
    assert defender_berry_mod(get_item("occa-berry"), "fire", True) == M_HALF


def test_occa_berry_does_not_halve_neutral_fire() -> None:
    assert defender_berry_mod(get_item("occa-berry"), "fire", False) == Q12_ONE


def test_occa_berry_does_not_halve_wrong_type() -> None:
    assert defender_berry_mod(get_item("occa-berry"), "water", True) == Q12_ONE


def test_chilan_berry_halves_any_normal_hit() -> None:
    assert defender_berry_mod(get_item("chilan-berry"), "normal", False) == M_HALF


def test_yache_berry_halves_four_x_ice_weakness() -> None:
    assert defender_berry_mod(get_item("yache-berry"), "ice", True) == M_HALF
