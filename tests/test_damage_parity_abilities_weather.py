from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.abilities import get_ability
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.grounded import GroundedInputs
from advisor.damage.items import get_item
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
    "earthquake": ("ground", "physical", 100, "allAdjacent"),
    "flamethrower": ("fire", "special", 90, "normal"),
    "ice-beam": ("ice", "special", 90, "normal"),
    "iron-head": ("steel", "physical", 80, "normal"),
    "moonblast": ("fairy", "special", 95, "normal"),
    "rock-slide": ("rock", "physical", 75, "allAdjacentFoes"),
    "scratch": ("normal", "physical", 40, "normal"),
    "shadow-ball": ("ghost", "special", 80, "normal"),
    "tackle": ("normal", "physical", 40, "normal"),
    "thunderbolt": ("electric", "special", 90, "normal"),
    "water-gun": ("water", "special", 40, "normal"),
}

OVERRIDES = {
    "cherrim": {"types": ["grass"], "base_stats": {"hp": 70, "atk": 60, "def": 70, "spa": 87, "spd": 78, "spe": 85}},
    "gogoat": {"types": ["grass"], "base_stats": {"hp": 123, "atk": 100, "def": 62, "spa": 97, "spd": 81, "spe": 68}},
    "great-tusk": {"types": ["ground", "fighting"], "base_stats": {"hp": 115, "atk": 131, "def": 131, "spa": 53, "spd": 53, "spe": 87}},
    "iron-bundle": {"types": ["ice", "water"], "base_stats": {"hp": 56, "atk": 80, "def": 114, "spa": 124, "spd": 60, "spe": 136}},
    "iron-moth": {"types": ["fire", "poison"], "base_stats": {"hp": 80, "atk": 70, "def": 60, "spa": 140, "spd": 110, "spe": 110}},
    "flutter-mane": {"types": ["ghost", "fairy"], "base_stats": {"hp": 55, "atk": 55, "def": 55, "spa": 135, "spd": 135, "spe": 135}},
}


