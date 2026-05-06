from __future__ import annotations

from advisor.damage.abilities import AbilityEffect
from advisor.damage.q12 import (
    M_DOUBLE,
    M_HALF,
    M_NEUTRAL,
    M_STAB,
    Q12_ONE,
    apply_damage_modifier,
    chain_modifiers,
)
from advisor.damage.stats import StatBlock, StatName, apply_boosts


M_PARADOX = 5324
M_HADRON_ORICHALCUM = 5461


def attacker_base_power_ability_mod(
    ability: AbilityEffect | None,
    move_type: str,
    weather: str,
    weather_suppressed: bool,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    if ability.ability_id == "sand-force":
        if weather == "sand" and not weather_suppressed:
            if move_type in ability.boosted_types:
                return ability.multiplier_q12
    return Q12_ONE


def defender_base_power_ability_mod(
    ability: AbilityEffect | None,
    move_type: str,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    if ability.ability_id == "dry-skin" and move_type == "fire":
        return 5120
    return Q12_ONE


def attack_stat_ability_mod(
    ability: AbilityEffect | None,
    is_physical: bool,
    weather: str,
    weather_suppressed: bool,
    terrain: str,
    stats: StatBlock | None = None,
    boosts: StatBlock | None = None,
    locked_paradox_stat: StatName | None = None,
    booster_active: bool = False,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    ability_id = ability.ability_id
    if ability_id == "solar-power" and not is_physical:
        if weather in ("sun", "harsh-sunlight") and not weather_suppressed:
            return M_STAB
    if ability_id == "flower-gift" and is_physical:
        if weather in ("sun", "harsh-sunlight") and not weather_suppressed:
            return M_STAB
    if _paradox_active(ability_id, weather, weather_suppressed, terrain, booster_active):
        boosted = locked_paradox_stat or _highest_paradox_stat(stats, boosts)
        if (is_physical and boosted == "atk") or (not is_physical and boosted == "spa"):
            return M_PARADOX
    return Q12_ONE


def attacker_move_attack_stat_ability_mod(
    ability: AbilityEffect | None,
    move_type: str,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    if ability.ability_id == "water-bubble" and move_type == "water":
        return M_DOUBLE
    return Q12_ONE


def defender_attack_stat_ability_mod(
    ability: AbilityEffect | None,
    move_type: str,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    ability_id = ability.ability_id
    if ability_id == "heatproof" and move_type == "fire":
        return M_HALF
    if ability_id == "thick-fat" and move_type in ("fire", "ice"):
        return M_HALF
    if ability_id == "water-bubble" and move_type == "fire":
        return M_HALF
    if ability_id == "purifying-salt" and move_type == "ghost":
        return M_HALF
    return Q12_ONE


def defense_stat_ability_mod(
    ability: AbilityEffect | None,
    is_physical: bool,
    weather: str,
    weather_suppressed: bool,
    terrain: str,
    stats: StatBlock | None = None,
    boosts: StatBlock | None = None,
    locked_paradox_stat: StatName | None = None,
    booster_active: bool = False,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    ability_id = ability.ability_id
    if ability_id == "flower-gift" and not is_physical:
        if weather in ("sun", "harsh-sunlight") and not weather_suppressed:
            return M_STAB
    if ability_id == "grass-pelt" and terrain == "grassy" and is_physical:
        return M_STAB
    if _paradox_active(ability_id, weather, weather_suppressed, terrain, booster_active):
        boosted = locked_paradox_stat or _highest_paradox_stat(stats, boosts)
        if (is_physical and boosted == "def") or (not is_physical and boosted == "spd"):
            return M_PARADOX
    return Q12_ONE


def speed_stat_ability_mod(
    ability: AbilityEffect | None,
    weather: str,
    weather_suppressed: bool,
    terrain: str,
    stats: StatBlock | None = None,
    boosts: StatBlock | None = None,
    locked_paradox_stat: StatName | None = None,
    booster_active: bool = False,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    ability_id = ability.ability_id
    if not weather_suppressed:
        if ability_id == "chlorophyll" and weather in ("sun", "harsh-sunlight"):
            return M_DOUBLE
        if ability_id == "swift-swim" and weather in ("rain", "heavy-rain"):
            return M_DOUBLE
        if ability_id == "sand-rush" and weather == "sand":
            return M_DOUBLE
        if ability_id == "slush-rush" and weather in ("snow", "hail"):
            return M_DOUBLE
    if ability_id == "surge-surfer" and terrain == "electric":
        return M_DOUBLE
    if _paradox_active(ability_id, weather, weather_suppressed, terrain, booster_active):
        boosted = locked_paradox_stat or _highest_paradox_stat(stats, boosts)
        if boosted == "spe":
            return M_STAB
    return Q12_ONE


def _paradox_active(
    ability_id: str,
    weather: str,
    weather_suppressed: bool,
    terrain: str,
    booster_active: bool,
) -> bool:
    if booster_active:
        return ability_id in {"quark-drive", "protosynthesis"}
    if ability_id == "quark-drive":
        return terrain == "electric"
    if ability_id == "protosynthesis":
        return weather in ("sun", "harsh-sunlight") and not weather_suppressed
    return False


def _highest_paradox_stat(
    stats: StatBlock | None,
    boosts: StatBlock | None = None,
) -> StatName | None:
    if stats is None:
        return None
    candidates: list[tuple[StatName, int]] = [
        ("atk", _boosted(stats.atk, boosts.atk if boosts else 0)),
        ("def", _boosted(stats.def_, boosts.def_ if boosts else 0)),
        ("spa", _boosted(stats.spa, boosts.spa if boosts else 0)),
        ("spd", _boosted(stats.spd, boosts.spd if boosts else 0)),
        ("spe", _boosted(stats.spe, boosts.spe if boosts else 0)),
    ]
    return max(candidates, key=lambda item: item[1])[0]


def _boosted(stat: int, stage: int) -> int:
    return apply_boosts(stat, stage)


def apply_speed_ability(
    speed: int,
    ability: AbilityEffect | None,
    weather: str,
    weather_suppressed: bool,
    terrain: str,
    stats: StatBlock | None = None,
    boosts: StatBlock | None = None,
    locked_paradox_stat: StatName | None = None,
    booster_active: bool = False,
) -> int:
    return apply_damage_modifier(
        speed,
        speed_stat_ability_mod(
            ability,
            weather,
            weather_suppressed,
            terrain,
            stats,
            boosts,
            locked_paradox_stat,
            booster_active,
        ),
    )


def defender_damage_ability_mod(
    ability: AbilityEffect | None,
    move_type: str,
    is_super_effective: bool,
    is_contact: bool,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE

    ability_id = ability.ability_id
    if ability_id == "fluffy":
        mods: list[int] = []
        if is_contact:
            mods.append(M_HALF)
        if move_type == "fire":
            mods.append(M_DOUBLE)
        return chain_modifiers(mods)

    if ability_id in {"solid-rock", "filter", "prism-armor"} and is_super_effective:
        return 3072

    return Q12_ONE


def attacker_damage_ability_mod_immunity_phase(
    ability: AbilityEffect | None,
    is_not_very_effective: bool,
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE
    if ability.ability_id == "tinted-lens" and is_not_very_effective:
        return M_DOUBLE
    return M_NEUTRAL
