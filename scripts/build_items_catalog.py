from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT_DIR = Path("data/static")
ITEMS_PATH = OUT_DIR / "items_damage.json"
MEGA_STONES_PATH = OUT_DIR / "mega_stones.json"
ROSTER_PATH = OUT_DIR / "champions_roster.json"

Q12_TYPE_BOOST = 4915
Q12_LIFE_ORB = 5324
Q12_CHOICE = 6144
Q12_SMALL_BOOST = 4505
Q12_DOUBLE = 8192

TYPE_BOOST_ITEMS: dict[str, tuple[str, int]] = {
    "silk-scarf": ("normal", Q12_TYPE_BOOST),
    "charcoal": ("fire", Q12_TYPE_BOOST),
    "mystic-water": ("water", Q12_TYPE_BOOST),
    "sea-incense": ("water", Q12_TYPE_BOOST),
    "wave-incense": ("water", Q12_TYPE_BOOST),
    "magnet": ("electric", Q12_TYPE_BOOST),
    "miracle-seed": ("grass", Q12_TYPE_BOOST),
    "rose-incense": ("grass", Q12_TYPE_BOOST),
    "never-melt-ice": ("ice", Q12_TYPE_BOOST),
    "black-belt": ("fighting", Q12_TYPE_BOOST),
    "poison-barb": ("poison", Q12_TYPE_BOOST),
    "soft-sand": ("ground", Q12_TYPE_BOOST),
    "sharp-beak": ("flying", Q12_TYPE_BOOST),
    "twisted-spoon": ("psychic", Q12_TYPE_BOOST),
    "odd-incense": ("psychic", Q12_TYPE_BOOST),
    "silver-powder": ("bug", Q12_TYPE_BOOST),
    "hard-stone": ("rock", Q12_TYPE_BOOST),
    "spell-tag": ("ghost", Q12_TYPE_BOOST),
    "dragon-fang": ("dragon", Q12_TYPE_BOOST),
    "black-glasses": ("dark", Q12_TYPE_BOOST),
    "metal-coat": ("steel", Q12_TYPE_BOOST),
}

TYPE_PLATES: dict[str, str] = {
    "blank-plate": "normal",
    "flame-plate": "fire",
    "splash-plate": "water",
    "zap-plate": "electric",
    "meadow-plate": "grass",
    "icicle-plate": "ice",
    "fist-plate": "fighting",
    "toxic-plate": "poison",
    "earth-plate": "ground",
    "sky-plate": "flying",
    "mind-plate": "psychic",
    "insect-plate": "bug",
    "stone-plate": "rock",
    "spooky-plate": "ghost",
    "draco-plate": "dragon",
    "dread-plate": "dark",
    "iron-plate": "steel",
    "pixie-plate": "fairy",
}

TYPE_RESIST_BERRIES: dict[str, str] = {
    "occa-berry": "fire",
    "passho-berry": "water",
    "wacan-berry": "electric",
    "rindo-berry": "grass",
    "yache-berry": "ice",
    "chople-berry": "fighting",
    "kebia-berry": "poison",
    "shuca-berry": "ground",
    "coba-berry": "flying",
    "payapa-berry": "psychic",
    "tanga-berry": "bug",
    "charti-berry": "rock",
    "kasib-berry": "ghost",
    "haban-berry": "dragon",
    "colbur-berry": "dark",
    "babiri-berry": "steel",
    "roseli-berry": "fairy",
    "chilan-berry": "normal",
}

MEGA_STONE_OVERRIDES: dict[str, str] = {
    "venusaur-mega": "venusaurite",
    "charizard-mega-x": "charizardite-x",
    "charizard-mega-y": "charizardite-y",
    "blastoise-mega": "blastoisinite",
    "beedrill-mega": "beedrillite",
    "pidgeot-mega": "pidgeotite",
    "alakazam-mega": "alakazite",
    "slowbro-mega": "slowbronite",
    "gengar-mega": "gengarite",
    "kangaskhan-mega": "kangaskhanite",
    "pinsir-mega": "pinsirite",
    "gyarados-mega": "gyaradosite",
    "aerodactyl-mega": "aerodactylite",
    "ampharos-mega": "ampharosite",
    "scizor-mega": "scizorite",
    "heracross-mega": "heracronite",
    "houndoom-mega": "houndoominite",
    "tyranitar-mega": "tyranitarite",
    "blaziken-mega": "blazikenite",
    "gardevoir-mega": "gardevoirite",
    "sableye-mega": "sablenite",
    "mawile-mega": "mawilite",
    "aggron-mega": "aggronite",
    "medicham-mega": "medichamite",
    "manectric-mega": "manectite",
    "banette-mega": "banettite",
    "absol-mega": "absolite",
    "garchomp-mega": "garchompite",
    "lucario-mega": "lucarionite",
    "abomasnow-mega": "abomasite",
    "gallade-mega": "galladite",
    "audino-mega": "audinite",
    "diancie-mega": "diancite",
}


