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
    "acrobatics": ("flying", "physical", 110, "normal"),
    "air-slash": ("flying", "special", 75, "normal"),
    "fire-blast": ("fire", "special", 110, "normal"),
    "flamethrower": ("fire", "special", 90, "normal"),
    "giga-drain": ("grass", "special", 75, "normal"),
    "bug-bite": ("bug", "physical", 60, "normal"),
    "bullet-punch": ("steel", "physical", 40, "normal"),
    "close-combat": ("fighting", "physical", 120, "normal"),
    "boomburst": ("normal", "special", 140, "allAdjacent"),
    "crunch": ("dark", "physical", 80, "normal"),
    "dazzling-gleam": ("fairy", "special", 80, "allAdjacentFoes"),
    "dragon-claw": ("dragon", "physical", 80, "normal"),
    "dragon-pulse": ("dragon", "special", 85, "normal"),
    "double-edge": ("normal", "physical", 120, "normal"),
    "ice-beam": ("ice", "special", 90, "normal"),
    "iron-head": ("steel", "physical", 80, "normal"),
    "mach-punch": ("fighting", "physical", 40, "normal"),
    "moonblast": ("fairy", "special", 95, "normal"),
    "play-rough": ("fairy", "physical", 90, "normal"),
    "psychic": ("psychic", "special", 90, "normal"),
    "rock-slide": ("rock", "physical", 75, "allAdjacentFoes"),
    "scratch": ("normal", "physical", 40, "normal"),
    "shadow-ball": ("ghost", "special", 80, "normal"),
    "sucker-punch": ("dark", "physical", 70, "normal"),
    "surf": ("water", "special", 90, "allAdjacent"),
    "struggle": ("normal", "physical", 50, "normal"),
    "tackle": ("normal", "physical", 40, "normal"),
    "thunderbolt": ("electric", "special", 90, "normal"),
    "water-gun": ("water", "special", 40, "normal"),
    "x-scissor": ("bug", "physical", 80, "normal"),
}

