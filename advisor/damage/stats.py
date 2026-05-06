from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from advisor.damage.item_modifiers import (
    attack_stat_item_mod,
    defense_stat_item_mod,
    speed_stat_item_mod,
)
from advisor.damage.abilities import AbilityEffect
from advisor.damage.items import ItemEffect
from advisor.damage.q12 import M_DOUBLE, M_STAB, apply_damage_modifier


StatName = Literal["hp", "atk", "def", "spa", "spd", "spe"]
RuleSet = Literal["gen9", "champions"]

NATURE_PLUS_MINUS: dict[str, tuple[StatName | None, StatName | None]] = {
    "hardy": (None, None),
    "lonely": ("atk", "def"),
    "brave": ("atk", "spe"),
    "adamant": ("atk", "spa"),
    "naughty": ("atk", "spd"),
    "bold": ("def", "atk"),
    "docile": (None, None),
    "relaxed": ("def", "spe"),
    "impish": ("def", "spa"),
    "lax": ("def", "spd"),
    "timid": ("spe", "atk"),
    "hasty": ("spe", "def"),
    "serious": (None, None),
    "jolly": ("spe", "spa"),
    "naive": ("spe", "spd"),
    "modest": ("spa", "atk"),
    "mild": ("spa", "def"),
    "quiet": ("spa", "spe"),
    "bashful": (None, None),
    "rash": ("spa", "spd"),
    "calm": ("spd", "atk"),
    "gentle": ("spd", "def"),
    "sassy": ("spd", "spe"),
    "careful": ("spd", "spa"),
    "quirky": (None, None),
}


@dataclass(frozen=True, slots=True)
class StatBlock:
    hp: int
    atk: int
    def_: int
    spa: int
    spd: int
    spe: int

    def get(self, stat: StatName) -> int:
        return self.def_ if stat == "def" else getattr(self, stat)


@dataclass(frozen=True, slots=True)
class StatInputs:
    base: StatBlock
    evs: StatBlock
    ivs: StatBlock
    nature_plus: StatName | None
    nature_minus: StatName | None
    level: int
    rule_set: RuleSet
    species: str = ""
    is_nfe: bool = False
    locked_paradox_stat: StatName | None = None


def nature_from_name(name: str) -> tuple[StatName | None, StatName | None]:
    return NATURE_PLUS_MINUS[name.lower()]


def nature_modifier(
    stat: StatName,
    nature_plus: StatName | None,
    nature_minus: StatName | None,
) -> float:
    if stat == nature_plus:
        return 1.1
    if stat == nature_minus:
        return 0.9
    return 1.0