def build_items_catalog() -> dict[str, Any]:
    return {
        "version": "gen9-champions",
        "type_boost_items": {
            item_id: {"type": type_id, "multiplier_q12": mod}
            for item_id, (type_id, mod) in sorted(TYPE_BOOST_ITEMS.items())
        },
        "type_plates": {
            item_id: {"type": type_id, "multiplier_q12": Q12_TYPE_BOOST}
            for item_id, type_id in sorted(TYPE_PLATES.items())
        },
        "species_orbs": {
            "adamant-orb": {
                "species": ["dialga"],
                "boosted_types": ["dragon", "steel"],
                "multiplier_q12": Q12_TYPE_BOOST,
            },
            "lustrous-orb": {
                "species": ["palkia"],
                "boosted_types": ["dragon", "water"],
                "multiplier_q12": Q12_TYPE_BOOST,
            },
            "griseous-orb": {
                "species": ["giratina-origin"],
                "boosted_types": ["dragon", "ghost"],
                "multiplier_q12": Q12_TYPE_BOOST,
            },
            "griseous-core": {
                "species": ["giratina-origin"],
                "boosted_types": ["dragon", "ghost"],
                "multiplier_q12": Q12_TYPE_BOOST,
            },
            "soul-dew": {
                "species": ["latios", "latias"],
                "boosted_types": ["psychic", "dragon"],
                "multiplier_q12": Q12_TYPE_BOOST,
            },
        },
        "stat_boost_items": {
            "booster-energy": {"stat": "ability_trigger", "multiplier_q12": 4096},
            "choice-band": {"stat": "atk", "multiplier_q12": Q12_CHOICE},
            "choice-specs": {"stat": "spa", "multiplier_q12": Q12_CHOICE},
            "choice-scarf": {"stat": "spe", "multiplier_q12": Q12_CHOICE},
            "life-orb": {"stat": "all_attack", "multiplier_q12": Q12_LIFE_ORB},
            "expert-belt": {
                "stat": "super_effective_only",
                "multiplier_q12": Q12_TYPE_BOOST,
            },
            "muscle-band": {"stat": "atk_move", "multiplier_q12": Q12_SMALL_BOOST},
            "wise-glasses": {"stat": "spa_move", "multiplier_q12": Q12_SMALL_BOOST},
        },
        "defensive_items": {
            "eviolite": {
                "stats": ["def", "spd"],
                "multiplier_q12": Q12_CHOICE,
                "requires_nfe": True,
            },
            "assault-vest": {"stats": ["spd"], "multiplier_q12": Q12_CHOICE},
        },
        "species_stat_items": {
            "light-ball": {
                "species": ["pikachu"],
                "stats": ["atk", "spa"],
                "multiplier_q12": Q12_DOUBLE,
            },
            "thick-club": {
                "species": ["cubone", "marowak", "marowak-alola"],
                "stats": ["atk"],
                "multiplier_q12": Q12_DOUBLE,
            },
            "metal-powder": {
                "species": ["ditto"],
                "stats": ["def"],
                "multiplier_q12": Q12_DOUBLE,
                "untransformed_only": True,
            },
            "quick-powder": {
                "species": ["ditto"],
                "stats": ["spe"],
                "multiplier_q12": Q12_DOUBLE,
                "untransformed_only": True,
            },
            "deep-sea-tooth": {
                "species": ["clamperl"],
                "stats": ["spa"],
                "multiplier_q12": Q12_DOUBLE,
            },
            "deep-sea-scale": {
                "species": ["clamperl"],
                "stats": ["spd"],
                "multiplier_q12": Q12_DOUBLE,
            },
        },
        "type_resist_berries": {
            item_id: {
                "resist_type": type_id,
                **({"always_resist": True} if item_id == "chilan-berry" else {}),
            }
            for item_id, type_id in sorted(TYPE_RESIST_BERRIES.items())
        },
    }


def _default_stone_name(mega_id: str) -> str:
    base = mega_id.removesuffix("-mega")
    if mega_id.endswith("-mega-x"):
        base = mega_id.removesuffix("-mega-x")
        return f"{base}ite-x"
    if mega_id.endswith("-mega-y"):
        base = mega_id.removesuffix("-mega-y")
        return f"{base}ite-y"
    return f"{base}ite"


def build_mega_stones() -> dict[str, Any]:
    roster = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    mega_stones: dict[str, dict[str, str]] = {}
    for species in roster["species"]:
        base = species["name_en"]
        for mega in species.get("mega_evolutions", []):
            mega_id = mega["mega_id"]
            stone_id = MEGA_STONE_OVERRIDES.get(mega_id, _default_stone_name(mega_id))
            mega_stones[stone_id] = {"base": base, "mega_form": mega_id}

    return {
        "version": "champions-2026",
        "mega_stones": dict(sorted(mega_stones.items())),
        "primal_orbs": {
            "red-orb": {"base": "groudon", "primal_form": "groudon-primal"},
            "blue-orb": {"base": "kyogre", "primal_form": "kyogre-primal"},
        },
        "rayquaza_mega": {
            "trigger": "knows-dragon-ascent",
            "base": "rayquaza",
            "mega_form": "rayquaza-mega",
        },
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(ITEMS_PATH, build_items_catalog())
    write_json(MEGA_STONES_PATH, build_mega_stones())
    print(f"wrote {ITEMS_PATH}")
    print(f"wrote {MEGA_STONES_PATH}")


if __name__ == "__main__":
    main()
