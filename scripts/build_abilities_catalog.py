from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


OUT_PATH = Path("data/static/abilities.json")
CAT_PATH = Path("data/static/ability_categories.json")

IMPLEMENTED: dict[str, dict[str, Any]] = {
    "drought": {"category": "weather_summon", "summons": "sun", "damage_effect": "none"},
    "drizzle": {"category": "weather_summon", "summons": "rain", "damage_effect": "none"},
    "sand-stream": {"category": "weather_summon", "summons": "sand", "damage_effect": "none"},
    "snow-warning": {"category": "weather_summon", "summons": "snow", "damage_effect": "none"},
    "desolate-land": {"category": "weather_summon", "summons": "harsh-sunlight", "damage_effect": "none"},
    "primordial-sea": {"category": "weather_summon", "summons": "heavy-rain", "damage_effect": "none"},
    "delta-stream": {"category": "weather_summon", "summons": "strong-winds", "damage_effect": "none"},
    "orichalcum-pulse": {"category": "weather_summon", "summons": "sun", "damage_effect": "none"},
    "hadron-engine": {"category": "terrain_summon", "summons": "electric", "damage_effect": "none"},
    "electric-surge": {"category": "terrain_summon", "summons": "electric", "damage_effect": "none"},
    "psychic-surge": {"category": "terrain_summon", "summons": "psychic", "damage_effect": "none"},
    "grassy-surge": {"category": "terrain_summon", "summons": "grassy", "damage_effect": "none"},
    "misty-surge": {"category": "terrain_summon", "summons": "misty", "damage_effect": "none"},
    "cloud-nine": {"category": "weather_suppress"},
    "air-lock": {"category": "weather_suppress"},
    "chlorophyll": {"category": "weather_conditional", "weather": "sun", "stat": "spe", "multiplier_q12": 8192},
    "swift-swim": {"category": "weather_conditional", "weather": "rain", "stat": "spe", "multiplier_q12": 8192},
    "sand-rush": {"category": "weather_conditional", "weather": "sand", "stat": "spe", "multiplier_q12": 8192},
    "slush-rush": {"category": "weather_conditional", "weather": "snow", "stat": "spe", "multiplier_q12": 8192},
    "solar-power": {
        "category": "weather_conditional",
        "weather": "sun",
        "stat": "spa",
        "multiplier_q12": 6144,
        "side_effect": "hp_loss_per_turn",
    },
    "flower-gift": {"category": "weather_conditional", "weather": "sun", "stat": "atk_spd", "multiplier_q12": 6144},
    "forecast": {"category": "weather_conditional", "weather": "any", "damage_effect": "type_change_external"},
    "sand-force": {
        "category": "weather_conditional",
        "weather": "sand",
        "boosted_types": ["rock", "ground", "steel"],
        "multiplier_q12": 5325,
    },
    "sand-veil": {"category": "weather_conditional", "weather": "sand", "damage_effect": "accuracy_only"},
    "snow-cloak": {"category": "weather_conditional", "weather": "snow", "damage_effect": "accuracy_only"},
    "ice-body": {"category": "weather_conditional", "weather": "snow", "damage_effect": "turn_loop"},
    "rain-dish": {"category": "weather_conditional", "weather": "rain", "damage_effect": "turn_loop"},
    "leaf-guard": {"category": "weather_conditional", "weather": "sun", "damage_effect": "status_only"},
    "harvest": {"category": "weather_conditional", "weather": "sun", "damage_effect": "turn_loop"},
    "surge-surfer": {"category": "terrain_conditional", "terrain": "electric", "stat": "spe", "multiplier_q12": 8192},
    "grass-pelt": {"category": "terrain_conditional", "terrain": "grassy", "stat": "def", "multiplier_q12": 6144},
    "mimicry": {"category": "terrain_conditional", "terrain": "any", "damage_effect": "type_change_external"},
    "quark-drive": {
        "category": "paradox",
        "trigger_field": "electric_terrain",
        "trigger_item": "booster-energy",
        "stat_boost_q12": {"default": 5324, "spe": 6144},
    },
    "protosynthesis": {
        "category": "paradox",
        "trigger_field": "sun",
        "trigger_item": "booster-energy",
        "stat_boost_q12": {"default": 5324, "spe": 6144},
    },
    "volt-absorb": {"category": "type_immunity", "immune_to_type": "electric"},
    "water-absorb": {"category": "type_immunity", "immune_to_type": "water"},
    "flash-fire": {
        "category": "type_immunity",
        "immune_to_type": "fire",
        "boost_on_proc": {"type": "fire", "multiplier_q12": 6144},
    },
    "sap-sipper": {"category": "type_immunity", "immune_to_type": "grass"},
    "motor-drive": {"category": "type_immunity", "immune_to_type": "electric"},
    "lightning-rod": {"category": "type_immunity_redirect", "immune_to_type": "electric"},
    "storm-drain": {"category": "type_immunity_redirect", "immune_to_type": "water"},
    "earth-eater": {"category": "type_immunity", "immune_to_type": "ground"},
    "levitate": {"category": "type_immunity", "immune_to_type": "ground", "via_grounded_check": True},
    "well-baked-body": {"category": "type_immunity", "immune_to_type": "fire"},
    "dry-skin": {
        "category": "type_dual_effect",
        "immune_to_type": "water",
        "vulnerable_type": "fire",
        "vulnerable_multiplier_q12": 5120,
    },
    "bulletproof": {"category": "move_flag_immunity", "immune_flag": "bullet"},
    "soundproof": {"category": "move_flag_immunity", "immune_flag": "sound"},
    "overcoat": {"category": "move_flag_immunity", "immune_flag": "powder"},
    "telepathy": {"category": "ally_immunity", "implemented_stub": True},
    "fluffy": {
        "category": "damage_mod_flag",
        "contact_multiplier_q12": 2048,
        "fire_multiplier_q12": 8192,
    },
    "heatproof": {"category": "damage_mod_type", "boosted_types": ["fire"], "multiplier_q12": 2048},
    "thick-fat": {"category": "damage_mod_type", "boosted_types": ["fire", "ice"], "multiplier_q12": 2048},
    "water-bubble": {
        "category": "damage_mod_dual",
        "defensive_type": "fire",
        "defensive_multiplier_q12": 2048,
        "offensive_type": "water",
        "offensive_multiplier_q12": 8192,
    },
    "purifying-salt": {"category": "damage_mod_type", "boosted_types": ["ghost"], "multiplier_q12": 2048},
    "solid-rock": {
        "category": "damage_mod_super_effective",
        "multiplier_q12": 3072,
        "ignored_by_mold_breaker": True,
    },
    "filter": {
        "category": "damage_mod_super_effective",
        "multiplier_q12": 3072,
        "ignored_by_mold_breaker": True,
    },
    "prism-armor": {
        "category": "damage_mod_super_effective",
        "multiplier_q12": 3072,
        "ignored_by_mold_breaker": False,
    },
    "tinted-lens": {"category": "damage_mod_not_very_effective", "multiplier_q12": 8192},
    "mold-breaker": {"category": "ability_suppress", "scope": "defender_immunity_and_damage"},
    "teravolt": {"category": "ability_suppress", "scope": "defender_immunity_and_damage"},
    "turboblaze": {"category": "ability_suppress", "scope": "defender_immunity_and_damage"},
    "neutralizing-gas": {"category": "ability_global_suppress"},
    "wonder-guard": {"category": "wonder_guard"},
    "magic-guard": {"category": "residual_immunity", "implemented_stub": True},
    "magic-bounce": {"category": "status_reflect", "implemented_stub": True},
}

