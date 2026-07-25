"""Pure snapshot-to-Q12 invocation boundary; it never changes Q12 formulas."""
from __future__ import annotations

from typing import Any, Mapping

from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.stats import StatBlock
from llm.advisor_turn_snapshot import build_q12_input_adapter


_STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


def invoke_existing_q12_from_snapshot(
    snapshot_damage_input: Mapping[str, Any], *, stat_provenance: Mapping[str, Any],
    trusted_level: int | None,
) -> dict[str, Any]:
    """Call the existing Q12 boundary only after snapshot readiness succeeds."""
    try:
        ready = build_q12_input_adapter(snapshot_damage_input, stat_provenance=stat_provenance)
    except ValueError:
        return _unavailable("invalid_snapshot_input")
    if ready.get("status") != "ready_for_existing_q12_boundary":
        return _unavailable(str(ready.get("reason", "q12_input_unavailable")))
    if not _ready_signature_matches_snapshot(ready, snapshot_damage_input):
        return _unavailable("invalid_snapshot_identity")
    if isinstance(trusted_level, bool) or not isinstance(trusted_level, int) or not 1 <= trusted_level <= 100:
        return _unavailable("trusted_level_unavailable")
    move = ready.get("move")
    if not isinstance(move, Mapping):
        return _unavailable("invalid_move_metadata")
    category = move.get("category")
    if category == "status":
        return _unavailable("status_move_not_damaging")
    if category not in {"physical", "special"}:
        return _unavailable("invalid_move_category")
    power, move_type = move.get("power"), move.get("type")
    if isinstance(power, bool) or not isinstance(power, int) or power < 1 or not isinstance(move_type, str) or not move_type:
        return _unavailable("invalid_move_metadata")
    try:
        attacker = _q12_side(ready.get("attacker"))
        defender = _q12_side(ready.get("defender"))
        attacker_stats = _stat_block(attacker["final_stats"]["value"])
        defender_stats = _stat_block(defender["final_stats"]["value"])
        is_physical = category == "physical"
        attack_stat = attacker_stats.atk if is_physical else attacker_stats.spa
        defense_stat = defender_stats.def_ if is_physical else defender_stats.spd
        context = DamageContext(
            attacker_level=trusted_level,
            move_power=power,
            attack_stat=attack_stat,
            defense_stat=defense_stat,
            move_type=move_type,
            move_id=str(move.get("move_id", "")),
            attacker_types=tuple(attacker["types"]["value"]),
            defender_types=tuple(defender["types"]["value"]),
            is_physical=is_physical,
            is_critical=False,
            is_spread=False,
            field=Field(is_doubles=False),
            attacker_species=str(attacker["pokemon_identity"]),
            defender_species=str(defender["pokemon_identity"]),
            attacker_stats=attacker_stats,
            defender_stats=defender_stats,
        )
        rolls = calc_damage_rolls(context)
    except Exception:
        return _unavailable("q12_calculation_failed")
    return {
        "status": "resolved",
        "candidate_move_id": move["move_id"],
        "candidate_move_slot": move.get("slot_index"),
        "damage_rolls": list(rolls),
        "min_damage": min(rolls),
        "max_damage": max(rolls),
        "current_hp": None,
        "ko_context": None,
        "limitations": [
            "Only trusted final stats, repository types, and move metadata were supplied.",
            "Stat stages, ability/item modifiers, weather, terrain, field effects, and observed events are not applied by this adapter.",
        ],
    }


def _q12_side(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_q12_side")
    if not isinstance(value.get("pokemon_identity"), str):
        raise ValueError("invalid_q12_side")
    types = value.get("types")
    if not isinstance(types, Mapping) or not isinstance(types.get("value"), list):
        raise ValueError("invalid_q12_side")
    if not all(isinstance(item, str) and item for item in types["value"]):
        raise ValueError("invalid_q12_side")
    return value


def _ready_signature_matches_snapshot(ready: Mapping[str, Any], damage_input: Mapping[str, Any]) -> bool:
    """Reject a tampered adapter input before the legacy formula is reached."""
    attacker = ready.get("attacker")
    defender = ready.get("defender")
    move = ready.get("move")
    input_attacker = damage_input.get("attacker")
    input_defender = damage_input.get("defender")
    if not all(isinstance(value, Mapping) for value in (attacker, defender, move, input_attacker, input_defender)):
        return False
    attacker_id = attacker.get("pokemon_identity")
    defender_id = defender.get("pokemon_identity")
    if not isinstance(attacker_id, str) or not isinstance(defender_id, str):
        return False
    return (
        input_attacker.get("species_id") == attacker_id
        and input_defender.get("species_id") == defender_id
        and move.get("owner_species_id") == attacker_id
        and isinstance(move.get("move_id"), str)
        and bool(move.get("move_id"))
        and isinstance(move.get("slot_index"), int)
        and not isinstance(move.get("slot_index"), bool)
        and move["slot_index"] >= 0
    )


def _stat_block(values: Any) -> StatBlock:
    if not isinstance(values, Mapping) or set(values) != set(_STAT_KEYS):
        raise ValueError("invalid_final_stats")
    normalized = {key: values[key] for key in _STAT_KEYS}
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in normalized.values()):
        raise ValueError("invalid_final_stats")
    return StatBlock(
        hp=normalized["hp"], atk=normalized["attack"], def_=normalized["defense"],
        spa=normalized["special-attack"], spd=normalized["special-defense"], spe=normalized["speed"],
    )


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "candidate_move_id": None,
        "candidate_move_slot": None,
        "damage_rolls": [],
        "min_damage": None,
        "max_damage": None,
        "current_hp": None,
        "ko_context": None,
        "limitations": [reason],
    }
