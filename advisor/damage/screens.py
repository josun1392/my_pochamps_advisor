from __future__ import annotations

from advisor.damage.field import SideField
from advisor.damage.q12 import M_SCREEN_DOUBLES, M_SCREEN_SINGLES, Q12_ONE


def screen_modifier(
    defender_side: SideField,
    is_physical: bool,
    is_critical: bool,
    is_doubles: bool,
    breaks_screens: bool = False,
    bypass_screens: bool = False,
) -> int:
    del breaks_screens
    if is_critical or bypass_screens:
        return Q12_ONE
    has_screen = defender_side.aurora_veil or (
        defender_side.reflect if is_physical else defender_side.light_screen
    )
    if not has_screen:
        return Q12_ONE
    return M_SCREEN_DOUBLES if is_doubles else M_SCREEN_SINGLES