STUB_CATEGORIES = {
    "huge-power": "stat_mod",
    "pure-power": "stat_mod",
}


def _all_smogon_abilities() -> list[dict[str, str]]:
    script = (
        "const {ABILITIES}=require('./tools/smogon_bridge/node_modules/@smogon/calc/dist/data/abilities');"
        "const {toID}=require('./tools/smogon_bridge/node_modules/@smogon/calc/dist/util');"
        "console.log(JSON.stringify(ABILITIES[9].map(name=>({id:toID(name).replace(/([a-z])([A-Z])/g,'$1-$2'),name}))));"
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    names = json.loads(result.stdout)
    return [{"id": _slugify(entry["name"]), "name": entry["name"]} for entry in names]


def _slugify(name: str) -> str:
    out: list[str] = []
    previous_dash = False
    for char in name.lower():
        if char.isalnum():
            out.append(char)
            previous_dash = False
        elif not previous_dash:
            out.append("-")
            previous_dash = True
    return "".join(out).strip("-")


def build_catalog() -> dict[str, Any]:
    abilities: dict[str, Any] = {}
    for entry in _all_smogon_abilities():
        ability_id = entry["id"]
        data = {
            "name": entry["name"],
            "category": STUB_CATEGORIES.get(ability_id, "uncategorized"),
            "implemented": False,
        }
        if ability_id in IMPLEMENTED:
            data.update(IMPLEMENTED[ability_id])
            data["implemented"] = True
        abilities[ability_id] = data

    return {"version": "champions-2026", "abilities": dict(sorted(abilities.items()))}


def build_categories(catalog: dict[str, Any]) -> dict[str, Any]:
    categories: dict[str, list[str]] = {}
    for ability_id, data in catalog["abilities"].items():
        categories.setdefault(data["category"], []).append(ability_id)
    return {
        "version": catalog["version"],
        "categories": {key: sorted(value) for key, value in sorted(categories.items())},
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    write_json(OUT_PATH, catalog)
    write_json(CAT_PATH, build_categories(catalog))
    implemented = sum(1 for item in catalog["abilities"].values() if item["implemented"])
    print(f"wrote {OUT_PATH}")
    print(f"wrote {CAT_PATH}")
    print(f"total abilities: {len(catalog['abilities'])}")
    print(f"implemented: {implemented}")


if __name__ == "__main__":
    main()
