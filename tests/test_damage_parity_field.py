from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.field import Field, SideField
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.grounded import GroundedInputs
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
    "dragon-pulse": ("dragon", "special", 85, "normal"),
    "earthquake": ("ground", "physical", 100, "allAdjacent"),
    "ember": ("fire", "special", 40, "normal"),
    "energy-ball": ("grass", "special", 90, "normal"),
    "flamethrower": ("fire", "special", 90, "normal"),
    "hydro-pump": ("water", "special", 110, "normal"),
    "ice-beam": ("ice", "special", 90, "normal"),
    "iron-head": ("steel", "physical", 80, "normal"),
    "outrage": ("dragon", "physical", 120, "normal"),
    "psychic": ("psychic", "special", 90, "normal"),
    "thunderbolt": ("electric", "special", 90, "normal"),
    "water-gun": ("water", "special", 40, "normal"),
}


def _request(
    attacker: str,
    defender: str,
    move: str,
    *,
    weather: str | None = None,
    terrain: str | None = None,
    format_: str = "gen9ou",
    is_critical: bool = False,
    defender_side: dict | None = None,
    tera_type: str | None = None,
) -> dict:
    return {
        "schema_version": "v1",
        "attacker": {
            "species": attacker,
            "level": 50,
            "ability": None,
            "item": None,
            "nature": "hardy",
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": tera_type,
            "is_terastallized": tera_type is not None,
        },
        "defender": {
            "species": defender,
            "level": 50,
            "ability": None,
            "item": None,
            "nature": "hardy",
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": None,
            "is_terastallized": False,
            "current_hp_pct": 100,
        },
        "move": {"name": move, "is_critical": is_critical, "is_z": False, "is_max": False},
        "field": {
            "weather": weather,
            "terrain": terrain,
            "is_gravity": False,
            "is_trick_room": False,
            "format": format_,
            "defender_side": defender_side,
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
    attack_stat = apply_boosts(attack_stat, request.attacker.boosts.atk if category == "physical" else request.attacker.boosts.spa)
    defense_stat = apply_boosts(defense_stat, request.defender.boosts.def_ if category == "physical" else request.defender.boosts.spd)
    field = _field_from_request(request)

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
        attacker_grounded_inputs=GroundedInputs(
            tuple(attacker_data["types"]),
            ability=request.attacker.ability,
            item=request.attacker.item,
        ),
        defender_grounded_inputs=GroundedInputs(
            tuple(defender_data["types"]),
            ability=request.defender.ability,
            item=request.defender.item,
        ),
        attacker_tera_type=request.attacker.tera_type,
        is_terastallized=request.attacker.is_terastallized,
    )


def _field_from_request(request: DamageRequest) -> Field:
    defender_side = request.field.defender_side
    return Field(
        weather=request.field.weather or "none",
        terrain=request.field.terrain or "none",
        is_doubles=request.field.format == "gen9doubles",
        is_gravity=request.field.is_gravity,
        defender_side=SideField(
            reflect=bool(defender_side and defender_side.reflect),
            light_screen=bool(defender_side and defender_side.light_screen),
            aurora_veil=bool(defender_side and defender_side.aurora_veil),
        ),
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


def _load_entity(entity_id: str) -> dict:
    return json.loads((CACHE_DIR / f"{entity_id}.json").read_text(encoding="utf-8"))


CASES = [
    ("sun_fire_boost", _request("charizard", "pikachu", "flamethrower", weather="sun")),
    ("rain_water_boost", _request("blastoise", "charizard", "hydro-pump", weather="rain")),
    ("rain_fire_nerf", _request("charizard", "pikachu", "flamethrower", weather="rain")),
    ("heavy_rain_blocks_fire", _request("charizard", "pikachu", "flamethrower", weather="heavy-rain")),
    ("harsh_sun_blocks_water", _request("blastoise", "charizard", "hydro-pump", weather="harsh-sunlight")),
    ("sand_rock_spdef", _request("charizard", "tyranitar", "flamethrower", weather="sand")),
    ("snow_ice_def", _request("garchomp", "glaceon", "earthquake", weather="snow")),
    ("electric_terrain_boost", _request("pikachu", "charizard", "thunderbolt", terrain="electric")),
    ("electric_terrain_flying_no_boost", _request("charizard", "blastoise", "thunderbolt", terrain="electric")),
    ("grassy_terrain_eq_nerf", _request("garchomp", "pikachu", "earthquake", terrain="grassy")),
    ("grassy_terrain_eq_flying_no_nerf", _request("garchomp", "charizard", "earthquake", terrain="grassy")),
    ("misty_terrain_dragon_nerf", _request("garchomp", "blastoise", "dragon-pulse", terrain="misty")),
    ("psychic_terrain_boost", _request("gardevoir", "gengar", "psychic", terrain="psychic")),
    (
        "reflect_doubles",
        _request("garchomp", "pikachu", "earthquake", format_="gen9doubles", defender_side={"reflect": True}),
    ),
    (
        "light_screen_singles",
        _request("charizard", "pikachu", "flamethrower", defender_side={"light_screen": True}),
    ),
    (
        "aurora_veil_doubles",
        _request("charizard", "pikachu", "flamethrower", format_="gen9doubles", defender_side={"aurora_veil": True}),
    ),
    (
        "crit_bypasses_screen",
        _request("charizard", "pikachu", "flamethrower", is_critical=True, defender_side={"light_screen": True}),
    ),
    ("tera_double_stab", _request("garchomp", "blastoise", "outrage", tera_type="dragon")),
    ("tera_new_stab", _request("garchomp", "pikachu", "iron-head", tera_type="steel")),
    ("tera_original_stab_after_tera", _request("garchomp", "blastoise", "outrage", tera_type="steel")),
    ("strong_winds_flying_nerf", _request("blastoise", "charizard", "ice-beam", weather="strong-winds")),
    ("grassy_grass_move", _request("venusaur", "blastoise", "energy-ball", terrain="grassy")),
    (
        "rain_plus_electric_terrain_thunderbolt",
        _request("pikachu", "charizard", "thunderbolt", weather="rain", terrain="electric"),
    ),
]


@pytest.mark.parametrize(("case_name", "request_data"), CASES)
def test_damage_parity_field(case_name: str, request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_damage_rolls(_context_from_request(request))

    assert py_rolls == js_response.damage_rolls, (
        f"{case_name}: Python {py_rolls} != JS {js_response.damage_rolls}"
    )
