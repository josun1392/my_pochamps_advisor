from __future__ import annotations

from advisor.damage.abilities import AbilityEffect, get_ability
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


def _pinch_type_boost(
    ability: str,
    *,
    move_type: str,
    hp_current: int,
    hp_max: int,
) -> int:
    """
    Returns Q12 multiplier for pinch type-boosters. Default 4096.

    Pinch threshold: hp_current * 3 <= hp_max
    Defeatist threshold: hp_current * 2 <= hp_max
    """
    type_map = {
        "overgrow": "grass",
        "blaze": "fire",
        "torrent": "water",
        "swarm": "bug",
    }
    if hp_max <= 0:
        return Q12_ONE
    normalized_type = move_type.lower()
    if ability in type_map:
        if normalized_type == type_map[ability] and hp_current * 3 <= hp_max:
            return M_STAB
        return Q12_ONE

    if ability == "defeatist":
        if hp_current * 2 <= hp_max:
            return M_HALF
        return Q12_ONE

    return Q12_ONE


def get_atk_ability_modifier(
    ability_id: str,
    move_category: str,
    *,
    move_type: str = "",
    hp_current: int = 1,
    hp_max: int = 1,
) -> int:
    """
    Returns Q12 multiplier for at_mods layer based on ability.
    move_category: "physical" | "special" | "status"
    Returns 4096 if no modifier applies.
    """
    ability = get_ability(ability_id)
    if ability is None or not ability.implemented:
        return Q12_ONE
    if ability.category != "stat_multiplier":
        return Q12_ONE
    if (
        ability.raw_data.get("stat") == "atk"
        and ability.raw_data.get("condition") == "physical_move"
        and move_category == "physical"
    ):
        return ability.multiplier_q12
    if ability.raw_data.get("condition") == "type_electric" and move_type == "electric":
        return ability.multiplier_q12
    return _pinch_type_boost(
        ability_id,
        move_type=move_type,
        hp_current=hp_current,
        hp_max=hp_max,
    )


def get_def_ability_modifier(ability_id: str, move_category: str) -> int:
    """
    df_mods/sd_mods layer.
    - fur-coat: physical receive 2048
    - ice-scales: special receive 2048
    - otherwise: 4096
    """
    ability = get_ability(ability_id)
    if ability is None or not ability.implemented:
        return Q12_ONE
    if ability.category != "stat_multiplier":
        return Q12_ONE
    condition = ability.raw_data.get("condition")
    if condition == "physical_move_received" and move_category == "physical":
        return ability.multiplier_q12
    if condition == "special_move_received" and move_category == "special":
        return ability.multiplier_q12
    return Q12_ONE


def get_final_def_ability_modifier(
    ability: str,
    *,
    hp_ratio: float,
    type_effectiveness: float,
    move_flags: set[str],
) -> int:
    """
    Returns Q12 multiplier for defender-side final_mods layer. Default 4096.

    Existing:
      - Multiscale / Shadow Shield: 2048 if hp_ratio == 1.0 else 4096

    New:
      - Filter / Solid Rock / Prism Armor: 3072 if type_effectiveness > 1.0
      - Punk Rock: 2048 if "sound" in move_flags
    """
    effect = get_ability(ability)
    if effect is None or not effect.implemented:
        return Q12_ONE
    condition = effect.raw_data.get("condition")
    if effect.category == "damage_mod_hp" and condition == "defender_hp_full":
        if hp_ratio == 1.0:
            return effect.multiplier_q12
        return Q12_ONE
    if effect.raw_data.get("stat") != "final_def":
        return Q12_ONE
    if condition == "super_effective" and type_effectiveness > 1.0 + 1e-9:
        return effect.multiplier_q12
    if condition == "sound_move" and "sound" in move_flags:
        # TODO: PR #? implements Punk Rock's offensive sound boost in bp_mods.
        return effect.multiplier_q12
    return Q12_ONE


def get_spa_ability_modifier(
    ability: str,
    *,
    weather: str | None = None,
    ally_has_plus_minus: bool = False,
    move_type: str = "",
    hp_current: int = 1,
    hp_max: int = 1,
) -> int:
    """Returns Q12 multiplier for SpA layer. Default 4096 (no-op)."""
    effect = get_ability(ability)
    if effect is None or not effect.implemented:
        return Q12_ONE
    if effect.category != "stat_multiplier":
        return Q12_ONE
    if effect.raw_data.get("stat") not in {"sa", "spa", "at_or_sa"}:
        return Q12_ONE
    condition = effect.raw_data.get("condition")
    if effect.raw_data.get("stat") in {"sa", "spa"} and condition == "weather_sun":
        # TODO: HP drain handled in turn_engine
        if weather in ("sun", "harsh_sun", "harsh-sunlight", "harsh_sunshine"):
            return effect.multiplier_q12
    if effect.raw_data.get("stat") in {"sa", "spa"} and condition == "ally_plus_minus" and ally_has_plus_minus:
        return effect.multiplier_q12
    if condition == "type_electric" and move_type == "electric":
        return effect.multiplier_q12
    return _pinch_type_boost(
        ability,
        move_type=move_type,
        hp_current=hp_current,
        hp_max=hp_max,
    )


