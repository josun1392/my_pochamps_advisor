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
from advisor.damage.type_immunity import move_flags_for
from advisor.parity.bridge import call_smogon_calc
from advisor.parity.schemas import DamageRequest


CACHE_DIR = Path("data/cache/pokemon")

MOVES = {
    "boomburst": ("normal", "special", 140, "allAdjacent"),
    "earthquake": ("ground", "physical", 100, "allAdjacent"),
    "energy-ball": ("grass", "special", 90, "normal"),
    "fire-punch": ("fire", "physical", 75, "normal"),
    "flamethrower": ("fire", "special", 90, "normal"),
    "ice-beam": ("ice", "special", 90, "normal"),
    "shadow-ball": ("ghost", "special", 80, "normal"),
    "tackle": ("normal", "physical", 40, "normal"),
    "thunderbolt": ("electric", "special", 90, "normal"),
    "water-gun": ("water", "special", 40, "normal"),
}

CONTACT_MOVES = {"fire-punch", "tackle"}
NFE = {"pikachu"}

OVERRIDES = {
    "shedinja": {
        "types": ["bug", "ghost"],
        "base_stats": {"hp": 1, "atk": 90, "def": 45, "spa": 30, "spd": 30, "spe": 40},
    }
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
            "boosted_stat": None,
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
        is_gravity=request.field.is_gravity,
    )

    return DamageContext(
        attacker_level=request.attacker.level,
        move_power=power,
        attack_stat=attack_stat,
        defense_stat=defense_stat,
        move_type=move_type,
        move_id=request.move.name,
        move_flags=move_flags_for(request.move.name),
        attacker_types=tuple(attacker_data["types"]),
        defender_types=tuple(defender_data["types"]),
        is_physical=category == "physical",
        is_critical=request.move.is_critical,
        is_spread=field.is_doubles and target in {"allAdjacent", "allAdjacentFoes"},
        is_contact=request.move.name in CONTACT_MOVES,
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
        attacker_is_nfe=request.attacker.species in NFE,
        defender_is_nfe=request.defender.species in NFE,
        attacker_ability=get_ability(request.attacker.ability),
        defender_ability=get_ability(request.defender.ability),
        attacker_stats=attacker_stats,
        defender_stats=defender_stats,
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
    path = CACHE_DIR / f"{entity_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return OVERRIDES[entity_id]


CASES = [
    ("volt_absorb_electric", _request("pikachu", "raichu", "thunderbolt", defender_ability="volt-absorb")),
    ("volt_absorb_normal_no_immunity", _request("pikachu", "raichu", "tackle", defender_ability="volt-absorb")),
    ("water_absorb_water", _request("blastoise", "charizard", "water-gun", defender_ability="water-absorb")),
    ("flash_fire_fire", _request("charizard", "pikachu", "flamethrower", defender_ability="flash-fire")),
    ("sap_sipper_grass", _request("venusaur", "pikachu", "energy-ball", defender_ability="sap-sipper")),
    ("motor_drive_electric", _request("pikachu", "raichu", "thunderbolt", defender_ability="motor-drive")),
    ("lightning_rod_electric", _request("pikachu", "raichu", "thunderbolt", defender_ability="lightning-rod")),
    ("storm_drain_water", _request("blastoise", "charizard", "water-gun", defender_ability="storm-drain")),
    ("earth_eater_ground", _request("garchomp", "pikachu", "earthquake", defender_ability="earth-eater")),
    ("well_baked_body_fire", _request("charizard", "pikachu", "flamethrower", defender_ability="well-baked-body")),
    ("levitate_ground_immune", _request("garchomp", "gengar", "earthquake", defender_ability="levitate")),
    ("bulletproof_shadow_ball", _request("gengar", "pikachu", "shadow-ball", defender_ability="bulletproof")),
    ("soundproof_boomburst", _request("snorlax", "pikachu", "boomburst", defender_ability="soundproof")),
    ("heatproof_fire_half", _request("charizard", "pikachu", "flamethrower", defender_ability="heatproof")),
    ("thick_fat_fire_half", _request("charizard", "pikachu", "flamethrower", defender_ability="thick-fat")),
    ("thick_fat_ice_half", _request("blastoise", "garchomp", "ice-beam", defender_ability="thick-fat")),
    ("water_bubble_fire_received_half", _request("charizard", "pikachu", "flamethrower", defender_ability="water-bubble")),
    ("water_bubble_water_dealt_double", _request("blastoise", "charizard", "water-gun", attacker_ability="water-bubble")),
    ("purifying_salt_ghost_half", _request("gengar", "pikachu", "shadow-ball", defender_ability="purifying-salt")),
    ("dry_skin_fire_125", _request("charizard", "pikachu", "flamethrower", defender_ability="dry-skin")),
    ("fluffy_contact_half", _request("pikachu", "charizard", "tackle", defender_ability="fluffy")),
    ("fluffy_fire_double", _request("charizard", "pikachu", "flamethrower", defender_ability="fluffy")),
    ("fluffy_contact_fire_neutral", _request("charizard", "pikachu", "fire-punch", defender_ability="fluffy")),
    ("solid_rock_se_75", _request("blastoise", "rhyperior", "water-gun", defender_ability="solid-rock")),
    ("filter_4x_se_75", _request("blastoise", "garchomp", "ice-beam", defender_ability="filter")),
    ("prism_armor_se_75", _request("blastoise", "rhyperior", "water-gun", defender_ability="prism-armor")),
    ("tinted_lens_nve_double", _request("blastoise", "venusaur", "water-gun", attacker_ability="tinted-lens")),
    ("wonder_guard_neutral_immune", _request("pikachu", "shedinja", "thunderbolt", defender_ability="wonder-guard")),
    ("wonder_guard_se_passes", _request("charizard", "shedinja", "flamethrower", defender_ability="wonder-guard")),
    ("mold_breaker_negates_volt_absorb", _request("pikachu", "raichu", "thunderbolt", attacker_ability="mold-breaker", defender_ability="volt-absorb")),
    ("mold_breaker_negates_levitate", _request("garchomp", "gengar", "earthquake", attacker_ability="mold-breaker", defender_ability="levitate")),
    ("mold_breaker_negates_solid_rock", _request("blastoise", "rhyperior", "water-gun", attacker_ability="mold-breaker", defender_ability="solid-rock")),
    ("mold_breaker_does_not_negate_prism_armor", _request("blastoise", "rhyperior", "water-gun", attacker_ability="mold-breaker", defender_ability="prism-armor")),
    ("teravolt_acts_as_mold_breaker", _request("pikachu", "raichu", "thunderbolt", attacker_ability="teravolt", defender_ability="volt-absorb")),
    ("neutralizing_gas_disables_volt_absorb", _request("pikachu", "raichu", "thunderbolt", attacker_ability="neutralizing-gas", defender_ability="volt-absorb")),
    ("water_bubble_plus_rain_water", _request("blastoise", "charizard", "water-gun", attacker_ability="water-bubble", weather="rain")),
    ("tinted_lens_plus_choice_specs", _request("blastoise", "venusaur", "water-gun", attacker_ability="tinted-lens", attacker_item="choice-specs")),
    ("solid_rock_plus_eviolite", _request("garchomp", "pikachu", "earthquake", defender_ability="solid-rock", defender_item="eviolite")),
]


@pytest.mark.parametrize(("case_name", "request_data"), CASES)
def test_damage_parity_abilities_immunity(case_name: str, request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_damage_rolls(_context_from_request(request))

    assert py_rolls == js_response.damage_rolls, (
        f"{case_name}: Python {py_rolls} != JS {js_response.damage_rolls}"
    )
