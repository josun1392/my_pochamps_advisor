from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.stats import (
    StatBlock,
    StatInputs,
    apply_boosts,
    final_stats,
    nature_from_name,
)
from advisor.parity.bridge import call_smogon_calc
from advisor.parity.schemas import DamageRequest


CACHE_DIR = Path("data/cache/pokemon")

MOVES = {
    "tackle": ("normal", "physical", 40, "normal"),
    "scratch": ("normal", "physical", 40, "normal"),
    "flamethrower": ("fire", "special", 90, "normal"),
    "ember": ("fire", "special", 40, "normal"),
    "water-gun": ("water", "special", 40, "normal"),
    "shadow-ball": ("ghost", "special", 80, "normal"),
    "ice-beam": ("ice", "special", 90, "normal"),
    "thunderbolt": ("electric", "special", 90, "normal"),
    "earthquake": ("ground", "physical", 100, "allAdjacent"),
}


def _request(
    attacker: str,
    defender: str,
    move: str,
    *,
    level: int = 50,
    attacker_nature: str = "hardy",
    defender_nature: str = "hardy",
    is_critical: bool = False,
    format_: str = "gen9ou",
) -> dict:
    return {
        "schema_version": "v1",
        "attacker": {
            "species": attacker,
            "level": level,
            "ability": None,
            "item": None,
            "nature": attacker_nature,
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": None,
            "is_terastallized": False,
        },
        "defender": {
            "species": defender,
            "level": level,
            "ability": None,
            "item": None,
            "nature": defender_nature,
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": None,
            "is_terastallized": False,
            "current_hp_pct": 100,
        },
        "move": {
            "name": move,
            "is_critical": is_critical,
            "is_z": False,
            "is_max": False,
        },
        "field": {
            "weather": None,
            "terrain": None,
            "is_gravity": False,
            "is_trick_room": False,
            "format": format_,
        },
    }


def _context_from_request(request: DamageRequest) -> DamageContext:
    move_type, category, power, target = MOVES[request.move.name]
    attacker_data = _load_entity(request.attacker.species)
    defender_data = _load_entity(request.defender.species)
    attacker_stats = _stats_for(request.attacker, attacker_data["base_stats"])
    defender_stats = _stats_for(request.defender, defender_data["base_stats"])
    attack_stat = attacker_stats.atk if category == "physical" else attacker_stats.spa
    defense_stat = defender_stats.def_ if category == "physical" else defender_stats.spd
    attack_stat = apply_boosts(attack_stat, _attack_boost(request.attacker.boosts, category))
    defense_stat = apply_boosts(defense_stat, _defense_boost(request.defender.boosts, category))

    return DamageContext(
        attacker_level=request.attacker.level,
        move_power=power,
        attack_stat=attack_stat,
        defense_stat=defense_stat,
        move_type=move_type,
        attacker_types=tuple(attacker_data["types"]),
        defender_types=tuple(defender_data["types"]),
        is_physical=category == "physical",
        is_critical=request.move.is_critical,
        is_spread=request.field.format == "gen9doubles"
        and target in {"allAdjacent", "allAdjacentFoes"},
    )


def _stats_for(pokemon, base_stats: dict[str, int]) -> StatBlock:
    nature_plus, nature_minus = nature_from_name(pokemon.nature)
    stats = final_stats(
        StatInputs(
            base=StatBlock(
                hp=base_stats["hp"],
                atk=base_stats["atk"],
                def_=base_stats["def"],
                spa=base_stats["spa"],
                spd=base_stats["spd"],
                spe=base_stats["spe"],
            ),
            evs=StatBlock(
                hp=pokemon.evs.hp,
                atk=pokemon.evs.atk,
                def_=pokemon.evs.def_,
                spa=pokemon.evs.spa,
                spd=pokemon.evs.spd,
                spe=pokemon.evs.spe,
            ),
            ivs=StatBlock(
                hp=pokemon.ivs.hp,
                atk=pokemon.ivs.atk,
                def_=pokemon.ivs.def_,
                spa=pokemon.ivs.spa,
                spd=pokemon.ivs.spd,
                spe=pokemon.ivs.spe,
            ),
            nature_plus=nature_plus,
            nature_minus=nature_minus,
            level=pokemon.level,
            rule_set="gen9",
        )
    )
    return stats


def _attack_boost(boosts, category: str) -> int:
    if category == "physical":
        return boosts.atk
    return boosts.spa if category == "special" else 0


def _defense_boost(boosts, category: str) -> int:
    if category == "physical":
        return boosts.def_
    return boosts.spd if category == "special" else 0


def _load_entity(entity_id: str) -> dict:
    return json.loads((CACHE_DIR / f"{entity_id}.json").read_text(encoding="utf-8"))


CASES = [
    ("vanilla_normal_move", _request("pikachu", "charizard", "scratch", attacker_nature="hardy")),
    ("stab_only", _request("charizard", "pikachu", "flamethrower", attacker_nature="modest")),
    ("super_effective", _request("blastoise", "charizard", "water-gun", attacker_nature="modest")),
    ("resisted", _request("blastoise", "venusaur", "water-gun", attacker_nature="modest")),
    ("immune", _request("pikachu", "gengar", "tackle", attacker_nature="hardy")),
    ("four_x_weakness", _request("blastoise", "garchomp", "ice-beam", attacker_nature="modest")),
    (
        "critical_hit",
        _request("charizard", "venusaur", "flamethrower", attacker_nature="modest", is_critical=True),
    ),
    (
        "spread_doubles",
        _request(
            "garchomp",
            "pikachu",
            "earthquake",
            attacker_nature="adamant",
            defender_nature="hardy",
            format_="gen9doubles",
        ),
    ),
    ("low_level", _request("pikachu", "charizard", "thunderbolt", level=5)),
    ("high_level", _request("charizard", "venusaur", "ember", level=100)),
]


@pytest.mark.parametrize(("case_name", "request_data"), CASES)
def test_damage_parity(case_name: str, request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_damage_rolls(_context_from_request(request))

    assert py_rolls == js_response.damage_rolls, (
        f"{case_name}: Python {py_rolls} != JS {js_response.damage_rolls}"
    )
