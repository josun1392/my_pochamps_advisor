"""Unknown-first direct-damage mechanics slice over the native Q12 engine."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from collections import Counter
from typing import Any

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.crit import select_critical_damage_stages
from advisor.damage.abilities import get_ability
from advisor.damage.ability_modifiers import get_bp_ability_modifier
from advisor.damage.field import Field, SideField
from advisor.damage.items import get_item
from advisor.damage.q12 import M_HALF, Q12_ONE
from advisor.damage.stats import StatBlock
from advisor.damage.type_immunity import load_move_flags
from advisor.damage.types import type_effectiveness_multiplier
from advisor.probability.single_hit import ko_chance_from_outcomes
from llm.advisor_battle_state_context import (
    DYNAMIC_MOVE_ASSESSMENT_REGISTRY,
    build_current_hp_based_power_assessment,
    calculate_stage_adjusted_stat,
    normalize_user_confirmed_current_condition,
    normalize_user_confirmed_current_field_state,
    normalize_user_confirmed_current_stat_stage,
)


_STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
_BOOST_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed")
_KNOWN_ABSENT = {"status": "known_absent"}
LEVEL_BASED_FIXED_DAMAGE_MOVE_TYPES = {"seismic-toss": "normal", "night-shade": "ghost"}
UNSUPPORTED_SPECIAL_FIXED_DAMAGE_MOVE_IDS = frozenset({
    "bide", "comeuppance", "counter", "dragon-rage", "endeavor", "final-gambit",
    "fissure", "guillotine", "horn-drill", "metal-burst", "mirror-coat",
    "natures-madness", "psywave", "ruination", "sheer-cold", "sonic-boom", "super-fang",
})
NATIVE_DIRECT_MECHANICS_SOURCES = frozenset({"native_q12_direct_damage", "native_level_based_fixed_damage"})
STATIC_ATTACKER_DAMAGE_ABILITIES = frozenset({
    "adaptability", "iron-fist", "strong-jaw", "mega-launcher", "technician", "tinted-lens", "sniper",
})
STATIC_DEFENDER_DAMAGE_ABILITIES = frozenset({"thick-fat", "fur-coat", "ice-scales", "filter", "solid-rock", "prism-armor", "wonder-guard", "multiscale", "shadow-shield"})
ABILITY_MODIFIER_TAGS = {
    "adaptability": "ability_adaptability_stab_boost",
    "iron-fist": "ability_iron_fist_boost",
    "strong-jaw": "ability_strong_jaw_boost",
    "mega-launcher": "ability_mega_launcher_boost",
    "technician": "ability_technician_boost",
    "tinted-lens": "ability_tinted_lens_not_very_effective_boost",
}
STATIC_ATTACKER_DAMAGE_ITEMS = frozenset({"life-orb", "choice-band", "choice-specs", "muscle-band", "wise-glasses", "expert-belt"})
STATIC_DEFENDER_DAMAGE_ITEMS = frozenset({"assault-vest"})
_CURRENT_HP_PROPORTIONAL_DIRECT_MOVES = frozenset({"eruption", "water-spout", "dragon-energy"})
_CURRENT_HP_BRACKET_DIRECT_MOVES = frozenset({"flail", "reversal"})
_STATUS_CONDITION_POWER_DIRECT_MOVES = frozenset({"hex", "venoshock"})
_ENVIRONMENT_TRANSFORMATION_DIRECT_MOVES = frozenset({"weather-ball", "terrain-pulse"})
_TURN_EVENT_POWER_DIRECT_MOVES = frozenset({"avalanche", "revenge", "payback", "assurance"})
ITEM_MODIFIER_TAGS = {
    "life-orb": "item_life_orb_boost",
    "choice-band": "item_choice_band_boost",
    "choice-specs": "item_choice_specs_boost",
    "muscle-band": "item_muscle_band_boost",
    "wise-glasses": "item_wise_glasses_special_boost",
    "expert-belt": "item_expert_belt_super_effective_boost",
}
DEFENDER_ITEM_MODIFIER_TAGS = {"assault-vest": "defender_item_assault_vest_special_defense"}
DEFENDER_TYPE_RESIST_BERRY_TAG = "defender_item_type_resist_berry_reduction"
DEFENDER_CHILAN_BERRY_TAG = "defender_item_chilan_berry_reduction"
DEFENDER_ABILITY_MODIFIER_TAGS = {
    "thick-fat": "defender_ability_thick_fat_reduction",
    "fur-coat": "defender_ability_fur_coat_reduction",
    "ice-scales": "defender_ability_ice_scales_reduction",
    "filter": "defender_ability_filter_reduction",
    "solid-rock": "defender_ability_solid_rock_reduction",
    "prism-armor": "defender_ability_prism_armor_reduction",
    "wonder-guard": "defender_ability_wonder_guard_immunity",
    "multiscale": "defender_ability_multiscale_reduction",
    "shadow-shield": "defender_ability_shadow_shield_reduction",
}


def evaluate_direct_damage_mechanics(
    snapshot_damage_input: Mapping[str, Any], *, stat_provenance: Mapping[str, Any],
    trusted_level: int | None, is_critical: bool = False,
) -> dict[str, Any]:
    """Return bounded public mechanics evidence without inventing battle facts.

    Only one normal, non-critical, single-hit damaging move is in scope. The
    supported dynamic-power exceptions consume only their exact frozen inputs.
    The caller supplies its existing frozen snapshot damage input and provenance.
    `direct_mechanics_context` is deliberately explicit: omitted facts are
    reported as logical missing names instead of becoming defaults.
    """
    missing: list[str] = []
    if not isinstance(is_critical, bool):
        return _insufficient(["is_critical"])
    if not isinstance(snapshot_damage_input, Mapping) or not isinstance(stat_provenance, Mapping):
        return _insufficient(["snapshot"])
    context = _mapping(snapshot_damage_input.get("battle_context"))
    current = _mapping(context.get("current_state"))
    direct = _mapping(current.get("direct_mechanics_context"))
    if not direct:
        return _insufficient(["direct_mechanics_context"])
    generation = direct.get("generation")
    if generation != "gen9":
        return _unsupported("generation") if generation else _insufficient(["generation"])
    move = _mapping(snapshot_damage_input.get("move"))
    move_id = move.get("move_id")
    if not isinstance(move_id, str) or not move_id:
        missing.append("selected_move")
    if move_id in LEVEL_BASED_FIXED_DAMAGE_MOVE_TYPES:
        return _evaluate_level_based_fixed_damage(
            direct=direct, stat_provenance=stat_provenance, trusted_level=trusted_level,
            move_id=move_id, generation=generation,
        )
    if move_id in UNSUPPORTED_SPECIAL_FIXED_DAMAGE_MOVE_IDS:
        return _fixed_unsupported("unsupported_fixed_damage_rule")
    category, power, move_type = move.get("category"), move.get("power"), move.get("type")
    if category == "status":
        return _unsupported("status_move")
    if move_id in DYNAMIC_MOVE_ASSESSMENT_REGISTRY and move_id not in {"facade", "brine", *_STATUS_CONDITION_POWER_DIRECT_MOVES, *_ENVIRONMENT_TRANSFORMATION_DIRECT_MOVES, *_TURN_EVENT_POWER_DIRECT_MOVES, *_CURRENT_HP_PROPORTIONAL_DIRECT_MOVES, *_CURRENT_HP_BRACKET_DIRECT_MOVES}:
        return _unsupported("dynamic_base_power")
    facade = _facade_power_context(current) if move_id == "facade" else None
    current_hp_power = _current_hp_proportional_power_context(move_id=move_id, direct_attacker=_mapping(direct.get("attacker"))) if move_id in _CURRENT_HP_PROPORTIONAL_DIRECT_MOVES else None
    current_hp_bracket_power = _current_hp_bracket_power_context(move_id=move_id, direct_attacker=_mapping(direct.get("attacker"))) if move_id in _CURRENT_HP_BRACKET_DIRECT_MOVES else None
    brine_power = _brine_power_context(direct_defender=_mapping(direct.get("defender"))) if move_id == "brine" else None
    status_condition_power = _status_condition_power_context(move_id=move_id, current=current) if move_id in _STATUS_CONDITION_POWER_DIRECT_MOVES else None
    environment_transformation = _environment_transformation_context(move_id=move_id, current=current) if move_id in _ENVIRONMENT_TRANSFORMATION_DIRECT_MOVES else None
    turn_event_power = _turn_event_power_context(move_id=move_id, current=current) if move_id in _TURN_EVENT_POWER_DIRECT_MOVES else None
    if move_id == "facade" and (category != "physical" or power != 70 or move_type != "normal"):
        return _unsupported("facade_metadata")
    expected_current_hp_metadata = {"eruption": "fire", "water-spout": "water", "dragon-energy": "dragon"}
    if move_id in _CURRENT_HP_PROPORTIONAL_DIRECT_MOVES and (category != "special" or power != 150 or move_type != expected_current_hp_metadata[move_id]):
        return _unsupported("current_hp_proportional_metadata")
    expected_current_hp_bracket_metadata = {"flail": "normal", "reversal": "fighting"}
    if move_id in _CURRENT_HP_BRACKET_DIRECT_MOVES and (category != "physical" or power != 20 or move_type != expected_current_hp_bracket_metadata[move_id]):
        return _unsupported("current_hp_bracket_metadata")
    if move_id == "brine" and (category != "special" or power != 65 or move_type != "water"):
        return _unsupported("brine_metadata")
    expected_status_condition_metadata = {"hex": "ghost", "venoshock": "poison"}
    if move_id in _STATUS_CONDITION_POWER_DIRECT_MOVES and (category != "special" or power != 65 or move_type != expected_status_condition_metadata[move_id]):
        return _unsupported("status_condition_power_metadata")
    if move_id in _ENVIRONMENT_TRANSFORMATION_DIRECT_MOVES and (category != "special" or power != 50 or move_type != "normal"):
        return _unsupported("environment_transformation_metadata")
    expected_turn_event_metadata = {"avalanche": ("physical", 60, "ice"), "revenge": ("physical", 60, "fighting"), "payback": ("physical", 50, "dark"), "assurance": ("physical", 60, "dark")}
    if move_id in _TURN_EVENT_POWER_DIRECT_MOVES and (category, power, move_type) != expected_turn_event_metadata[move_id]:
        return _unsupported("turn_event_power_metadata")
    if isinstance(facade, Mapping):
        if facade.get("status") == "unsupported_mechanic":
            return _unsupported("facade_condition_context")
        missing.extend(facade.get("missing_inputs", []))
        if facade.get("status") == "known":
            power = facade["effective_power"]
    if isinstance(current_hp_power, Mapping):
        if current_hp_power.get("status") == "not_applicable":
            return _unsupported("attacker_already_fainted")
        if current_hp_power.get("status") == "unsupported_mechanic":
            return _unsupported("current_hp_proportional_hp_context")
        missing.extend(current_hp_power.get("missing_inputs", []))
        if current_hp_power.get("status") == "known":
            power = current_hp_power["effective_power"]
    if isinstance(current_hp_bracket_power, Mapping):
        if current_hp_bracket_power.get("status") == "not_applicable":
            return _unsupported("attacker_already_fainted")
        if current_hp_bracket_power.get("status") == "unsupported_mechanic":
            return _unsupported("current_hp_bracket_context")
        missing.extend(current_hp_bracket_power.get("missing_inputs", []))
        if current_hp_bracket_power.get("status") == "known":
            power = current_hp_bracket_power["effective_power"]
    if isinstance(brine_power, Mapping):
        if brine_power.get("status") == "not_applicable":
            return _unsupported("defender_already_fainted")
        if brine_power.get("status") == "unsupported_mechanic":
            return _unsupported("brine_hp_context")
        missing.extend(brine_power.get("missing_inputs", []))
        if brine_power.get("status") == "known":
            power = brine_power["effective_power"]
    if isinstance(status_condition_power, Mapping):
        if status_condition_power.get("status") == "unsupported_mechanic":
            return _unsupported("status_condition_power_context")
        missing.extend(status_condition_power.get("missing_inputs", []))
        if status_condition_power.get("status") == "known":
            power = status_condition_power["effective_power"]
    if isinstance(environment_transformation, Mapping):
        if environment_transformation.get("status") == "unsupported_mechanic":
            return _unsupported("environment_transformation_context")
        missing.extend(environment_transformation.get("missing_inputs", []))
        if environment_transformation.get("status") == "known":
            power = environment_transformation["effective_power"]
            move_type = environment_transformation["effective_type"]
    if isinstance(turn_event_power, Mapping):
        if turn_event_power.get("status") == "unsupported_mechanic":
            return _unsupported("turn_event_power_context")
        missing.extend(turn_event_power.get("missing_inputs", []))
        if turn_event_power.get("status") == "known":
            power = turn_event_power["effective_power"]
    minimum, maximum = move.get("min_hits"), move.get("max_hits")
    if minimum is None and maximum is None:
        hit_count = 1
    elif isinstance(minimum, int) and not isinstance(minimum, bool) and minimum == maximum and 1 <= minimum <= 4:
        hit_count = minimum
    elif isinstance(minimum, int) and isinstance(maximum, int) and minimum != maximum:
        return _unsupported("variable_multi_hit_move")
    else:
        return _unsupported("invalid_fixed_hit_count")
    if hit_count > 1 and move.get("drain") not in {None, 0}:
        return _unsupported("fixed_hit_consequence_not_supported")
    if category not in {"physical", "special"}:
        return _unsupported("move_category")
    if not _positive_int(power) or not _nonempty_str(move_type):
        missing.append("selected_move_metadata")
    attacker = _ready_side(stat_provenance.get("attacker"), "attacker", missing)
    defender = _ready_side(stat_provenance.get("defender"), "defender", missing)
    type_authorities = _type_damage_authorities(stat_provenance)
    if type_authorities["unsupported"]:
        return _unsupported("current_type_context")
    missing.extend(type_authorities["missing_inputs"])
    if not _valid_level(trusted_level):
        missing.append("attacker.level")
    direct_attacker = _mapping(direct.get("attacker"))
    direct_defender = _mapping(direct.get("defender"))
    modifier = _modifier_context(
        current=current, direct=direct, category=category, move_type=move_type,
        defender_types=defender["types"] if defender is not None else (),
        ignore_burn_attack_reduction=bool(isinstance(facade, Mapping) and facade.get("burn_attack_reduction_ignored") is True),
    )
    ability_modifier = _attacker_ability_modifier_context(
        current=current, direct_attacker=direct_attacker, move_id=move_id, power=power,
        move_type=move_type, attacker_types=attacker["types"] if attacker is not None else (), is_critical=is_critical,
        defender_types=defender["types"] if defender is not None else (),
    )
    item_modifier = _attacker_item_modifier_context(
        stat_provenance=stat_provenance, direct_attacker=direct_attacker, category=category,
        move_type=move_type, defender_types=defender["types"] if defender is not None else (),
    )
    defender_item_modifier = _defender_item_modifier_context(
        stat_provenance=stat_provenance, direct_defender=direct_defender, category=category,
        move_type=move_type, defender_types=defender["types"] if defender is not None else (), hit_count=hit_count,
    )
    defender_ability_modifier = _defender_ability_modifier_context(
        current=current, direct_defender=direct_defender, category=category, move_type=move_type,
        defender_types=defender["types"] if defender is not None else (),
    )
    stage_context = _relevant_stage_context(current=current, category=category)
    legacy_modifier_reason = _unsupported_modifier(
        {**direct_attacker, "ability": _KNOWN_ABSENT, "item": _KNOWN_ABSENT}, {**direct_defender, "ability": _KNOWN_ABSENT}, {}
    )
    if legacy_modifier_reason is not None:
        return _unsupported(legacy_modifier_reason)
    modifier_reason = modifier.get("unsupported_reason")
    if modifier_reason is not None:
        return _unsupported(modifier_reason)
    if ability_modifier["unsupported_reason"] is not None:
        return _unsupported(ability_modifier["unsupported_reason"])
    if item_modifier["unsupported_reason"] is not None:
        return _unsupported(item_modifier["unsupported_reason"])
    if defender_item_modifier["unsupported_reason"] is not None:
        return _unsupported(defender_item_modifier["unsupported_reason"])
    if defender_ability_modifier["unsupported_reason"] is not None:
        return _unsupported(defender_ability_modifier["unsupported_reason"])
    if stage_context["unsupported_reason"] is not None:
        return _unsupported(stage_context["unsupported_reason"])
    missing.extend(modifier.get("missing_inputs", []))
    missing.extend(ability_modifier["missing_inputs"])
    missing.extend(item_modifier["missing_inputs"])
    missing.extend(defender_item_modifier["missing_inputs"])
    missing.extend(defender_ability_modifier["missing_inputs"])
    missing.extend(stage_context["missing_inputs"])
    for side_name, side in (("attacker", direct_attacker), ("defender", direct_defender)):
        if side_name == "defender" and not defender_ability_modifier["authority_explicit"]:
            _require_known_absent(side.get("ability"), f"{side_name}.ability", missing)
        if not _item_authority_is_explicit(stat_provenance, side_name):
            _require_known_absent(side.get("item"), f"{side_name}.item", missing)
        _require_zero_boosts(side.get("boosts"), f"{side_name}.boosts", missing)
        _require_hp(side, side_name, missing)
        if side_name == "attacker" and modifier.get("burn_known"):
            pass
        else:
            _require_known_absent(side.get("status"), f"{side_name}.status", missing)
    field = _mapping(direct.get("field"))
    if not modifier.get("weather_known"):
        _require_known_absent(field.get("weather"), "field.weather", missing)
    if not modifier.get("terrain_known"):
        _require_known_absent(field.get("terrain"), "field.terrain", missing)
    if missing:
        return _insufficient(missing)
    assert attacker is not None and defender is not None and isinstance(trusted_level, int)
    try:
        attacker_stats = _stat_block(attacker["final_stats"])
        defender_stats = _stat_block(defender["final_stats"])
        is_physical = category == "physical"
        attack_stat = attacker_stats.atk if is_physical else attacker_stats.spa
        defense_stat = defender_stats.def_ if is_physical else defender_stats.spd
        if stage_context["applied"]:
            offensive_stage, defensive_stage = select_critical_damage_stages(
                stage_context["offensive_stage_value"], stage_context["defensive_stage_value"], is_critical=is_critical,
            )
            attack_stat = calculate_stage_adjusted_stat(attack_stat, offensive_stage)
            defense_stat = calculate_stage_adjusted_stat(defense_stat, defensive_stage)
        rolls = calc_damage_rolls(DamageContext(
            attacker_level=trusted_level, move_power=power,  # type: ignore[arg-type]
            attack_stat=attack_stat, defense_stat=defense_stat,
            move_type=move_type, attacker_types=tuple(attacker["types"]),
            defender_types=tuple(defender["types"]), is_physical=is_physical,
            is_critical=is_critical, is_spread=False, move_id=move_id,
            attacker_species=attacker["pokemon_identity"], defender_species=defender["pokemon_identity"],
            attacker_stats=attacker_stats, defender_stats=defender_stats,
            field=modifier["field"], burn_mod_q12=modifier["burn_mod_q12"],
            attacker_grounded=modifier.get("attacker_grounded"), defender_grounded=modifier.get("defender_grounded"),
            attacker_ability=ability_modifier["ability_effect"],
            attacker_item=item_modifier["item_effect"],
            defender_item=defender_item_modifier["item_effect"],
            defender_ability=defender_ability_modifier["ability_effect"],
            defender_hp_current=direct_defender["current_hp"], defender_hp_max=direct_defender["max_hp"],
        ))
    except (TypeError, ValueError, KeyError):
        return _unsupported("native_direct_damage")
    defender_hp = direct_defender["current_hp"]
    max_hp = direct_defender["max_hp"]
    total_counts = Counter({0: 1})
    for _ in range(hit_count):
        total_counts = _convolve_roll_counts(total_counts, Counter(rolls))
    total_rolls = tuple(value for value, count in total_counts.items() for _ in range(count))
    result = {
        "status": "known", "move": move_id, "type_effectiveness": type_effectiveness_multiplier(move_type, tuple(defender["types"])),
        "hit_count": hit_count, "per_hit_damage_range": {"minimum": min(rolls), "maximum": max(rolls)},
        "damage_range": {"minimum": min(total_rolls), "maximum": max(total_rolls)},
        "damage_percent_range": {"minimum": round(min(total_rolls) * 100 / max_hp, 2), "maximum": round(max(total_rolls) * 100 / max_hp, 2)},
        "ko_result": {"status": "resolved", "single_hit_probability": float(ko_chance_from_outcomes(total_rolls, defender_hp))},
        "damage_model": "fixed_hit_formula" if hit_count > 1 else "single_hit_formula",
        "applied_damage_modifiers": [*modifier["applied"], *ability_modifier["applied"], *item_modifier["applied"], *defender_item_modifier["applied"], *defender_ability_modifier["applied"]], "missing_inputs": [], "unsupported_reason": None,
        "stat_stage_evidence": _critical_stage_evidence(stage_context, is_critical),
        "mechanics_source": "native_q12_direct_damage", "generation": generation,
        "type_damage_evidence": type_authorities["evidence"],
    }
    if isinstance(facade, Mapping) and facade.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(facade))
    if isinstance(current_hp_power, Mapping) and current_hp_power.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(current_hp_power))
    if isinstance(current_hp_bracket_power, Mapping) and current_hp_bracket_power.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(current_hp_bracket_power))
    if isinstance(brine_power, Mapping) and brine_power.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(brine_power))
    if isinstance(status_condition_power, Mapping) and status_condition_power.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(status_condition_power))
    if isinstance(environment_transformation, Mapping) and environment_transformation.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(environment_transformation))
    if isinstance(turn_event_power, Mapping) and turn_event_power.get("status") == "known":
        result["dynamic_power_evidence"] = deepcopy(dict(turn_event_power))
    if hit_count == 1:
        result["exact_damage_rolls"] = tuple(rolls)
    return result


def _relevant_stage_context(*, current: Mapping[str, Any], category: Any) -> dict[str, Any]:
    offensive, defensive = ("attack", "defense") if category == "physical" else ("special-attack", "special-defense")
    result = {"missing_inputs": [], "unsupported_reason": None, "applied": False, "offensive_stage_value": 0, "defensive_stage_value": 0, "evidence": None}
    context = current.get("stat_stage_context")
    if context is None:
        return result
    entries = context.get("current_stages") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        result["missing_inputs"] = [f"attacker.{offensive}_stage", f"defender.{defensive}_stage"]
        return result
    resolved: dict[tuple[str, str], int] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            result["unsupported_reason"] = "stat_stage_context"; return result
        try:
            normalized = normalize_user_confirmed_current_stat_stage({key: value for key, value in entry.items() if key != "provenance"})
        except ValueError:
            result["unsupported_reason"] = "stat_stage_context"; return result
        key = (normalized["side"], normalized["stat"])
        if key in resolved:
            result["unsupported_reason"] = "stat_stage_context"; return result
        resolved[key] = normalized["stage"]
    needed = (("self", offensive), ("opponent", defensive))
    if not any(key in resolved for key in needed):
        return result
    missing = [f"attacker.{offensive}_stage" if side == "self" else f"defender.{stat}_stage" for side, stat in needed if (side, stat) not in resolved]
    if missing:
        result["missing_inputs"] = missing; return result
    result.update(applied=True, offensive_stage_value=resolved[("self", offensive)], defensive_stage_value=resolved[("opponent", defensive)])
    result["evidence"] = {"offensive_stage_stat": offensive, "offensive_stage_value": result["offensive_stage_value"], "defensive_stage_stat": defensive, "defensive_stage_value": result["defensive_stage_value"], "stage_adjustment_applied": True}
    return result


def _critical_stage_evidence(stage_context: Mapping[str, Any], is_critical: bool) -> Any:
    """Keep legacy non-critical evidence byte-compatible while recording crit selection."""
    evidence = stage_context.get("evidence")
    if not is_critical or not isinstance(evidence, Mapping):
        return evidence
    offensive, defensive = select_critical_damage_stages(
        stage_context["offensive_stage_value"], stage_context["defensive_stage_value"], is_critical=True,
    )
    return {
        **deepcopy(dict(evidence)), "critical_damage_stage_selection": True,
        "effective_offensive_stage_value": offensive, "effective_defensive_stage_value": defensive,
    }


def _evaluate_level_based_fixed_damage(*, direct: Mapping[str, Any], stat_provenance: Mapping[str, Any], trusted_level: int | None, move_id: str, generation: str) -> dict[str, Any]:
    """Resolve only canonical attacker-level damage without Q12/stat inputs."""
    missing: list[str] = []
    if not _valid_level(trusted_level):
        missing.append("attacker.level")
    defender = _mapping(direct.get("defender"))
    _require_hp(defender, "defender", missing)
    defender_block = _mapping(stat_provenance.get("defender"))
    defender_types = _available(defender_block.get("legacy_types"))
    if defender_types is None:
        defender_types = _available(defender_block.get("types"))
    if not isinstance(defender_types, list) or not defender_types or not all(_nonempty_str(item) for item in defender_types):
        missing.append("defender.types")
    for side_name in ("attacker", "defender"):
        ability = _mapping(direct.get(side_name)).get("ability")
        if ability == _KNOWN_ABSENT:
            continue
        if isinstance(ability, Mapping) and ability.get("status") == "known" and _nonempty_str(ability.get("value")):
            return _fixed_unsupported("ability_modifier")
        missing.append(f"{side_name}.ability")
    if missing:
        return _fixed_insufficient(missing)
    assert isinstance(trusted_level, int) and isinstance(defender_types, list)
    effectiveness = type_effectiveness_multiplier(LEVEL_BASED_FIXED_DAMAGE_MOVE_TYPES[move_id], tuple(defender_types))
    damage = trusted_level if effectiveness > 0 else 0
    max_hp, current_hp = defender["max_hp"], defender["current_hp"]
    return {
        "status": "known", "move": move_id, "damage_model": "level_based_fixed", "fixed_damage": damage,
        "type_effectiveness": effectiveness, "hit_count": 1, "per_hit_damage_range": None,
        "damage_range": {"minimum": damage, "maximum": damage},
        "damage_percent_range": {"minimum": round(damage * 100 / max_hp, 2), "maximum": round(damage * 100 / max_hp, 2)},
        "ko_result": {"status": "resolved", "single_hit_probability": 1.0 if damage >= current_hp else 0.0},
        "missing_inputs": [], "unsupported_reason": None,
        "mechanics_source": "native_level_based_fixed_damage", "generation": generation,
    }


def _convolve_roll_counts(left: Counter[int], right: Counter[int]) -> Counter[int]:
    result: Counter[int] = Counter()
    for left_value, left_count in left.items():
        for right_value, right_count in right.items():
            result[left_value + right_value] += left_count * right_count
    return result


def _ready_side(value: Any, side: str, missing: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        missing.append(f"{side}.identity")
        return None
    identity = value.get("pokemon_identity")
    if not _nonempty_str(identity): missing.append(f"{side}.identity")
    types = _available(value.get("types"))
    type_status = _mapping(value.get("type_authority")).get("status")
    if (not isinstance(types, list) or not types or not all(_nonempty_str(item) for item in types)) and type_status not in {"unknown", "malformed"}:
        missing.append(f"{side}.types")
    stats = _available(value.get("final_stats"))
    if not isinstance(stats, Mapping) or set(stats) != set(_STAT_KEYS): missing.append(f"{side}.final_stats")
    return {"pokemon_identity": identity, "types": types, "final_stats": stats}


def _type_damage_authorities(stat_provenance: Mapping[str, Any]) -> dict[str, Any]:
    sides = {name: _mapping(stat_provenance.get(name)).get("type_authority") for name in ("attacker", "defender")}
    normalized = {name: _mapping(value) or {"status": "known", "basis": "legacy_species"} for name, value in sides.items()}
    if any(value.get("status") == "malformed" for value in normalized.values()):
        return {"unsupported": True, "missing_inputs": [], "evidence": None}
    missing = [
        f"{name}.current_type" for name, value in normalized.items()
        if value.get("status") not in {None, "known"} and value.get("basis") == "current_type_context"
    ]
    attacker_basis, defender_basis = normalized["attacker"].get("basis"), normalized["defender"].get("basis")
    return {
        "unsupported": False,
        "missing_inputs": missing,
        "evidence": {
            "attacker_type_authority": attacker_basis,
            "defender_type_authority": defender_basis,
            "stab_basis": attacker_basis,
            "effectiveness_basis": defender_basis,
            "current_type_override_used": "current_type_context" in {attacker_basis, defender_basis},
            "legacy_species_type_compatibility_used": "legacy_species" in {attacker_basis, defender_basis},
            "type_related_damage_supportability": "complete" if not missing else "insufficient_context",
        },
    }


def _require_known_absent(value: Any, name: str, missing: list[str]) -> None:
    if value == _KNOWN_ABSENT:
        return
    missing.append(name)


def _require_zero_boosts(value: Any, name: str, missing: list[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != set(_BOOST_KEYS) or any(value[key] != 0 for key in _BOOST_KEYS):
        missing.append(name)


def _require_hp(value: Mapping[str, Any], side: str, missing: list[str]) -> None:
    current, maximum = value.get("current_hp"), value.get("max_hp")
    if not _positive_int(current): missing.append(f"{side}.current_hp")
    if not _positive_int(maximum): missing.append(f"{side}.max_hp")
    if _positive_int(current) and _positive_int(maximum) and current > maximum: missing.append(f"{side}.current_hp")


def _unsupported_modifier(attacker: Mapping[str, Any], defender: Mapping[str, Any], field: Mapping[str, Any]) -> str | None:
    for side in (attacker, defender):
        for key, reason in (("ability", "ability_modifier"), ("item", "item_modifier"), ("status", "major_status_modifier")):
            value = side.get(key)
            if isinstance(value, Mapping) and value.get("status") == "known" and _nonempty_str(value.get("value")):
                return reason
        boosts = side.get("boosts")
        if isinstance(boosts, Mapping) and set(boosts) == set(_BOOST_KEYS) and any(boosts[key] != 0 for key in _BOOST_KEYS):
            return "stat_stage_modifier"
    for key in ("weather", "terrain"):
        value = field.get(key)
        if isinstance(value, Mapping) and value.get("status") == "known" and _nonempty_str(value.get("value")):
            return "field_modifier"
    return None


def _attacker_ability_modifier_context(*, current: Mapping[str, Any], direct_attacker: Mapping[str, Any], move_id: str, power: Any, move_type: Any, attacker_types: tuple[str, ...] | list[str], defender_types: tuple[str, ...] | list[str], is_critical: bool = False) -> dict[str, Any]:
    """Resolve only static request-start attacker ability effects already owned by Q12."""
    result = {"ability_effect": None, "applied": [], "missing_inputs": [], "unsupported_reason": None}
    context = current.get("ability_context")
    if not isinstance(context, Mapping):
        if direct_attacker.get("ability") == _KNOWN_ABSENT:
            return result
        if isinstance(direct_attacker.get("ability"), Mapping) and direct_attacker["ability"].get("status") == "known":
            result["unsupported_reason"] = "ability_modifier"
        else:
            result["missing_inputs"].append("attacker.ability")
        return result
    entries = context.get("current_abilities")
    if not isinstance(entries, list):
        result["missing_inputs"].append("attacker.ability")
        return result
    self_entries = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == "self"]
    if not self_entries and direct_attacker.get("ability") == _KNOWN_ABSENT:
        return result
    if len(self_entries) != 1:
        result["missing_inputs"].append("attacker.ability")
        return result
    ability_id = self_entries[0].get("ability")
    if not _nonempty_str(ability_id) or ability_id == "unknown":
        result["missing_inputs"].append("attacker.ability")
        return result
    if ability_id in _ACTION_ORDER_ONLY_ABILITIES or ability_id in _KNOWN_NO_DIRECT_DAMAGE_EFFECT_ABILITIES:
        return result
    if ability_id not in STATIC_ATTACKER_DAMAGE_ABILITIES:
        result["unsupported_reason"] = "ability_modifier"
        return result
    effect = get_ability(ability_id)
    if effect is None:
        result["unsupported_reason"] = "ability_modifier"
        return result
    if ability_id == "sniper":
        result["ability_effect"] = effect
        if is_critical:
            result["applied"].append("ability_sniper_critical_damage")
        return result
    if ability_id == "adaptability":
        if move_type in attacker_types:
            result["ability_effect"] = effect
            result["applied"].append(ABILITY_MODIFIER_TAGS[ability_id])
        return result
    if ability_id == "tinted-lens":
        effectiveness = type_effectiveness_multiplier(move_type, tuple(defender_types)) if _nonempty_str(move_type) else None
        if effectiveness is not None and 0 < effectiveness < 1:
            result["ability_effect"] = effect
            result["applied"].append(ABILITY_MODIFIER_TAGS[ability_id])
        return result
    if not _positive_int(power):
        result["missing_inputs"].append("selected_move_metadata")
        return result
    flags_by_move = load_move_flags()
    if ability_id != "technician" and move_id not in flags_by_move:
        result["unsupported_reason"] = "move_flag_metadata"
        return result
    flags = set(flags_by_move.get(move_id, ()))
    modifier = get_bp_ability_modifier(ability_id, base_power=power, move_flags=flags, move_id=move_id)
    if modifier == Q12_ONE:
        return result
    result["ability_effect"] = effect
    result["applied"].append(ABILITY_MODIFIER_TAGS[ability_id])
    return result


def _defender_ability_modifier_context(*, current: Mapping[str, Any], direct_defender: Mapping[str, Any], category: Any, move_type: Any, defender_types: tuple[str, ...] | list[str]) -> dict[str, Any]:
    """Resolve only static, request-start target ability effects already owned by Q12."""
    result = {"ability_effect": None, "applied": [], "missing_inputs": [], "unsupported_reason": None, "authority_explicit": False}
    context = current.get("ability_context")
    if not isinstance(context, Mapping):
        if direct_defender.get("ability") == _KNOWN_ABSENT:
            return result
        if isinstance(direct_defender.get("ability"), Mapping) and direct_defender["ability"].get("status") == "known":
            result["unsupported_reason"] = "defender_ability_modifier"
        else:
            result["missing_inputs"].append("defender.ability")
        return result
    entries = context.get("current_abilities")
    if not isinstance(entries, list):
        result["missing_inputs"].append("defender.ability")
        return result
    target_entries = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == "opponent"]
    if not target_entries and direct_defender.get("ability") == _KNOWN_ABSENT:
        return result
    if len(target_entries) != 1:
        result["missing_inputs"].append("defender.ability")
        return result
    ability_id = target_entries[0].get("ability")
    if not _nonempty_str(ability_id) or ability_id == "unknown":
        result["missing_inputs"].append("defender.ability")
        return result
    result["authority_explicit"] = True
    if ability_id in _ACTION_ORDER_ONLY_ABILITIES or ability_id in _KNOWN_NO_DIRECT_DAMAGE_EFFECT_ABILITIES:
        return result
    if ability_id not in STATIC_DEFENDER_DAMAGE_ABILITIES:
        result["unsupported_reason"] = "defender_ability_modifier"
        return result
    effect = get_ability(ability_id)
    if effect is None:
        result["unsupported_reason"] = "defender_ability_modifier"
        return result
    applies = (
        (ability_id == "thick-fat" and move_type in {"fire", "ice"})
        or (ability_id == "fur-coat" and category == "physical")
        or (ability_id == "ice-scales" and category == "special")
        or (ability_id in {"filter", "solid-rock", "prism-armor"} and _nonempty_str(move_type) and type_effectiveness_multiplier(move_type, tuple(defender_types)) > 1)
        or (ability_id == "wonder-guard" and _nonempty_str(move_type) and type_effectiveness_multiplier(move_type, tuple(defender_types)) <= 1)
        or (ability_id in {"multiscale", "shadow-shield"})
    )
    if not applies:
        return result
    result["ability_effect"] = effect
    result["applied"].append(DEFENDER_ABILITY_MODIFIER_TAGS[ability_id])
    return result


def _attacker_item_modifier_context(*, stat_provenance: Mapping[str, Any], direct_attacker: Mapping[str, Any], category: Any, move_type: Any, defender_types: tuple[str, ...] | list[str]) -> dict[str, Any]:
    """Resolve only a request-start, user-confirmed self held item.

    The profile source is retained by the frozen snapshot so a UI default is
    never promoted to known absence.  Legacy direct contexts without an item
    profile retain their explicit known-absent compatibility path.
    """
    result = {"item_effect": None, "applied": [], "missing_inputs": [], "unsupported_reason": None}
    attacker = _mapping(stat_provenance.get("attacker"))
    item = _mapping(attacker.get("known_item"))
    status = item.get("status")
    profile_source = item.get("profile_source")
    if status == "known_absent":
        return result
    if status == "unknown":
        if profile_source is None and direct_attacker.get("item") == _KNOWN_ABSENT:
            return result
        if profile_source is None and isinstance(direct_attacker.get("item"), Mapping) and direct_attacker["item"].get("status") == "known":
            result["unsupported_reason"] = "item_modifier"
            return result
        result["missing_inputs"].append("attacker.item")
        return result
    if status != "known" or not _nonempty_str(item.get("value")):
        result["missing_inputs"].append("attacker.item")
        return result
    item_id = item["value"]
    if item_id not in STATIC_ATTACKER_DAMAGE_ITEMS:
        result["unsupported_reason"] = "item_modifier"
        return result
    effect = get_item(item_id)
    if effect is None:
        result["unsupported_reason"] = "item_modifier"
        return result
    if item_id == "expert-belt":
        effectiveness = type_effectiveness_multiplier(move_type, tuple(defender_types)) if _nonempty_str(move_type) else None
        if effectiveness is not None and effectiveness > 1:
            result["item_effect"] = effect
            result["applied"].append(ITEM_MODIFIER_TAGS[item_id])
        return result
    applies = (
        item_id == "life-orb"
        or (item_id in {"choice-band", "muscle-band"} and category == "physical")
        or (item_id in {"choice-specs", "wise-glasses"} and category == "special")
    )
    if not applies:
        return result
    result["item_effect"] = effect
    result["applied"].append(ITEM_MODIFIER_TAGS[item_id])
    return result


def _defender_item_modifier_context(
    *, stat_provenance: Mapping[str, Any], direct_defender: Mapping[str, Any], category: Any,
    move_type: Any, defender_types: tuple[str, ...] | list[str], hit_count: int,
) -> dict[str, Any]:
    """Resolve exact defender-owned Q12 items for the one prospective direct hit.

    A frozen exact held berry is current availability for this narrow evaluation;
    no consumption is projected beyond the hit being calculated.  Matching
    multi-hit berry triggers remain deliberately unsupported.
    """
    result = {"item_effect": None, "applied": [], "missing_inputs": [], "unsupported_reason": None}
    defender = _mapping(stat_provenance.get("defender"))
    item = _mapping(defender.get("known_item"))
    status = item.get("status")
    if status == "known_absent":
        return result
    if status is None and direct_defender.get("item") == _KNOWN_ABSENT:
        return result
    if status == "unknown":
        if item.get("profile_source") is None and direct_defender.get("item") == _KNOWN_ABSENT:
            return result
        if item.get("profile_source") is None and isinstance(direct_defender.get("item"), Mapping) and direct_defender["item"].get("status") == "known":
            result["unsupported_reason"] = "defender_item_modifier"
            return result
        result["missing_inputs"].append("defender.item")
        return result
    if status != "known" or not _nonempty_str(item.get("value")):
        result["missing_inputs"].append("defender.item")
        return result
    item_id = item["value"]
    effect = get_item(item_id)
    if effect is None:
        result["unsupported_reason"] = "defender_item_modifier"
        return result
    if effect.kind == "type_resist_berry":
        berry_type = effect.boosted_types[0] if len(effect.boosted_types) == 1 else None
        effectiveness = type_effectiveness_multiplier(move_type, tuple(defender_types)) if _nonempty_str(move_type) else None
        applies = (
            isinstance(berry_type, str)
            and move_type == berry_type
            and effectiveness is not None
            and (effectiveness > 0 if effect.always_resist else effectiveness > 1)
        )
        if not applies:
            return result
        if hit_count != 1:
            result["unsupported_reason"] = "defender_type_resist_berry_multi_hit"
            return result
        result["item_effect"] = effect
        result["applied"].append(
            DEFENDER_CHILAN_BERRY_TAG if item_id == "chilan-berry" else DEFENDER_TYPE_RESIST_BERRY_TAG
        )
        return result
    if item_id not in STATIC_DEFENDER_DAMAGE_ITEMS:
        result["unsupported_reason"] = "defender_item_modifier"
        return result
    if category == "special":
        result["item_effect"] = effect
        result["applied"].append(DEFENDER_ITEM_MODIFIER_TAGS[item_id])
    return result


def _item_authority_is_explicit(stat_provenance: Mapping[str, Any], side: str) -> bool:
    return _mapping(_mapping(stat_provenance.get(side)).get("known_item")).get("status") in {"known", "known_absent"}


def _facade_power_context(current: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Facade only from one exact attacker-owned current condition."""
    context = current.get("condition_context")
    entries = context.get("current_conditions") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return {"status": "insufficient_context", "missing_inputs": ["attacker.condition"]}
    matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == "self"]
    if len(matches) != 1:
        return {"status": "insufficient_context", "missing_inputs": ["attacker.condition"]}
    try:
        condition = normalize_user_confirmed_current_condition({key: value for key, value in matches[0].items() if key != "provenance"})["condition_type"]
    except ValueError:
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    boosted = condition in {"burn", "poison", "toxic", "paralysis"}
    return {
        "status": "known", "mechanic": "facade", "attacker_condition": condition,
        "effective_power": 140 if boosted else 70,
        "burn_attack_reduction_ignored": condition == "burn",
        "missing_inputs": [],
    }