OVERRIDES = {
    "cherrim": {"types": ["grass"], "base_stats": {"hp": 70, "atk": 60, "def": 70, "spa": 87, "spd": 78, "spe": 85}},
    "archeops": {"types": ["rock", "flying"], "base_stats": {"hp": 75, "atk": 140, "def": 65, "spa": 112, "spd": 65, "spe": 110}},
    "exploud": {"types": ["normal"], "base_stats": {"hp": 104, "atk": 91, "def": 63, "spa": 91, "spd": 73, "spe": 68}},
    "gogoat": {"types": ["grass"], "base_stats": {"hp": 123, "atk": 100, "def": 62, "spa": 97, "spd": 81, "spe": 68}},
    "great-tusk": {"types": ["ground", "fighting"], "base_stats": {"hp": 115, "atk": 131, "def": 131, "spa": 53, "spd": 53, "spe": 87}},
    "hitmonchan": {"types": ["fighting"], "base_stats": {"hp": 50, "atk": 105, "def": 79, "spa": 35, "spd": 110, "spe": 76}},
    "iron-bundle": {"types": ["ice", "water"], "base_stats": {"hp": 56, "atk": 80, "def": 114, "spa": 124, "spd": 60, "spe": 136}},
    "iron-moth": {"types": ["fire", "poison"], "base_stats": {"hp": 80, "atk": 70, "def": 60, "spa": 140, "spd": 110, "spe": 110}},
    "flutter-mane": {"types": ["ghost", "fairy"], "base_stats": {"hp": 55, "atk": 55, "def": 55, "spa": 135, "spd": 135, "spe": 135}},
    "lugia": {"types": ["psychic", "flying"], "base_stats": {"hp": 106, "atk": 90, "def": 130, "spa": 90, "spd": 154, "spe": 110}},
    "lunala": {"types": ["psychic", "ghost"], "base_stats": {"hp": 137, "atk": 113, "def": 89, "spa": 137, "spd": 107, "spe": 97}},
    "minun": {"types": ["electric"], "base_stats": {"hp": 60, "atk": 40, "def": 50, "spa": 75, "spd": 85, "spe": 95}},
    "necrozma-ultra": {"types": ["psychic", "dragon"], "base_stats": {"hp": 97, "atk": 167, "def": 97, "spa": 167, "spd": 97, "spe": 129}},
    "plusle": {"types": ["electric"], "base_stats": {"hp": 60, "atk": 50, "def": 40, "spa": 85, "spd": 75, "spe": 95}},
    "psyduck": {"types": ["water"], "base_stats": {"hp": 50, "atk": 52, "def": 48, "spa": 65, "spd": 50, "spe": 55}},
    "tapu-lele": {"types": ["psychic", "fairy"], "base_stats": {"hp": 70, "atk": 85, "def": 75, "spa": 130, "spd": 115, "spe": 95}},
    "weezing-galar": {"types": ["poison", "fairy"], "base_stats": {"hp": 65, "atk": 90, "def": 120, "spa": 85, "spd": 70, "spe": 60}},
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
    ally_has_plus_minus: bool = False,
    boosted_stat: str | None = None,
    attacker_current_hp_pct: int = 100,
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
            "current_hp_pct": attacker_current_hp_pct,
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
            "ally_has_plus_minus": ally_has_plus_minus,
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
        ally_has_plus_minus=request.field.ally_has_plus_minus,
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
        attacker_hp_current=request.attacker.current_hp_pct,
        attacker_hp_max=100,
        defender_hp_current=request.defender.current_hp_pct,
        defender_hp_max=100,
        defender_hp_ratio=request.defender.current_hp_pct / 100,
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
    # PR #3.3-A3: Neutralizing Gas suppresses Cloud Nine -> sun boost re-applies
    (
        "neutralizing_gas_disables_cloud_nine_in_sun",
        _request(
            "weezing-galar",
            "psyduck",
            "flamethrower",
            attacker_ability="neutralizing-gas",
            defender_ability="cloud-nine",
            weather="sun",
        ),
    ),
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
    ("azumarill_huge_power_play_rough", _request("azumarill", "garchomp", "play-rough", attacker_ability="huge-power")),
    ("flapple_hustle_tackle", _request("flapple", "pikachu", "tackle", attacker_ability="hustle")),
    ("furfrou_fur_coat_earthquake", _request("garchomp", "furfrou", "earthquake", defender_ability="fur-coat")),
    ("goodra_h_ice_scales_psychic", _request("tapu-lele", "goodra-hisui", "psychic", defender_ability="ice-scales")),
    ("lugia_multiscale_full_hp_earthquake", _request("garchomp", "lugia", "earthquake", defender_ability="multiscale")),
    ("lunala_shadow_shield_full_hp_sucker_punch", _request("gengar", "lunala", "sucker-punch", defender_ability="shadow-shield")),
    ("solar_power_fire_blast_sun", _request("charizard", "blastoise", "fire-blast", attacker_ability="solar-power", weather="sun")),
    ("solar_power_fire_blast_no_sun", _request("charizard", "blastoise", "fire-blast", attacker_ability="solar-power")),
    ("plusle_plus_thunderbolt_ally_minun", _request("plusle", "blastoise", "thunderbolt", attacker_ability="plus", ally_has_plus_minus=True)),
    ("minun_minus_thunderbolt_solo", _request("minun", "blastoise", "thunderbolt", attacker_ability="minus")),
    ("scizor_technician_bullet_punch", _request("scizor", "pikachu", "bullet-punch", attacker_ability="technician")),
    ("scizor_technician_bug_bite", _request("scizor", "pikachu", "bug-bite", attacker_ability="technician")),
    ("scizor_technician_x_scissor_no_boost", _request("scizor", "pikachu", "x-scissor", attacker_ability="technician")),
    ("charizard_tough_claws_dragon_claw", _request("charizard", "blastoise", "dragon-claw", attacker_ability="tough-claws")),
    ("hitmonchan_iron_fist_mach_punch", _request("hitmonchan", "pikachu", "mach-punch", attacker_ability="iron-fist")),
    ("hitmonchan_iron_fist_close_combat_no_boost", _request("hitmonchan", "pikachu", "close-combat", attacker_ability="iron-fist")),
    ("mega_aggron_filter_earthquake", _request("garchomp", "aggron-mega", "earthquake", defender_ability="filter")),
    ("rhyperior_solid_rock_surf", _request("blastoise", "rhyperior", "surf", defender_ability="solid-rock")),
    ("ultra_necrozma_prism_armor_dazzling_gleam", _request("tapu-lele", "necrozma-ultra", "dazzling-gleam", defender_ability="prism-armor")),
    ("toxapex_punk_rock_boomburst", _request("exploud", "toxapex", "boomburst", attacker_ability="scrappy", defender_ability="punk-rock")),
    ("toxapex_punk_rock_earthquake_no_sound", _request("garchomp", "toxapex", "earthquake", defender_ability="punk-rock")),
    ("aggron_filter_full_hp_earthquake", _request("garchomp", "aggron", "earthquake", defender_ability="filter")),
    ("charizard_blaze_flamethrower_low_hp", _request("charizard", "pikachu", "flamethrower", attacker_ability="blaze", attacker_current_hp_pct=10)),
    ("charizard_blaze_flamethrower_half_hp", _request("charizard", "pikachu", "flamethrower", attacker_ability="blaze", attacker_current_hp_pct=50)),
    ("charizard_blaze_air_slash_low_hp_wrong_type", _request("charizard", "pikachu", "air-slash", attacker_ability="blaze", attacker_current_hp_pct=10)),
    ("venusaur_overgrow_giga_drain_33_hp", _request("venusaur", "blastoise", "giga-drain", attacker_ability="overgrow", attacker_current_hp_pct=33)),
    ("venusaur_overgrow_giga_drain_34_hp", _request("venusaur", "blastoise", "giga-drain", attacker_ability="overgrow", attacker_current_hp_pct=34)),
    ("archeops_defeatist_acrobatics_half_hp", _request("archeops", "pikachu", "acrobatics", attacker_ability="defeatist", attacker_current_hp_pct=50)),
    ("gyarados_strong_jaw_crunch", _request("gyarados", "pikachu", "crunch", attacker_ability="strong-jaw")),
    ("blastoise_mega_launcher_dragon_pulse", _request("blastoise", "pikachu", "dragon-pulse", attacker_ability="mega-launcher")),
    ("charizard_reckless_double_edge", _request("charizard", "pikachu", "double-edge", attacker_ability="reckless")),
    ("charizard_reckless_struggle_no_boost", _request("charizard", "pikachu", "struggle", attacker_ability="reckless")),
    ("exploud_punk_rock_boomburst", _request("exploud", "pikachu", "boomburst", attacker_ability="punk-rock")),
    ("garchomp_sheer_force_iron_head", _request("garchomp", "pikachu", "iron-head", attacker_ability="sheer-force")),
    ("garchomp_sheer_force_earthquake_no_boost", _request("garchomp", "pikachu", "earthquake", attacker_ability="sheer-force")),
    ("pikachu_transistor_thunderbolt", _request("pikachu", "blastoise", "thunderbolt", attacker_ability="transistor")),
]


@pytest.mark.parametrize(("case_name", "request_data"), CASES)
def test_damage_parity_abilities_weather(case_name: str, request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_damage_rolls(_context_from_request(request))

    assert py_rolls == js_response.damage_rolls, (
        f"{case_name}: Python {py_rolls} != JS {js_response.damage_rolls}"
    )
