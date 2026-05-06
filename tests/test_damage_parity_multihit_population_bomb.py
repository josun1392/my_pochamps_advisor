from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.abilities import get_ability
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.grounded import GroundedInputs
from advisor.damage.multihit import (
    MultiHitAttacker,
    MultiHitMove,
    calc_multihit_damage_rolls,
    get_escalated_bp,
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
    "population-bomb": ("normal", "physical", 20, "normal", 10),
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
    attacker_item: str | None = None,
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


def _assert_population_bomb_parity(request_data: dict) -> list[int]:
    request = DamageRequest.model_validate(request_data)
    js_response = call_smogon_calc(request)
    ctx = _context_from_request(request)
    move = MultiHitMove("population-bomb")

    py_rolls = calc_multihit_damage_rolls(
        ctx,
        hit_count=request.move.hits or 1,
        move=move,
    )

    assert py_rolls == js_response.damage_rolls
    return py_rolls


def test_population_bomb_default_min_1_hit() -> None:
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker()
    hits = resolve_hit_count(move, attacker, mode="min")

    assert hits == 1
    _assert_population_bomb_parity(
        _request("cinccino", "pikachu", "population-bomb", hits=hits)
    )


def test_population_bomb_default_max_10_hits() -> None:
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker()
    hits = resolve_hit_count(move, attacker, mode="max")
    request = _request("cinccino", "pikachu", "population-bomb", hits=hits)
    single_hit = calc_damage_rolls(_context_from_request(DamageRequest.model_validate(request)))

    assert hits == 10
    assert _assert_population_bomb_parity(request) == [roll * 10 for roll in single_hit]


def test_population_bomb_skill_link_10_hits() -> None:
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(ability="skill-link")
    hits = resolve_hit_count(move, attacker, mode="min")

    assert hits == 10
    _assert_population_bomb_parity(
        _request(
            "cinccino",
            "pikachu",
            "population-bomb",
            hits=hits,
            attacker_ability="skill-link",
        )
    )


def test_population_bomb_loaded_dice_min_4_hits() -> None:
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(item="loaded-dice")
    hits = resolve_hit_count(move, attacker, mode="min")

    assert hits == 4
    _assert_population_bomb_parity(
        _request(
            "cinccino",
            "pikachu",
            "population-bomb",
            hits=hits,
            attacker_item="loaded-dice",
        )
    )


def test_population_bomb_loaded_dice_max_10_hits() -> None:
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(item="loaded-dice")
    hits = resolve_hit_count(move, attacker, mode="max")

    assert hits == 10
    _assert_population_bomb_parity(
        _request(
            "cinccino",
            "pikachu",
            "population-bomb",
            hits=hits,
            attacker_item="loaded-dice",
        )
    )


def test_population_bomb_skill_link_plus_loaded_dice_loaded_dice_wins() -> None:
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(ability="skill-link", item="loaded-dice")
    hits = resolve_hit_count(move, attacker, mode="min")

    assert hits == 4
    _assert_population_bomb_parity(
        _request(
            "cinccino",
            "pikachu",
            "population-bomb",
            hits=hits,
            attacker_ability="skill-link",
            attacker_item="loaded-dice",
        )
    )


def test_population_bomb_skill_link_only_returns_10() -> None:
    """Skill Link removes multiaccuracy, so all 10 hits are guaranteed post-connect."""
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(ability="skill-link")

    assert resolve_hit_count(move, attacker, mode="min") == 10
    assert resolve_hit_count(move, attacker, mode="max") == 10


def test_population_bomb_loaded_dice_only_returns_4_to_10() -> None:
    """Loaded Dice on Tier C uses targetHits = 10 - random(7), deterministic 4..10."""
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(item="loaded-dice")

    assert resolve_hit_count(move, attacker, mode="min") == 4
    assert resolve_hit_count(move, attacker, mode="max") == 10


def test_population_bomb_skill_link_and_loaded_dice_loaded_dice_still_applies() -> None:
    """
    Regression: PR #3.4-C2 incorrectly returned 10 here.
    Showdown source (sim/battle-actions.ts line 876) shows Loaded Dice's
    targetHits === 10 branch is independent of Skill Link's multiaccuracy removal.
    """
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker(ability="skill-link", item="loaded-dice")

    assert resolve_hit_count(move, attacker, mode="min") == 4
    assert resolve_hit_count(move, attacker, mode="max") == 10


def test_population_bomb_default_post_connect_min_is_1() -> None:
    """Post-connect model: first hit has landed; initial miss lives above damage."""
    move = MultiHitMove("population-bomb")
    attacker = MultiHitAttacker()

    assert resolve_hit_count(move, attacker, mode="min") == 1
    assert resolve_hit_count(move, attacker, mode="max") == 10


def test_population_bomb_bp_per_hit_is_20() -> None:
    move = MultiHitMove("population-bomb")

    assert [get_escalated_bp(move, hit_idx) for hit_idx in range(10)] == [20] * 10


def test_population_bomb_technician_applies_to_all_hits() -> None:
    request = _request(
        "cinccino",
        "pikachu",
        "population-bomb",
        hits=10,
        attacker_ability="technician",
    )
    single_hit = calc_damage_rolls(_context_from_request(DamageRequest.model_validate(request)))

    assert _assert_population_bomb_parity(request) == [roll * 10 for roll in single_hit]


@pytest.mark.xfail(reason="Probabilistic sampling reserved for PR #3.4-D", strict=True)
def test_population_bomb_default_probabilistic_distribution() -> None:
    resolve_hit_count(MultiHitMove("population-bomb"), MultiHitAttacker(), mode="expected")
