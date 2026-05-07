from __future__ import annotations

from advisor.damage.crit import (
    CritState,
    MoveCritState,
    crit_probability,
    resolve_crit_roll,
    resolve_crit_stage,
)


def test_default_stage_is_zero() -> None:
    assert resolve_crit_stage(CritState(), MoveCritState(move_id="tackle")) == 0


def test_high_crit_ratio_move_adds_one() -> None:
    assert resolve_crit_stage(CritState(), MoveCritState(move_id="slash")) == 1


def test_super_luck_adds_one() -> None:
    assert resolve_crit_stage(CritState(ability="super-luck"), MoveCritState()) == 1


def test_scope_lens_adds_one() -> None:
    assert resolve_crit_stage(CritState(item="scope-lens"), MoveCritState()) == 1


def test_focus_energy_adds_two() -> None:
    assert resolve_crit_stage(CritState(volatiles=("focus-energy",)), MoveCritState()) == 2


def test_stacking_super_luck_plus_scope_lens_plus_focus_energy() -> None:
    stage = resolve_crit_stage(
        CritState(ability="super-luck", item="scope-lens", volatiles=("focus-energy",)),
        MoveCritState(),
    )

    assert stage == 4
    assert crit_probability(stage).numerator == 1
    assert crit_probability(stage).denominator == 1


def test_always_crit_move_overrides_to_guaranteed() -> None:
    assert resolve_crit_stage(CritState(), MoveCritState(move_id="frost-breath")) >= 3
    assert resolve_crit_stage(CritState(), MoveCritState(move_id="storm-throw")) >= 3
    assert resolve_crit_stage(CritState(), MoveCritState(move_id="surging-strikes")) >= 3


def test_merciless_against_poisoned_target_guarantees_crit() -> None:
    stage = resolve_crit_stage(
        CritState(ability="merciless"),
        MoveCritState(),
        CritState(status="poison"),
    )

    assert stage >= 3


def test_battle_armor_blocks_crit() -> None:
    assert resolve_crit_roll(4, "max", defender_state=CritState(ability="battle-armor")) is False


def test_shell_armor_blocks_crit() -> None:
    assert resolve_crit_roll(4, "max", defender_state=CritState(ability="shell-armor")) is False


def test_lucky_chant_blocks_crit() -> None:
    assert resolve_crit_roll(4, "max", field_state={"lucky_chant": True}) is False


def test_dragon_cheer_adds_two_for_dragon_type() -> None:
    assert resolve_crit_stage(CritState(types=("dragon",), volatiles=("dragon-cheer",)), MoveCritState()) == 2


def test_species_crit_items_require_species() -> None:
    assert resolve_crit_stage(CritState(item="stick", species="farfetchd"), MoveCritState()) == 2
    assert resolve_crit_stage(CritState(item="stick", species="pikachu"), MoveCritState()) == 0
    assert resolve_crit_stage(CritState(item="lucky-punch", species="chansey"), MoveCritState()) == 2
