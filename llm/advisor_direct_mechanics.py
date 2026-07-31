"""Unknown-first direct-damage mechanics slice over the native Q12 engine."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from collections import Counter
from typing import Any

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.stats import StatBlock
from advisor.damage.types import type_effectiveness_multiplier
from advisor.probability.single_hit import ko_chance_from_outcomes
from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY


_STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
_BOOST_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed")
_KNOWN_ABSENT = {"status": "known_absent"}


def evaluate_direct_damage_mechanics(
    snapshot_damage_input: Mapping[str, Any], *, stat_provenance: Mapping[str, Any],
    trusted_level: int | None,
) -> dict[str, Any]:
    """Return bounded public mechanics evidence without inventing battle facts.

    Only one normal, non-critical, single-hit, non-dynamic damaging move is in
    scope. The caller supplies its existing frozen snapshot damage input and
    provenance. `direct_mechanics_context` is deliberately explicit: omitted
    facts are reported as logical missing names instead of becoming defaults.
    """
    missing: list[str] = []
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
    category, power, move_type = move.get("category"), move.get("power"), move.get("type")
    if category == "status":
        return _unsupported("status_move")
    if move_id in DYNAMIC_MOVE_ASSESSMENT_REGISTRY:
        return _unsupported("dynamic_base_power")
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
    if not _valid_level(trusted_level):
        missing.append("attacker.level")
    direct_attacker = _mapping(direct.get("attacker"))
    direct_defender = _mapping(direct.get("defender"))
    modifier_reason = _unsupported_modifier(direct_attacker, direct_defender, _mapping(direct.get("field")))
    if modifier_reason is not None:
        return _unsupported(modifier_reason)
    for side_name, side in (("attacker", direct_attacker), ("defender", direct_defender)):
        _require_known_absent(side.get("ability"), f"{side_name}.ability", missing)
        _require_known_absent(side.get("item"), f"{side_name}.item", missing)
        _require_zero_boosts(side.get("boosts"), f"{side_name}.boosts", missing)
        _require_hp(side, side_name, missing)
        _require_known_absent(side.get("status"), f"{side_name}.status", missing)
    field = _mapping(direct.get("field"))
    _require_known_absent(field.get("weather"), "field.weather", missing)
    _require_known_absent(field.get("terrain"), "field.terrain", missing)
    if missing:
        return _insufficient(missing)
    assert attacker is not None and defender is not None and isinstance(trusted_level, int)
    try:
        attacker_stats = _stat_block(attacker["final_stats"])
        defender_stats = _stat_block(defender["final_stats"])
        is_physical = category == "physical"
        rolls = calc_damage_rolls(DamageContext(
            attacker_level=trusted_level, move_power=power,  # type: ignore[arg-type]
            attack_stat=attacker_stats.atk if is_physical else attacker_stats.spa,
            defense_stat=defender_stats.def_ if is_physical else defender_stats.spd,
            move_type=move_type, attacker_types=tuple(attacker["types"]),
            defender_types=tuple(defender["types"]), is_physical=is_physical,
            is_critical=False, is_spread=False, move_id=move_id,
            attacker_species=attacker["pokemon_identity"], defender_species=defender["pokemon_identity"],
            attacker_stats=attacker_stats, defender_stats=defender_stats,
        ))
    except (TypeError, ValueError, KeyError):
        return _unsupported("native_direct_damage")
    defender_hp = direct_defender["current_hp"]
    max_hp = direct_defender["max_hp"]
    total_counts = Counter({0: 1})
    for _ in range(hit_count):
        total_counts = _convolve_roll_counts(total_counts, Counter(rolls))
    total_rolls = tuple(value for value, count in total_counts.items() for _ in range(count))
    return {
        "status": "known", "move": move_id, "type_effectiveness": type_effectiveness_multiplier(move_type, tuple(defender["types"])),
        "hit_count": hit_count, "per_hit_damage_range": {"minimum": min(rolls), "maximum": max(rolls)},
        "damage_range": {"minimum": min(total_rolls), "maximum": max(total_rolls)},
        "damage_percent_range": {"minimum": round(min(total_rolls) * 100 / max_hp, 2), "maximum": round(max(total_rolls) * 100 / max_hp, 2)},
        "ko_result": {"status": "resolved", "single_hit_probability": float(ko_chance_from_outcomes(total_rolls, defender_hp))},
        "missing_inputs": [], "unsupported_reason": None,
        "mechanics_source": "native_q12_direct_damage", "generation": generation,
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
    if not isinstance(types, list) or not types or not all(_nonempty_str(item) for item in types): missing.append(f"{side}.types")
    stats = _available(value.get("final_stats"))
    if not isinstance(stats, Mapping) or set(stats) != set(_STAT_KEYS): missing.append(f"{side}.final_stats")
    return {"pokemon_identity": identity, "types": types, "final_stats": stats}


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
