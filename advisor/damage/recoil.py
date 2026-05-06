from __future__ import annotations

from dataclasses import dataclass

from advisor.damage.move_categories import is_secondary_suppressed_by


@dataclass(frozen=True, slots=True)
class RecoilPokemon:
    max_hp: int
    item: str | None = None
    ability: str | None = None


@dataclass(frozen=True, slots=True)
class RecoilMove:
    move_id: str
    category: str


@dataclass(frozen=True, slots=True)
class HitResult:
    targets_hit: int = 0


def compute_life_orb_recoil(
    attacker: RecoilPokemon,
    move: RecoilMove,
    hit_result: HitResult,
) -> int:
    """Return Life Orb HP loss after a successful damaging move, or 0."""
    if attacker.item != "life-orb":
        return 0
    if attacker.max_hp <= 0:
        return 0
    if move.category == "status":
        return 0
    if hit_result.targets_hit <= 0:
        return 0
    if attacker.ability == "magic-guard":
        return 0
    if is_secondary_suppressed_by(move.move_id, attacker_ability=attacker.ability):
        return 0
    return max(1, attacker.max_hp // 10)
