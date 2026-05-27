from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field, replace
from advisor.damage.abilities import AbilityEffect, is_weather_suppressed
from advisor.damage.ability_modifiers import (
    attack_stat_ability_mod,
    attacker_damage_ability_mod_immunity_phase,
    attacker_base_power_ability_mod,
    attacker_move_attack_stat_ability_mod,
    defender_attack_stat_ability_mod,
    defender_base_power_ability_mod,
    defender_damage_ability_mod,
    defense_stat_ability_mod,
    get_bp_ability_modifier,
)
from advisor.damage.field import Field
from advisor.damage.grounded import GroundedInputs, is_grounded
from advisor.damage.item_modifiers import (
    attacker_base_power_item_mod,
    defense_stat_item_mod,
    defender_berry_mod,
    get_atk_item_modifier,
    get_bp_item_modifier,
    get_final_atk_item_modifier,
    get_spa_item_modifier,
)
from advisor.damage.items import ItemEffect
from advisor.damage.move_categories import has_secondary_effect
from advisor.damage.modifiers import (
    calc_stab,
    sand_spdef_boost,
    snow_def_boost,
    terrain_attack_modifier,
    terrain_defense_modifier,
    type_effectiveness_with_field,
    weather_modifier,
)
from advisor.damage.mold_breaker import (
    effective_attacker_ability,
    effective_defender_ability,
    is_mold_breaker_active,
    is_neutralizing_gas_active,
)
from advisor.damage.crit import resolve_crit_multiplier
from advisor.damage.modifiers.abilities import apply_adaptability, apply_multiscale
from advisor.damage.q12 import (
    M_NEUTRAL,
    M_SPREAD,
    Q12_ONE,
    apply_damage_modifier,
    chain_modifiers,
    pokeround,
)
from advisor.damage.screens import screen_modifier
from advisor.damage.stats import StatBlock
from advisor.damage.type_immunity import (
    is_immune_by_ability,
    is_wonder_guard_blocked,
    move_flags_for,
)
from advisor.damage.types import load_type_chart


@dataclass(frozen=True, slots=True)
class DamageContext:
    attacker_level: int
    move_power: int
    attack_stat: int
    defense_stat: int
    move_type: str
    attacker_types: tuple[str, ...]
    defender_types: tuple[str, ...]
    is_physical: bool
    is_critical: bool
    is_spread: bool
    move_id: str = ""
    field: Field = dataclass_field(default_factory=Field)
    attacker_grounded_inputs: GroundedInputs | None = None
    defender_grounded_inputs: GroundedInputs | None = None
    bypass_screens: bool = False
    breaks_screens: bool = False
    attacker_tera_type: str | None = None
    is_terastallized: bool = False
    weather_mod_q12: int = Q12_ONE
    item_mod_q12: int = Q12_ONE
    ability_atk_mod_q12: int = Q12_ONE
    ability_def_mod_q12: int = Q12_ONE
    final_mod_q12: int = Q12_ONE
    attacker_item: ItemEffect | None = None
    defender_item: ItemEffect | None = None
    attacker_species: str = ""
    defender_species: str = ""
    attacker_is_nfe: bool = False
    defender_is_nfe: bool = False
    attacker_is_transformed: bool = False
    defender_is_transformed: bool = False
    attacker_ability: AbilityEffect | None = None
    defender_ability: AbilityEffect | None = None
    attacker_stats: StatBlock | None = None
    defender_stats: StatBlock | None = None
    attacker_boosts: StatBlock | None = None
    defender_boosts: StatBlock | None = None
    attacker_booster_active: bool = False
    defender_booster_active: bool = False
    attacker_locked_paradox_stat: str | None = None
    defender_locked_paradox_stat: str | None = None
    ally_has_flower_gift: bool = False
    move_flags: tuple[str, ...] = ()
    is_contact: bool = False
    attacker_hp_current: int = 100
    attacker_hp_max: int = 100
    defender_hp_current: int | None = None
    defender_hp_max: int | None = None
    defender_hp_ratio: float = 1.0
    ally_ability_ids: tuple[str | None, ...] = ()