def _request(
    attacker: str,
    defender: str,
    move: str,
    *,
    attacker_ability: str | None = None,
    defender_ability: str | None = None,
    attacker_item: str | None = None,
    defender_item: str | None = None,
    weather: str | None = None,
    terrain: str | None = None,
    boosted_stat: str | None = None,
    format_: str = "gen9ou",
) -> dict:
    return {
        "schema_version": "v1",
        "attacker": {
            "species": attacker,
            "level": 50,
            "ability": attacker_ability,
            "item": attacker_item,
            "nature": "hardy",
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": None,
            "is_terastallized": False,
            "boosted_stat": boosted_stat,
        },
        "defender": {
            "species": defender,
            "level": 50,
            "ability": defender_ability,
            "item": defender_item,
            "nature": "hardy",
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": None,
            "is_terastallized": False,
            "boosted_stat": None,
            "current_hp_pct": 100,
        },
        "move": {"name": move, "is_critical": False, "is_z": False, "is_max": False},
        "field": {
            "weather": weather,
            "terrain": terrain,
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
    attack_stat = apply_boosts(
        attack_stat,
        request.attacker.boosts.atk if category == "physical" else request.attacker.boosts.spa,
    )
    defense_stat = apply_boosts(
        defense_stat,
        request.defender.boosts.def_ if category == "physical" else request.defender.boosts.spd,
    )
    field = Field(
        weather=request.field.weather or "none",
        terrain=request.field.terrain or "none",
        is_doubles=request.field.format == "gen9doubles",
    )
    attacker_boosts = _boost_block(request.attacker.boosts)
    defender_boosts = _boost_block(request.defender.boosts)

    return DamageContext(
        attacker_level=request.attacker.level,
        move_power=power,
        attack_stat=attack_stat,
        defense_stat=defense_stat,
        move_type=move_type,
        move_id=request.move.name,
        attacker_types=tuple(attacker_data["types"]),
        defender_types=tuple(defender_data["types"]),
        is_physical=category == "physical",
        is_critical=request.move.is_critical,
        is_spread=field.is_doubles and target in {"allAdjacent", "allAdjacentFoes"},
        field=field,
        attacker_grounded_inputs=GroundedInputs(tuple(attacker_data["types"])),
        defender_grounded_inputs=GroundedInputs(tuple(defender_data["types"])),
        attacker_item=get_item(request.attacker.item),
        defender_item=get_item(request.defender.item),
        attacker_species=request.attacker.species,
        defender_species=request.defender.species,
        attacker_ability=get_ability(request.attacker.ability),
        defender_ability=get_ability(request.defender.ability),
        attacker_stats=attacker_stats,
        defender_stats=defender_stats,
        attacker_boosts=attacker_boosts,
        defender_boosts=defender_boosts,
        attacker_booster_active=request.attacker.item == "booster-energy",
        defender_booster_active=request.defender.item == "booster-energy",
        attacker_locked_paradox_stat=None
        if request.attacker.boosted_stat in (None, "auto")
        else request.attacker.boosted_stat,
        defender_locked_paradox_stat=None
        if request.defender.boosted_stat in (None, "auto")
        else request.defender.boosted_stat,
    )


def _stats_for(pokemon, base_stats: dict[str, int]) -> StatBlock:
    nature_plus, nature_minus = nature_from_name(pokemon.nature)
    return final_stats(
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


def _boost_block(boosts) -> StatBlock:
    return StatBlock(hp=0, atk=boosts.atk, def_=boosts.def_, spa=boosts.spa, spd=boosts.spd, spe=boosts.spe)


def _load_entity(entity_id: str) -> dict:
    path = CACHE_DIR / f"{entity_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return OVERRIDES[entity_id]


CASES = [
    ("cloud_nine_negates_sun_fire", _request("charizard", "pikachu", "flamethrower", attacker_ability="cloud-nine", weather="sun")),
    ("air_lock_negates_rain_water", _request("blastoise", "charizard", "water-gun", attacker_ability="air-lock", weather="rain")),
    ("cloud_nine_solar_power_inactive", _request("charizard", "pikachu", "flamethrower", attacker_ability="solar-power", defender_ability="cloud-nine", weather="sun")),
    ("sand_force_rock", _request("garchomp", "pikachu", "rock-slide", attacker_ability="sand-force", weather="sand")),
    ("sand_force_ground", _request("garchomp", "pikachu", "earthquake", attacker_ability="sand-force", weather="sand")),
    ("sand_force_steel", _request("garchomp", "pikachu", "iron-head", attacker_ability="sand-force", weather="sand")),
    ("sand_force_normal_no_boost", _request("garchomp", "pikachu", "scratch", attacker_ability="sand-force", weather="sand")),
    ("sand_force_no_sand_no_boost", _request("garchomp", "pikachu", "earthquake", attacker_ability="sand-force")),
    ("solar_power_sun", _request("charizard", "pikachu", "flamethrower", attacker_ability="solar-power", weather="sun")),
    ("solar_power_no_sun", _request("charizard", "pikachu", "flamethrower", attacker_ability="solar-power")),
    ("flower_gift_cherrim", _request("cherrim", "pikachu", "tackle", attacker_ability="flower-gift", weather="sun")),
    ("grass_pelt_defense", _request("pikachu", "gogoat", "tackle", defender_ability="grass-pelt", terrain="grassy")),
    ("protosynthesis_atk", _request("great-tusk", "pikachu", "earthquake", attacker_ability="protosynthesis", weather="sun", boosted_stat="auto")),
    ("quark_drive_spa", _request("iron-moth", "pikachu", "flamethrower", attacker_ability="quark-drive", terrain="electric", boosted_stat="auto")),
    ("protosynthesis_booster_locked_spa", _request("flutter-mane", "pikachu", "shadow-ball", attacker_ability="protosynthesis", attacker_item="booster-energy", boosted_stat="spa")),
    ("sand_force_life_orb", _request("garchomp", "pikachu", "earthquake", attacker_ability="sand-force", attacker_item="life-orb", weather="sand")),
]


@pytest.mark.parametrize(("case_name", "request_data"), CASES)
def test_damage_parity_abilities_weather(case_name: str, request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_damage_rolls(_context_from_request(request))

    assert py_rolls == js_response.damage_rolls, (
        f"{case_name}: Python {py_rolls} != JS {js_response.damage_rolls}"
    )