def _current_hp_proportional_power_context(*, move_id: Any, direct_attacker: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve only the three canonical 150-power current-HP moves."""
    current, maximum = direct_attacker.get("current_hp"), direct_attacker.get("max_hp")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (current, maximum)):
        return {"status": "insufficient_context", "missing_inputs": ["attacker.current_hp", "attacker.max_hp"]}
    if maximum <= 0 or current < 0 or current > maximum:
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    if current == 0:
        return {"status": "not_applicable", "missing_inputs": []}
    return {
        "status": "known", "mechanic": "current_hp_proportional_power", "move": move_id,
        "attacker_current_hp": current, "attacker_maximum_hp": maximum,
        "effective_power": max(1, 150 * current // maximum),
        "rule": "current-hp-proportional-150", "missing_inputs": [],
    }


def _current_hp_bracket_power_context(*, move_id: Any, direct_attacker: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt the canonical Flail/Reversal resolver to the direct-Q12 seam."""
    current, maximum = direct_attacker.get("current_hp"), direct_attacker.get("max_hp")
    missing = []
    if isinstance(current, bool) or not isinstance(current, int):
        missing.append("attacker.current_hp")
    if isinstance(maximum, bool) or not isinstance(maximum, int):
        missing.append("attacker.max_hp")
    if missing:
        return {"status": "insufficient_context", "missing_inputs": missing}
    assessment = build_current_hp_based_power_assessment(
        {"move_id": move_id},
        {"current_hp": [{"side": "self", "current_hp": current, "maximum_hp": maximum}]},
    )
    if not isinstance(assessment, Mapping):
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    if assessment.get("status") == "resolved":
        return {
            "status": "known", "mechanic": "current_hp_bracket_power", "move": move_id,
            "attacker_current_hp": assessment["self_current_hp"], "attacker_maximum_hp": assessment["self_maximum_hp"],
            "effective_power": assessment["effective_power"], "rule": assessment["rule"], "missing_inputs": [],
        }
    if assessment.get("status") == "not_applicable":
        return {"status": "not_applicable", "missing_inputs": []}
    reason = assessment.get("reason")
    if reason == "missing_self_current_hp":
        return {"status": "insufficient_context", "missing_inputs": ["attacker.current_hp"]}
    if reason == "missing_self_maximum_hp":
        return {"status": "insufficient_context", "missing_inputs": ["attacker.max_hp"]}
    return {"status": "unsupported_mechanic", "missing_inputs": []}


def _brine_power_context(*, direct_defender: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Brine only from exact defender-owned current and maximum HP."""
    current, maximum = direct_defender.get("current_hp"), direct_defender.get("max_hp")
    missing = []
    if isinstance(current, bool) or not isinstance(current, int):
        missing.append("defender.current_hp")
    if isinstance(maximum, bool) or not isinstance(maximum, int):
        missing.append("defender.max_hp")
    if missing:
        return {"status": "insufficient_context", "missing_inputs": missing}
    if maximum <= 0 or current < 0 or current > maximum:
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    if current == 0:
        return {"status": "not_applicable", "missing_inputs": []}
    condition_met = current * 2 <= maximum
    return {
        "status": "known", "mechanic": "brine", "defender_current_hp": current,
        "defender_maximum_hp": maximum, "condition_met": condition_met,
        "effective_power": 130 if condition_met else 65,
        "rule": "opponent-half-hp-or-less-doubles-power", "missing_inputs": [],
    }


def _status_condition_power_context(*, move_id: str, current: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Hex and Venoshock only from one exact defender-owned condition."""
    context = current.get("condition_context")
    entries = context.get("current_conditions") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return {"status": "insufficient_context", "missing_inputs": ["defender.condition"]}
    matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == "opponent"]
    if len(matches) != 1:
        return {"status": "insufficient_context", "missing_inputs": ["defender.condition"]}
    try:
        condition = normalize_user_confirmed_current_condition({key: value for key, value in matches[0].items() if key != "provenance"})["condition_type"]
    except ValueError:
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    condition_met = condition != "none" if move_id == "hex" else condition in {"poison", "toxic"}
    rule = "defender-major-status-doubles-power" if move_id == "hex" else "defender-poison-doubles-power"
    return {
        "status": "known", "mechanic": "status_condition_power", "move": move_id,
        "defender_condition": condition, "condition_met": condition_met,
        "effective_power": 130 if condition_met else 65, "rule": rule,
        "missing_inputs": [],
    }


def _environment_transformation_context(*, move_id: str, current: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve field-changing move metadata from trusted current field authority."""
    context = current.get("field_state_context")
    field = context.get("current_field") if isinstance(context, Mapping) else None
    missing_name = "field.weather" if move_id == "weather-ball" else "field.terrain"
    if not isinstance(field, Mapping):
        return {"status": "insufficient_context", "missing_inputs": [missing_name]}
    if field.get("weather") == "unknown" or field.get("terrain") == "unknown":
        return {"status": "insufficient_context", "missing_inputs": [missing_name]}
    try:
        normalized = normalize_user_confirmed_current_field_state(field)
    except ValueError:
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    if move_id == "weather-ball":
        weather = normalized["weather"]
        types = {"sun": "fire", "rain": "water", "sandstorm": "rock", "snow": "ice"}
        transformed = weather in types
        return {
            "status": "known", "mechanic": "environment_transformation", "move": move_id,
            "weather": weather, "effective_type": types.get(weather, "normal"),
            "effective_power": 100 if transformed else 50, "transformed": transformed,
            "rule": "weather-ball-current-weather", "missing_inputs": [],
        }
    terrain = normalized["terrain"]
    if terrain == "none":
        return {
            "status": "known", "mechanic": "environment_transformation", "move": move_id,
            "terrain": terrain, "grounded": None, "effective_type": "normal", "effective_power": 50,
            "transformed": False, "rule": "terrain-pulse-current-terrain-and-groundedness", "missing_inputs": [],
        }
    grounded = _grounded_authority(current, "self")
    if grounded is None:
        return {"status": "insufficient_context", "missing_inputs": ["self.grounded"]}
    if grounded == "invalid":
        return {"status": "unsupported_mechanic", "missing_inputs": []}
    types = {"electric": "electric", "grassy": "grass", "misty": "fairy", "psychic": "psychic"}
    transformed = grounded is True
    return {
        "status": "known", "mechanic": "environment_transformation", "move": move_id,
        "terrain": terrain, "grounded": grounded, "effective_type": types[terrain] if transformed else "normal",
        "effective_power": 100 if transformed else 50, "transformed": transformed,
        "rule": "terrain-pulse-current-terrain-and-groundedness", "missing_inputs": [],
    }


def _turn_event_power_context(*, move_id: str, current: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve only a matching trusted same-turn observation predicate."""
    context = current.get("turn_event_context")
    if not isinstance(context, Mapping) or context.get("status") != "known" or context.get("projection_source") != "runtime_same_turn_event_projection" or not isinstance(context.get("turn_number"), int) or isinstance(context.get("turn_number"), bool):
        return {"status": "insufficient_context", "missing_inputs": ["same_turn_event"]}
    events = context.get("events")
    if not isinstance(events, list): return {"status": "unsupported_mechanic", "missing_inputs": []}
    predicate = "received_qualifying_direct_damage" if move_id in {"avalanche", "revenge"} else "acted_earlier_this_turn" if move_id == "payback" else "lost_hp_this_turn"
    expected_subject = "self" if move_id in {"avalanche", "revenge"} else "opponent"
    expected_target = "opponent" if expected_subject == "self" else "self"
    matches = [event for event in events if isinstance(event, Mapping) and event.get("session_id") == context.get("session_id") and event.get("turn_number") == context.get("turn_number") and event.get("predicate") == predicate and event.get("side") == expected_subject and event.get("target_side") == expected_target and isinstance(event.get("occurred"), bool) and _valid_same_turn_event_provenance(event.get("provenance"))]
    if len(matches) != 1:
        return {"status": "insufficient_context", "missing_inputs": ["same_turn_event"]}
    occurred = matches[0]["occurred"]
    base_power = 50 if move_id == "payback" else 60
    rule = "received-target-direct-damage-this-turn-doubles-power" if move_id in {"avalanche", "revenge"} else "target-acted-earlier-this-turn-doubles-power" if move_id == "payback" else "target-lost-hp-this-turn-doubles-power"
    return {"status": "known", "mechanic": "turn_event_power", "move": move_id, "predicate": predicate, "occurred": occurred, "effective_power": base_power * (2 if occurred else 1), "rule": rule, "missing_inputs": []}


def _valid_same_turn_event_provenance(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == "same_turn_event_observed" and value.get("trust") == "user_confirmed_observation"


def _modifier_context(*, current: Mapping[str, Any], direct: Mapping[str, Any], category: Any, move_type: Any, defender_types: tuple[str, ...] | list[str] = (), ignore_burn_attack_reduction: bool = False) -> dict[str, Any]:
    """Adapt only explicit request-start weather, burn, and target screens."""
    result = {"field": Field(is_doubles=False), "burn_mod_q12": Q12_ONE, "applied": [], "missing_inputs": [], "unsupported_reason": None, "weather_known": False, "burn_known": False, "terrain_known": False, "attacker_grounded": None, "defender_grounded": None}
    field_context = _mapping(current.get("field_state_context"))
    field_state = _mapping(field_context.get("current_field"))
    has_field_snapshot = isinstance(current.get("field_state_context"), Mapping)
    weather = field_state.get("weather")
    if weather in {"none", "rain", "sun", "sandstorm", "snow"}:
        result["field"] = Field(weather="sand" if weather == "sandstorm" else weather, is_doubles=False); result["weather_known"] = True
        if move_type == "water" and weather == "rain": result["applied"].append("rain_water_boost")
        if move_type == "fire" and weather == "rain": result["applied"].append("rain_fire_reduction")
        if move_type == "fire" and weather == "sun": result["applied"].append("sun_fire_boost")
        if move_type == "water" and weather == "sun": result["applied"].append("sun_water_reduction")
        if weather == "sandstorm" and category == "special" and "rock" in defender_types:
            result["applied"].append("sandstorm_rock_special_defense_boost")
        if weather == "snow" and category == "physical" and "ice" in defender_types:
            result["applied"].append("snow_ice_defense_boost")
    elif weather in {None, "unknown"}:
        if move_type in {"water", "fire"}: result["missing_inputs"].append("field.weather")
    else: result["unsupported_reason"] = "weather_modifier"
    terrain = field_state.get("terrain")
    terrain_types = {"electric": ("electric", "attacker_grounded", "terrain_electric_boost"), "grassy": ("grass", "attacker_grounded", "terrain_grassy_boost"), "psychic": ("psychic", "attacker_grounded", "terrain_psychic_boost"), "misty": ("dragon", "defender_grounded", "terrain_misty_dragon_reduction")}
    if terrain == "none":
        result["terrain_known"] = True
    elif terrain in terrain_types:
        result["terrain_known"] = True
        required_type, grounded_key, tag = terrain_types[terrain]
        if move_type == required_type:
            grounded = _grounded_authority(current, "self" if grounded_key == "attacker_grounded" else "opponent")
            if grounded == "invalid": result["unsupported_reason"] = "grounded_context"
            elif grounded is None: result["missing_inputs"].append("self.grounded" if grounded_key == "attacker_grounded" else "opponent.grounded")
            else:
                result[grounded_key] = grounded
                if grounded: result["applied"].append(tag)
        result["field"] = Field(weather=result["field"].weather, terrain=terrain, is_doubles=False)
    elif terrain in {None, "unknown"}:
        if _mapping(direct.get("field")).get("terrain") == _KNOWN_ABSENT and (not has_field_snapshot or "terrain" not in field_state):
            result["terrain_known"] = True
        elif move_type in {"electric", "grass", "psychic", "dragon"}: result["missing_inputs"].append("field.terrain")
    else: result["unsupported_reason"] = "terrain_modifier"
    conditions = _mapping(current.get("condition_context")).get("current_conditions")
    if isinstance(conditions, list):
        own = [x for x in conditions if isinstance(x, Mapping) and x.get("side") == "self"]
        if category == "physical":
            if not own or own[0].get("condition_type") == "unknown": result["missing_inputs"].append("attacker.condition")
            elif own[0].get("condition_type") == "burn":
                if not ignore_burn_attack_reduction:
                    result["burn_mod_q12"] = M_HALF; result["applied"].append("burn_physical_reduction")
                result["burn_known"] = True
            else: result["burn_known"] = True
    elif not has_field_snapshot and _mapping(direct.get("attacker")).get("status") == _KNOWN_ABSENT:
        result["burn_known"] = True
    elif category == "physical":
        result["missing_inputs"].append("attacker.condition")
    # The legacy direct context predates request-start field snapshots.  Keep
    # that explicit known-absent compatibility path, but never treat a present
    # snapshot with omitted/ambiguous side ownership as an inactive screen.
    if has_field_snapshot:
        effects = field_state.get("side_effects")
        screen = "reflect" if category == "physical" else "light-screen"
        if not isinstance(effects, list):
            result["missing_inputs"].append("target_side_conditions")
        else:
            target_screen = False
            ambiguous_screen = False
            for effect in effects:
                if not isinstance(effect, Mapping):
                    ambiguous_screen = True
                    continue
                effect_name, side = effect.get("effect"), effect.get("side")
                if effect_name == screen:
                    if side == "opponent":
                        target_screen = True
                    elif side != "self":
                        ambiguous_screen = True
            if ambiguous_screen:
                result["missing_inputs"].append("target_side_conditions")
            elif target_screen:
                fmt = _mapping(_mapping(current.get("battle_format_context")).get("current_battle_format")).get("battle_format")
                if fmt == "singles":
                    result["field"] = Field(
                        weather=result["field"].weather, terrain=result["field"].terrain, is_doubles=False,
                        defender_side=SideField(
                            reflect=screen == "reflect",
                            light_screen=screen == "light-screen",
                        ),
                    )
                    result["applied"].append("reflect_reduction" if screen == "reflect" else "light_screen_reduction")
                elif fmt in {None, "unknown"}:
                    result["missing_inputs"].append("battle_format")
                else:
                    result["unsupported_reason"] = "battle_format"
    return result


def _grounded_authority(current: Mapping[str, Any], side: str) -> bool | None | str:
    context = current.get("grounded_context")
    entry = context.get(side) if isinstance(context, Mapping) else None
    if not isinstance(entry, Mapping): return None
    status, provenance = entry.get("status"), entry.get("provenance")
    if status == "known_grounded" and provenance == "user_confirmed_current": return True
    if status == "known_ungrounded" and provenance == "user_confirmed_current": return False
    if status == "unknown" and provenance == "unknown": return None
    return "invalid"


def _available(value: Any) -> Any:
    return value.get("value") if isinstance(value, Mapping) and value.get("available") is True else None


def _stat_block(value: Mapping[str, Any]) -> StatBlock:
    if any(not _positive_int(value[key]) for key in _STAT_KEYS): raise ValueError("invalid stats")
    return StatBlock(hp=value["hp"], atk=value["attack"], def_=value["defense"], spa=value["special-attack"], spd=value["special-defense"], spe=value["speed"])


def _mapping(value: Any) -> Mapping[str, Any]: return value if isinstance(value, Mapping) else {}
def _nonempty_str(value: Any) -> bool: return isinstance(value, str) and bool(value)
def _positive_int(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value > 0
def _valid_level(value: Any) -> bool: return _positive_int(value) and value <= 100


def _insufficient(missing: list[str]) -> dict[str, Any]:
    return {"status": "insufficient_context", "move": None, "type_effectiveness": None, "damage_range": None, "damage_percent_range": None, "ko_result": None, "missing_inputs": sorted(set(missing)), "unsupported_reason": None, "mechanics_source": "native_q12_direct_damage", "generation": None}


def _unsupported(reason: str) -> dict[str, Any]:
    return {"status": "unsupported_mechanic", "move": None, "type_effectiveness": None, "damage_range": None, "damage_percent_range": None, "ko_result": None, "missing_inputs": [], "unsupported_reason": reason, "mechanics_source": "native_q12_direct_damage", "generation": None}


def _fixed_insufficient(missing: list[str]) -> dict[str, Any]:
    return {"status": "insufficient_context", "move": None, "damage_model": "level_based_fixed", "fixed_damage": None, "type_effectiveness": None, "damage_range": None, "damage_percent_range": None, "ko_result": None, "missing_inputs": sorted(set(missing)), "unsupported_reason": None, "mechanics_source": "native_level_based_fixed_damage", "generation": None}


def _fixed_unsupported(reason: str) -> dict[str, Any]:
    return {"status": "unsupported_mechanic", "move": None, "damage_model": "level_based_fixed", "fixed_damage": None, "type_effectiveness": None, "damage_range": None, "damage_percent_range": None, "ko_result": None, "missing_inputs": [], "unsupported_reason": reason, "mechanics_source": "native_level_based_fixed_damage", "generation": None}
# These abilities are explicitly catalogued as having no direct-damage formula
# modifier.  They remain known identities rather than being represented as an
# invented absence authority.
_KNOWN_NO_DIRECT_DAMAGE_EFFECT_ABILITIES = frozenset({"pressure"})
_ACTION_ORDER_ONLY_ABILITIES = frozenset({"prankster", "gale-wings", "triage", "sturdy"})
