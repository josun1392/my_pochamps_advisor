from __future__ import annotations

from advisor.damage.recoil import (
    HitResult,
    RecoilMove,
    RecoilPokemon,
    compute_life_orb_recoil,
)


def test_life_orb_damaging_move_recoil_floor_tenth_max_hp() -> None:
    attacker = RecoilPokemon(max_hp=299, item="life-orb")
    move = RecoilMove(move_id="thunderbolt", category="special")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=1)) == 29


def test_life_orb_status_move_has_no_recoil() -> None:
    attacker = RecoilPokemon(max_hp=299, item="life-orb")
    move = RecoilMove(move_id="thunder-wave", category="status")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=1)) == 0


def test_life_orb_magic_guard_has_no_recoil() -> None:
    attacker = RecoilPokemon(max_hp=299, item="life-orb", ability="magic-guard")
    move = RecoilMove(move_id="thunderbolt", category="special")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=1)) == 0


def test_life_orb_sheer_force_suppressible_move_has_no_recoil() -> None:
    attacker = RecoilPokemon(max_hp=299, item="life-orb", ability="sheer-force")
    move = RecoilMove(move_id="iron-head", category="physical")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=1)) == 0


def test_life_orb_sheer_force_non_secondary_move_still_has_recoil() -> None:
    attacker = RecoilPokemon(max_hp=299, item="life-orb", ability="sheer-force")
    move = RecoilMove(move_id="earthquake", category="physical")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=1)) == 29


def test_life_orb_damaging_miss_has_no_recoil() -> None:
    attacker = RecoilPokemon(max_hp=299, item="life-orb")
    move = RecoilMove(move_id="thunderbolt", category="special")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=0)) == 0


def test_life_orb_recoil_minimum_one_for_positive_max_hp() -> None:
    attacker = RecoilPokemon(max_hp=1, item="life-orb")
    move = RecoilMove(move_id="thunderbolt", category="special")
    assert compute_life_orb_recoil(attacker, move, HitResult(targets_hit=1)) == 1