def get_bp_ability_modifier(
    ability: str,
    *,
    base_power: int,
    move_flags: set[str],
    move_id: str = "",
) -> int:
    """
    Returns Q12 multiplier for bp_mods layer. Default 4096 (no-op).

    Stacking order (Smogon Gen 9):
      1. Tough Claws / Iron Fist apply first (independent flags).
      2. Technician applies on the POST-other-BP-mod base power.

    This function returns ONE ability's contribution. The caller must
    sequence them correctly in formula.py.
    """
    effect = get_ability(ability)
    if effect is None or not effect.implemented:
        return Q12_ONE
    if effect.ability_id == "punk-rock" and "sound" in move_flags:
        return int(effect.raw_data.get("attacker_multiplier_q12", Q12_ONE))
    if effect.ability_id == "sharpness":
        return M_STAB if "slicing" in move_flags else Q12_ONE
    if effect.ability_id == "analytic":
        # Applicability is fail-closed by the runtime action-order authority;
        # this formula seam receives the effect only once that authority won.
        return effect.multiplier_q12
    if effect.category != "bp_modifier":
        return Q12_ONE
    condition = effect.raw_data.get("condition")
    if condition == "contact" and "contact" in move_flags:
        return effect.multiplier_q12
    if condition == "punch" and "punch" in move_flags:
        return effect.multiplier_q12
    if condition == "bite" and "bite" in move_flags:
        return effect.multiplier_q12
    if condition == "pulse" and "pulse" in move_flags:
        return effect.multiplier_q12
    if condition == "recoil" and "recoil" in move_flags and move_id != "struggle":
        return effect.multiplier_q12
    if condition == "sound_move" and "sound" in move_flags:
        return effect.multiplier_q12
    if condition == "slicing" and "slicing" in move_flags:
        return effect.multiplier_q12
    if condition == "has_secondary" and "has_secondary" in move_flags:
        return effect.multiplier_q12
    if condition == "bp_le_60" and base_power <= 60:
        return effect.multiplier_q12
    return Q12_ONE


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
    ally_has_plus_minus: bool = False,
    move_type: str = "",
    hp_current: int = 1,
    hp_max: int = 1,
    attacker_condition: str = "none",
) -> int:
    if ability is None:
        return Q12_ONE
    ability_id = ability.ability_id
    if (
        ability_id == "guts"
        and is_physical
        and attacker_condition in set(ability.raw_data.get("trigger_status", ()))
    ):
        return ability.multiplier_q12
    if not ability.implemented:
        return Q12_ONE
    stat_multiplier = get_atk_ability_modifier(
        ability_id,
        "physical" if is_physical else "special",
        move_type=move_type,
        hp_current=hp_current,
        hp_max=hp_max,
    )
    if stat_multiplier != Q12_ONE:
        return stat_multiplier
    spa_multiplier = get_spa_ability_modifier(
        ability_id,
        weather="none" if weather_suppressed else weather,
        ally_has_plus_minus=ally_has_plus_minus,
        move_type=move_type,
        hp_current=hp_current,
        hp_max=hp_max,
    )
    if not is_physical and spa_multiplier != Q12_ONE:
        return spa_multiplier
    if ability_id == "flower-gift" and is_physical:
        if weather in ("sun", "harsh-sunlight") and not weather_suppressed:
            return M_STAB
    if ability_id == "transistor" and move_type == "electric":
        return ability.multiplier_q12
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
    if ability_id == "fur-coat" and get_def_ability_modifier(ability_id, "physical" if is_physical else "special") != Q12_ONE:
        return M_DOUBLE
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
    is_physical: bool = True,
    defender_hp_ratio: float = 1.0,
    type_effectiveness: float | None = None,
    move_flags: set[str] | frozenset[str] | tuple[str, ...] = (),
) -> int:
    if ability is None or not ability.implemented:
        return Q12_ONE

    ability_id = ability.ability_id
    def_mod = get_def_ability_modifier(
        ability_id,
        "physical" if is_physical else "special",
    )
    if ability_id == "fur-coat":
        def_mod = Q12_ONE
    final_def_mod = (
        Q12_ONE
        if ability.category == "damage_mod_hp"
        else get_final_def_ability_modifier(
            ability_id,
            hp_ratio=defender_hp_ratio,
            type_effectiveness=type_effectiveness
            if type_effectiveness is not None
            else (2.0 if is_super_effective else 1.0),
            move_flags=set(move_flags),
        )
    )
    if def_mod != Q12_ONE or final_def_mod != Q12_ONE:
        return chain_modifiers([def_mod, final_def_mod])

    if ability_id == "fluffy":
        mods: list[int] = []
        if is_contact:
            mods.append(M_HALF)
        if move_type == "fire":
            mods.append(M_DOUBLE)
        return chain_modifiers(mods)

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
