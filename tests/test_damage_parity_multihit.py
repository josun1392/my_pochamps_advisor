from __future__ import annotations

import json
from pathlib import Path

from advisor.damage.abilities import get_ability
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.grounded import GroundedInputs
from advisor.damage.multihit import (
    MultiHitAttacker,
    MultiHitMove,
    calc_multihit_damage_rolls,
    resolve_hit_count,
)
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
    "bullet-seed": ("grass", "physical", 25, "normal", (2, 5)),
    "rock-blast": ("rock", "physical", 25, "normal", (2, 5)),
    "icicle-spear": ("ice", "physical", 25, "normal", (2, 5)),
}

OVERRIDES = {
    "cinccino": {
        "types": ["normal"],
        "base_stats": {"hp": 75, "atk": 95, "def": 60, "spa": 65, "spd": 60, "spe": 115},
    },
}


def _request(
    attacker: str,
    defender: str,
    move: str,
    *,
    hits: int,
    attacker_ability: str | None = None,
) -> dict:
    return {
        "schema_version": "v1",
        "attacker": {
            "species": attacker,
            "level": 50,
            "ability": attacker_ability,
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
        "move": {"name": move, "is_critical": False, "is_z": False, "is_max": False, "hits": hits},
        "field": {
            "weather": None,
            "terrain": None,
            "is_gravity": False,
            "is_trick_room": False,
            "format": "gen9ou",
        },
    }


def _context_from_request(request: DamageRequest) -> DamageContext:
    move_type, category, power, target, _ = MOVES[request.move.name]
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
    field = Field()

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
        attacker_ability=get_ability(request.attacker.ability),
        defender_ability=get_ability(request.defender.ability),
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


def _assert_multihit_parity(request_data: dict) -> None:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)

    py_rolls = calc_multihit_damage_rolls(
        _context_from_request(request),
        hit_count=request.move.hits or 1,
    )

    assert py_rolls == js_response.damage_rolls


def test_bulletseed_min_hits_2() -> None:
    request = _request("cinccino", "pikachu", "bullet-seed", hits=2)
    single_hit = calc_damage_rolls(_context_from_request(DamageRequest.model_validate(request)))

    _assert_multihit_parity(request)
    assert calc_multihit_damage_rolls(
        _context_from_request(DamageRequest.model_validate(request)),
        hit_count=2,
    ) == [roll + roll for roll in single_hit]


def test_bulletseed_max_hits_5() -> None:
    _assert_multihit_parity(_request("cinccino", "pikachu", "bullet-seed", hits=5))


def test_rockblast_min_hits_2() -> None:
    _assert_multihit_parity(_request("cinccino", "charizard", "rock-blast", hits=2))


def test_iciclespear_max_hits_5() -> None:
    _assert_multihit_parity(_request("mamoswine", "charizard", "icicle-spear", hits=5))


def test_skill_link_forces_5_hits() -> None:
    move = MultiHitMove("bullet-seed")
    attacker = MultiHitAttacker("skill-link")
    request = _request(
        "cinccino",
        "pikachu",
        "bullet-seed",
        hits=resolve_hit_count(move, attacker, mode="min"),
        attacker_ability="skill-link",
    )

    assert resolve_hit_count(move, attacker, mode="min") == 5
    _assert_multihit_parity(request)