def base_damage(level: int, power: int, attack: int, defense: int) -> int:
    return ((((2 * level) // 5 + 2) * power * attack) // defense) // 50 + 2


def calc_damage_rolls(
    ctx: DamageContext,
    type_chart: dict[str, dict[str, float]] | None = None,
) -> list[int]:
    chart = type_chart or load_type_chart()
    field = ctx.field
    attacker_ability_id = ctx.attacker_ability.ability_id if ctx.attacker_ability else None
    defender_ability_id = ctx.defender_ability.ability_id if ctx.defender_ability else None
    neutralizing_gas_active = is_neutralizing_gas_active(
        attacker_ability_id,
        defender_ability_id,
        ctx.ally_ability_ids,
    )
    eff_attacker_ability = effective_attacker_ability(
        ctx.attacker_ability,
        neutralizing_gas_active,
    )
    eff_defender_ability = effective_defender_ability(
        ctx.defender_ability,
        attacker_ability_id,
        neutralizing_gas_active,
    )
    mold_breaker_active = (
        is_mold_breaker_active(attacker_ability_id) and not neutralizing_gas_active
    )
    weather_suppressed = is_weather_suppressed(
        eff_attacker_ability.ability_id if eff_attacker_ability else None,
        eff_defender_ability.ability_id if eff_defender_ability else None,
    )
    effective_weather = "none" if weather_suppressed else field.weather
    attacker_grounded_inputs = ctx.attacker_grounded_inputs or GroundedInputs(ctx.attacker_types)
    defender_grounded_inputs = ctx.defender_grounded_inputs or GroundedInputs(ctx.defender_types)
    attacker_grounded_inputs = replace(
        attacker_grounded_inputs,
        ability=eff_attacker_ability.ability_id if eff_attacker_ability else None,
    )
    defender_grounded_inputs = replace(
        defender_grounded_inputs,
        ability=eff_defender_ability.ability_id if eff_defender_ability else None,
    )
    attacker_grounded = is_grounded(
        attacker_grounded_inputs,
        field,
    )
    defender_grounded = is_grounded(
        defender_grounded_inputs,
        field,
    )
    move_id = ctx.move_id or ctx.move_type
    move_flags = ctx.move_flags or move_flags_for(move_id)
    if is_immune_by_ability(
        ctx.move_type,
        move_id,
        move_flags,
        eff_defender_ability,
        defender_grounded,
        mold_breaker_active,
    ):
        return [0] * 16
    bp = ctx.move_power
    move_category = "physical" if ctx.is_physical else "special"
    attacker_item_id = ctx.attacker_item.item_id if ctx.attacker_item else ""
    bp_item_modifier = (
        attacker_base_power_item_mod(
            ctx.attacker_item,
            ctx.move_type,
            ctx.attacker_species,
            ctx.is_physical,
        )
        if ctx.attacker_item is not None and ctx.attacker_item.kind == "type_boost"
        else get_bp_item_modifier(attacker_item_id, move_category=move_category)
    )
    bp = apply_damage_modifier(
        bp,
        bp_item_modifier,
    )
    pass1_move_flags = set(move_flags)
    if has_secondary_effect(move_id):
        # TODO PR #8a: suppress secondary effects.
        pass1_move_flags.add("has_secondary")
    if eff_attacker_ability and eff_attacker_ability.ability_id in (
        "tough-claws",
        "iron-fist",
        "strong-jaw",
        "mega-launcher",
        "reckless",
        "punk-rock",
        "sheer-force",
    ):
        bp_mod = get_bp_ability_modifier(
            eff_attacker_ability.ability_id,
            base_power=bp,
            move_flags=pass1_move_flags,
            move_id=move_id,
        )
        bp = apply_damage_modifier(bp, bp_mod)

    if eff_attacker_ability and eff_attacker_ability.ability_id == "technician":
        bp_mod = get_bp_ability_modifier(
            "technician",
            base_power=bp,
            move_flags=set(move_flags),
        )
        bp = apply_damage_modifier(bp, bp_mod)

    bp_mod = chain_modifiers(
        [
            terrain_attack_modifier(
                ctx.move_type,
                move_id,
                field.terrain,
                attacker_grounded,
            ),
            terrain_defense_modifier(
                ctx.move_type,
                move_id,
                field.terrain,
                defender_grounded,
            ),
            attacker_base_power_ability_mod(
                eff_attacker_ability,
                ctx.move_type,
                effective_weather,
                weather_suppressed,
            ),
            defender_base_power_ability_mod(
                eff_defender_ability,
                ctx.move_type,
            ),
        ]
    )
    power = max(1, apply_damage_modifier(bp, bp_mod))
    attack = apply_damage_modifier(
        ctx.attack_stat,
        chain_modifiers(
            [
                get_atk_item_modifier(
                    attacker_item_id,
                    move_category,
                    move_type=ctx.move_type,
                )
                if ctx.is_physical
                else get_spa_item_modifier(
                    attacker_item_id,
                    move_type=ctx.move_type,
                ),
                attack_stat_ability_mod(
                    eff_attacker_ability,
                    ctx.is_physical,
                    effective_weather,
                    weather_suppressed,
                    field.terrain,
                    ctx.attacker_stats,
                    ctx.attacker_boosts,
                    ctx.attacker_locked_paradox_stat,  # type: ignore[arg-type]
                    ctx.attacker_booster_active,
                    field.ally_has_plus_minus,
                    move_type=ctx.move_type,
                    hp_current=ctx.attacker_hp_current,
                    hp_max=ctx.attacker_hp_max,
                ),
                attacker_move_attack_stat_ability_mod(
                    eff_attacker_ability,
                    ctx.move_type,
                ),
                defender_attack_stat_ability_mod(
                    eff_defender_ability,
                    ctx.move_type,
                ),
            ]
        ),
    )
    defense = ctx.defense_stat
    if ctx.is_physical:
        defense_mod = snow_def_boost(ctx.defender_types, effective_weather)
    else:
        defense_mod = sand_spdef_boost(ctx.defender_types, effective_weather)
    defense = max(1, apply_damage_modifier(defense, defense_mod))
    defense = max(
        1,
        apply_damage_modifier(
            defense,
            chain_modifiers(
                [
                    defense_stat_ability_mod(
                        eff_defender_ability,
                        ctx.is_physical,
                        effective_weather,
                        weather_suppressed,
                        field.terrain,
                        ctx.defender_stats,
                        ctx.defender_boosts,
                        ctx.defender_locked_paradox_stat,  # type: ignore[arg-type]
                        ctx.defender_booster_active,
                    ),
                    defense_stat_item_mod(
                        ctx.defender_item,
                        ctx.is_physical,
                        ctx.defender_species,
                        ctx.defender_is_nfe,
                        ctx.defender_is_transformed,
                    ),
                ]
            ),
        ),
    )

    base = base_damage(
        ctx.attacker_level,
        power,
        attack,
        defense,
    )

    if ctx.is_spread:
        base = apply_damage_modifier(base, M_SPREAD)

    weather_mod = weather_modifier(ctx.move_type, effective_weather)
    if weather_mod == 0:
        return [0] * 16
    base = apply_damage_modifier(base, weather_mod)

    if ctx.weather_mod_q12 != M_NEUTRAL:
        base = apply_damage_modifier(base, ctx.weather_mod_q12)

    crit_mult = resolve_crit_multiplier(
        ctx.is_critical,
        eff_attacker_ability.ability_id if eff_attacker_ability else None,
    )
    if crit_mult != Q12_ONE:
        base = (base * crit_mult) // Q12_ONE

    effectiveness = type_effectiveness_with_field(
        ctx.move_type,
        ctx.defender_types,
        chart,
        field.with_weather(effective_weather),
    )
    if effectiveness == 0.0:
        return [0] * 16
    if is_wonder_guard_blocked(effectiveness, eff_defender_ability, mold_breaker_active):
        return [0] * 16
    # type_effectiveness_with_field returns a float from static chart data; item
    # final_mods compare at the Q12 boundary, so convert once at the hook.
    type_effectiveness_q12 = int(effectiveness * Q12_ONE)
    is_super_effective = effectiveness > 1.0
    is_not_very_effective = 0.0 < effectiveness < 1.0

    stab_mod = calc_stab(
        ctx.attacker_types,
        ctx.move_type,
        ctx.is_terastallized,
        ctx.attacker_tera_type,
    )
    stab_mod = apply_adaptability(
        stab_mod,
        eff_attacker_ability.ability_id if eff_attacker_ability else None,
        ctx.move_type,
        ctx.attacker_types,
    )
    final_mod = chain_modifiers(
        [
            screen_modifier(
                field.defender_side,
                ctx.is_physical,
                ctx.is_critical,
                field.is_doubles,
                ctx.breaks_screens,
                ctx.bypass_screens,
            ),
            ctx.item_mod_q12,
            get_final_atk_item_modifier(
                attacker_item_id,
                type_effectiveness_q12=type_effectiveness_q12,
            ),
            defender_berry_mod(
                ctx.defender_item,
                ctx.move_type,
                is_super_effective,
            ),
            ctx.ability_atk_mod_q12,
            attacker_damage_ability_mod_immunity_phase(
                eff_attacker_ability,
                is_not_very_effective,
            ),
            ctx.ability_def_mod_q12,
            defender_damage_ability_mod(
                eff_defender_ability,
                ctx.move_type,
                is_super_effective,
                ctx.is_contact,
                ctx.is_physical,
                ctx.defender_hp_ratio,
                effectiveness,
                set(move_flags),
            ),
            ctx.final_mod_q12,
        ]
    )

    rolls: list[int] = []
    for random_factor in range(85, 101):
        damage = (base * random_factor) // 100
        if stab_mod != M_NEUTRAL:
            damage = apply_damage_modifier(damage, stab_mod)
        damage = int(pokeround(damage) * effectiveness)
        damage = apply_damage_modifier(max(1, damage), final_mod)
        defender_hp_current = ctx.defender_hp_current
        defender_hp_max = ctx.defender_hp_max
        if defender_hp_current is None or defender_hp_max is None:
            defender_hp_current = 1 if ctx.defender_hp_ratio == 1.0 else 0
            defender_hp_max = 1
        damage = apply_multiscale(
            damage,
            eff_defender_ability.ability_id if eff_defender_ability else None,
            defender_hp_current,
            defender_hp_max,
        )
        rolls.append(damage)
    return rolls
