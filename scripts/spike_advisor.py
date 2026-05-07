from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.probability.single_hit import ko_chance_from_outcomes
from llm.token_logger import TokenLogger


DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash")


@dataclass(frozen=True, slots=True)
class Pokemon:
    name: str
    level: int
    types: tuple[str, ...]
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    ability: str | None = None


@dataclass(frozen=True, slots=True)
class Move:
    name: str
    move_id: str
    move_type: str
    category: str
    power: int


MEGA_KANGASKHAN = Pokemon(
    name="Mega Kangaskhan",
    level=50,
    types=("normal",),
    hp=180,
    attack=145,
    defense=120,
    special_attack=80,
    special_defense=120,
    ability="parental-bond",
)

GARCHOMP = Pokemon(
    name="Garchomp",
    level=50,
    types=("dragon", "ground"),
    hp=183,
    attack=150,
    defense=115,
    special_attack=100,
    special_defense=105,
    ability="rough-skin",
)

KANGASKHAN_MOVES = (
    Move("Fake Out", "fake-out", "normal", "physical", 40),
    Move("Return", "return", "normal", "physical", 102),
    Move("Earthquake", "earthquake", "ground", "physical", 100),
    Move("Sucker Punch", "sucker-punch", "dark", "physical", 70),
)

GARCHOMP_MOVES = (
    Move("Earthquake", "earthquake", "ground", "physical", 100),
    Move("Dragon Claw", "dragon-claw", "dragon", "physical", 80),
    Move("Outrage", "outrage", "dragon", "physical", 120),
    Move("Rock Slide", "rock-slide", "rock", "physical", 75),
)


def _ctx(attacker: Pokemon, defender: Pokemon, move: Move) -> DamageContext:
    is_physical = move.category == "physical"
    attack_stat = attacker.attack if is_physical else attacker.special_attack
    defense_stat = defender.defense if is_physical else defender.special_defense
    return DamageContext(
        attacker_level=attacker.level,
        move_power=move.power,
        attack_stat=attack_stat,
        defense_stat=defense_stat,
        move_type=move.move_type,
        move_id=move.move_id,
        attacker_types=attacker.types,
        defender_types=defender.types,
        is_physical=is_physical,
        is_critical=False,
        is_spread=False,
        field=Field(),
        attacker_ability=get_ability(attacker.ability),
        defender_ability=get_ability(defender.ability),
        attacker_species=attacker.name.lower().replace(" ", "-"),
        defender_species=defender.name.lower().replace(" ", "-"),
        attacker_hp_current=attacker.hp,
        attacker_hp_max=attacker.hp,
        defender_hp_current=defender.hp,
        defender_hp_max=defender.hp,
    )


def _move_report(attacker: Pokemon, defender: Pokemon, move: Move) -> dict[str, Any]:
    ctx = _ctx(attacker, defender, move)
    rolls = tuple(calc_damage_rolls(ctx))
    max_damage = calculate(ctx)
    ko_probability = ko_chance_from_outcomes(rolls, defender.hp)
    return {
        "move": move.name,
        "type": move.move_type,
        "category": move.category,
        "power": move.power,
        "damage_rolls": list(rolls),
        "min_damage": min(rolls),
        "max_damage": max(rolls),
        "max_roll_damage": max_damage,
        "target_hp": defender.hp,
        "ohko_probability": f"{ko_probability.numerator}/{ko_probability.denominator}",
        "ohko_percent": float(ko_probability * 100),
    }


def collect_battle_data() -> dict[str, Any]:
    kang_to_chomp = [_move_report(MEGA_KANGASKHAN, GARCHOMP, move) for move in KANGASKHAN_MOVES]
    chomp_to_kang = [_move_report(GARCHOMP, MEGA_KANGASKHAN, move) for move in GARCHOMP_MOVES]
    return {
        "scenario": {
            "attacker_side": MEGA_KANGASKHAN.name,
            "defender_side": GARCHOMP.name,
            "format_note": "1-turn advisor spike; no switching, no Protect, no speed tie modeling.",
            "known_limitations": [
                "Parental Bond second-hit behavior is not modeled in this spike.",
                "Rough Skin recoil is not modeled in the recommendation score.",
                "Items, EV spreads, and field effects are omitted.",
            ],
        },
        "pokemon": {
            MEGA_KANGASKHAN.name: {
                "level": MEGA_KANGASKHAN.level,
                "types": MEGA_KANGASKHAN.types,
                "hp": MEGA_KANGASKHAN.hp,
                "ability": MEGA_KANGASKHAN.ability,
            },
            GARCHOMP.name: {
                "level": GARCHOMP.level,
                "types": GARCHOMP.types,
                "hp": GARCHOMP.hp,
                "ability": GARCHOMP.ability,
            },
        },
        "mega_kangaskhan_to_garchomp": kang_to_chomp,
        "garchomp_to_mega_kangaskhan": chomp_to_kang,
    }


def build_prompt(data: dict[str, Any]) -> str:
    return (
        "You are Master Ball Advisor. Recommend the best one-turn action for "
        "Mega Kangaskhan against Garchomp using only the quantitative damage "
        "and KO probability data below. Be concise, mention the best move, "
        "main risk, and what Garchomp threatens in return.\n\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
    )


def call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY to run the LLM call.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }
    response = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=60,
    )
    if not response.ok:
        detail = response.text[:500]
        raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {detail}")
    body = response.json()
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    usage = body.get("usageMetadata", {})
    return text, {
        "input_tokens": int(usage.get("promptTokenCount", 0)),
        "output_tokens": int(usage.get("candidatesTokenCount", 0)),
        "cached_tokens": int(usage.get("cachedContentTokenCount", 0)),
    }


def main() -> int:
    data = collect_battle_data()
    prompt = build_prompt(data)
    print("=== Quantitative Data ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("\n=== Prompt ===")
    print(prompt)

    logger = TokenLogger()
    try:
        recommendation, usage = call_gemini(prompt, DEFAULT_MODEL)
    except Exception as exc:
        print("\n=== LLM Recommendation ===")
        print(f"Gemini call skipped/failed: {exc}", file=sys.stderr)
        return 1

    logger.log_call(
        model=DEFAULT_MODEL,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
        tool_name="damage_calculator",
        turn_number=1,
        game_id="spike_mega_kangaskhan_vs_garchomp",
    )
    print("\n=== LLM Recommendation ===")
    print(recommendation)
    print("\n=== Token Session Summary ===")
    print(json.dumps(logger.get_session_summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
