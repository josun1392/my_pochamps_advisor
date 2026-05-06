from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.field import Field, SideField
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
    "close-combat": ("fighting", "physical", 120, "normal"),
    "earthquake": ("ground", "physical", 100, "allAdjacent"),
    "flamethrower": ("fire", "special", 90, "normal"),
    "iron-head": ("steel", "physical", 80, "normal"),
    "psychic": ("psychic", "special", 90, "normal"),
    "thunderbolt": ("electric", "special", 90, "normal"),
}

ENTITY_OVERRIDES = {
    "metagross": {
        "types": ["steel", "psychic"],
        "base_stats": {"hp": 80, "atk": 135, "def": 130, "spa": 95, "spd": 90, "spe": 70},
    },
}


def _request(
    attacker: str,
    defender: str,
    move: str,
    *,
    attacker_item: str | None = None,
) -> dict:
    return {
        "schema_version": "v1",
        "attacker": {
            "species": attacker,
            "level": 50,
            "ability": None,
            "item": attacker_item,
            "nature": "hardy",
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "status": None,
            "tera_type": None,
            "is_terastallized": False,
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
        "move": {"name": move, "is_critical": False, "is_z": False, "is_max": False},
        "field": {
            "weather": None,
            "terrain": None,
            "is_gravity": False,
            "is_trick_room": False,
            "format": "gen9ou",
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
        attacker_item=get_item(request.attacker.item),
        defender_item=get_item(request.defender.item),
        attacker_species=request.attacker.species,
        defender_species=request.defender.species,
    )


def _field_from_request(request: DamageRequest) -> Field:
    return Field(
        weather=request.field.weather or "none",
        terrain=request.field.terrain or "none",
        is_doubles=request.field.format == "gen9doubles",
        is_gravity=request.field.is_gravity,
        defender_side=SideField(),
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
    if entity_id in ENTITY_OVERRIDES:
        return ENTITY_OVERRIDES[entity_id]
    return json.loads((CACHE_DIR / f"{entity_id}.json").read_text(encoding="utf-8"))


CASES = [
    ("life_orb_earthquake", _request("garchomp", "arcanine", "earthquake", attacker_item="life-orb")),
    ("choice_band_close_combat", _request("conkeldurr", "pikachu", "close-combat", attacker_item="choice-band")),
    ("choice_specs_thunderbolt", _request("pikachu", "charizard", "thunderbolt", attacker_item="choice-specs")),
    ("muscle_band_iron_head", _request("metagross", "pikachu", "iron-head", attacker_item="muscle-band")),
    ("wise_glasses_psychic", _request("espeon", "conkeldurr", "psychic", attacker_item="wise-glasses")),
    ("expert_belt_super_effective", _request("charizard", "forretress", "flamethrower", attacker_item="expert-belt")),
    ("expert_belt_neutral", _request("charizard", "pikachu", "flamethrower", attacker_item="expert-belt")),
    ("flame_plate_flamethrower", _request("arcanine", "pikachu", "flamethrower", attacker_item="flame-plate")),
    ("life_orb_super_effective", _request("pikachu", "charizard", "thunderbolt", attacker_item="life-orb")),
    ("choice_band_no_life_orb", _request("garchomp", "pikachu", "earthquake", attacker_item="choice-band")),
]


@pytest.mark.parametrize(("case_name", "request_data"), CASES)
def test_damage_parity_items(case_name: str, request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_damage_rolls(_context_from_request(request))

    assert py_rolls == js_response.damage_rolls, (
        f"{case_name}: Python {py_rolls} != JS {js_response.damage_rolls}"
    )