def calc_stat_gen9(
    base: int,
    ev: int,
    iv: int,
    level: int,
    nature_mod: float,
    is_hp: bool,
) -> int:
    if is_hp:
        return ((2 * base + iv + ev // 4) * level) // 100 + level + 10
    raw = ((2 * base + iv + ev // 4) * level) // 100 + 5
    if nature_mod == 1.1:
        return (raw * 11) // 10
    if nature_mod == 0.9:
        return (raw * 9) // 10
    return raw


def calc_stat_champions(
    base: int,
    ev: int,
    level: int,
    nature_mod: float,
    is_hp: bool,
) -> int:
    if ev > 32:
        raise ValueError("Champions EVs must be <= 32 per stat")
    return calc_stat_gen9(base, ev, 31, level, nature_mod, is_hp)


def apply_boosts(stat: int, stage: int) -> int:
    if not -6 <= stage <= 6:
        raise ValueError("stat boost stage must be between -6 and +6")
    if stage == 0:
        return stat
    if stage > 0:
        return stat * (2 + stage) // 2
    return stat * 2 // (2 + abs(stage))


def final_stats(
    inputs: StatInputs,
    item: ItemEffect | None = None,
    is_transformed: bool = False,
    ability: AbilityEffect | None = None,
    weather: str = "none",
    weather_suppressed: bool = False,
    terrain: str = "none",
    booster_active: bool = False,
) -> StatBlock:
    kwargs: dict[str, int] = {}
    for stat in ("hp", "atk", "def", "spa", "spd", "spe"):
        stat_name = stat  # type: ignore[assignment]
        mod = nature_modifier(stat_name, inputs.nature_plus, inputs.nature_minus)
        is_hp = stat == "hp"
        if inputs.rule_set == "champions":
            value = calc_stat_champions(
                inputs.base.get(stat_name),
                inputs.evs.get(stat_name),
                inputs.level,
                mod,
                is_hp,
            )
        else:
            value = calc_stat_gen9(
                inputs.base.get(stat_name),
                inputs.evs.get(stat_name),
                inputs.ivs.get(stat_name),
                inputs.level,
                mod,
                is_hp,
            )
        kwargs["def_" if stat == "def" else stat] = value
    stats = StatBlock(**kwargs)
    species = inputs.species
    if item is not None:
        stats = StatBlock(
            hp=stats.hp,
            atk=apply_damage_modifier(
                stats.atk,
                attack_stat_item_mod(item, True, species, is_transformed),
            ),
            def_=apply_damage_modifier(
                stats.def_,
                defense_stat_item_mod(
                    item,
                    True,
                    species,
                    inputs.is_nfe,
                    is_transformed,
                ),
            ),
            spa=apply_damage_modifier(
                stats.spa,
                attack_stat_item_mod(item, False, species, is_transformed),
            ),
            spd=apply_damage_modifier(
                stats.spd,
                defense_stat_item_mod(
                    item,
                    False,
                    species,
                    inputs.is_nfe,
                    is_transformed,
                ),
            ),
            spe=apply_damage_modifier(
                stats.spe,
                speed_stat_item_mod(item, species, is_transformed),
            ),
        )

    if ability is None or not ability.implemented:
        return stats

    return _apply_ability_stats(
        stats,
        ability,
        weather,
        weather_suppressed,
        terrain,
        booster_active,
        inputs.locked_paradox_stat,
    )


def _apply_ability_stats(
    stats: StatBlock,
    ability: AbilityEffect,
    weather: str,
    weather_suppressed: bool,
    terrain: str,
    booster_active: bool,
    locked_paradox_stat: StatName | None,
) -> StatBlock:
    ability_id = ability.ability_id
    atk = stats.atk
    def_ = stats.def_
    spa = stats.spa
    spd = stats.spd
    spe = stats.spe

    if not weather_suppressed:
        if ability_id == "chlorophyll" and weather in ("sun", "harsh-sunlight"):
            spe = apply_damage_modifier(spe, M_DOUBLE)
        elif ability_id == "swift-swim" and weather in ("rain", "heavy-rain"):
            spe = apply_damage_modifier(spe, M_DOUBLE)
        elif ability_id == "sand-rush" and weather == "sand":
            spe = apply_damage_modifier(spe, M_DOUBLE)
        elif ability_id == "slush-rush" and weather in ("snow", "hail"):
            spe = apply_damage_modifier(spe, M_DOUBLE)
        elif ability_id == "solar-power" and weather in ("sun", "harsh-sunlight"):
            spa = apply_damage_modifier(spa, M_STAB)
        elif ability_id == "flower-gift" and weather in ("sun", "harsh-sunlight"):
            atk = apply_damage_modifier(atk, M_STAB)
            spd = apply_damage_modifier(spd, M_STAB)

    if ability_id == "surge-surfer" and terrain == "electric":
        spe = apply_damage_modifier(spe, M_DOUBLE)
    if ability_id == "grass-pelt" and terrain == "grassy":
        def_ = apply_damage_modifier(def_, M_STAB)

    if _paradox_active(ability_id, weather, weather_suppressed, terrain, booster_active):
        boosted = locked_paradox_stat or _highest_stat(stats)
        if boosted == "atk":
            atk = apply_damage_modifier(atk, 5324)
        elif boosted == "def":
            def_ = apply_damage_modifier(def_, 5324)
        elif boosted == "spa":
            spa = apply_damage_modifier(spa, 5324)
        elif boosted == "spd":
            spd = apply_damage_modifier(spd, 5324)
        elif boosted == "spe":
            spe = apply_damage_modifier(spe, M_STAB)

    return StatBlock(
        hp=stats.hp,
        atk=atk,
        def_=def_,
        spa=spa,
        spd=spd,
        spe=spe,
    )


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


def _highest_stat(stats: StatBlock) -> StatName:
    candidates: list[tuple[StatName, int]] = [
        ("atk", stats.atk),
        ("def", stats.def_),
        ("spa", stats.spa),
        ("spd", stats.spd),
        ("spe", stats.spe),
    ]
    return max(candidates, key=lambda item: item[1])[0]
