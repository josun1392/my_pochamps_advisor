from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache_manager import CacheManager  # noqa: E402
from core.pokeapi_fetcher import PokeAPIFetcher  # noqa: E402


BULBAPEDIA_URL = "https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_in_Pok%C3%A9mon_Champions"
SEREBII_URL = "https://www.serebii.net/pokemonchampions/pokemon.shtml"
OFFICIAL_URL = "https://champions.pokemon.com/en-us/"
OUTPUT_PATH = PROJECT_ROOT / "data" / "static" / "champions_roster.json"

TYPE_NAMES = {
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
}

FORM_ID_OVERRIDES = {
    "tauros paldean form combat breed": ("tauros-paldea-combat-breed", True),
    "tauros paldean form blaze breed": ("tauros-paldea-blaze-breed", True),
    "tauros paldean form aqua breed": ("tauros-paldea-aqua-breed", True),
    "raichu alolan form": ("raichu-alola", True),
    "ninetales alolan form": ("ninetales-alola", True),
    "arcanine hisuian form": ("arcanine-hisui", True),
    "slowbro galarian form": ("slowbro-galar", True),
    "slowking galarian form": ("slowking-galar", True),
    "typhlosion hisuian form": ("typhlosion-hisui", True),
    "samurott hisuian form": ("samurott-hisui", True),
    "zoroark hisuian form": ("zoroark-hisui", True),
    "stunfisk galarian form": ("stunfisk-galar", True),
    "goodra hisuian form": ("goodra-hisui", True),
    "decidueye hisuian form": ("decidueye-hisui", True),
    "avalugg hisuian form": ("avalugg-hisui", True),
    "rotom rotom": ("rotom", True),
    "rotom heat rotom": ("rotom-heat", True),
    "rotom wash rotom": ("rotom-wash", True),
    "rotom frost rotom": ("rotom-frost", True),
    "rotom fan rotom": ("rotom-fan", True),
    "rotom mow rotom": ("rotom-mow", True),
    "floette eternal flower": ("floette-eternal", True),
    "meowstic male": ("meowstic-male", True),
    "meowstic female": ("meowstic-female", True),
    "gourgeist medium variety": ("gourgeist-average", True),
    "gourgeist small variety": ("gourgeist-small", True),
    "gourgeist large variety": ("gourgeist-large", True),
    "gourgeist jumbo variety": ("gourgeist-super", True),
    "lycanroc midday form": ("lycanroc-midday", True),
    "lycanroc midnight form": ("lycanroc-midnight", True),
    "lycanroc dusk form": ("lycanroc-dusk", True),
    "basculegion male": ("basculegion-male", True),
    "basculegion female": ("basculegion-female", True),
    "maushold": ("maushold-family-of-four", True),
    "maushold family of four": ("maushold-family-of-four", True),
    "palafin": ("palafin-zero", True),
    "palafin hero form": ("palafin-hero", True),
    "aegislash": ("aegislash-shield", True),
    "aegislash blade forme": ("aegislash-blade", True),
    "morpeko": ("morpeko-full-belly", True),
    "morpeko hangry mode": ("morpeko-hangry", True),
}

COSMETIC_BASES = {
    "vivillon",
    "furfrou",
    "alcremie",
    "florges",
}


@dataclass(frozen=True)
class ParsedRow:
    national_dex: int
    base_display: str
    display_name: str
    types: list[str]
    availability: str
    version_added: str
    table_kind: str


def main() -> int:
    cache = CacheManager(PROJECT_ROOT / "data" / "cache" / "pokeapi")
    fetcher = PokeAPIFetcher(cache)
    soup = BeautifulSoup(requests.get(BULBAPEDIA_URL, timeout=30).text, "html.parser")
    tables = soup.find_all("table")

    roster_rows = _parse_rows(tables[0], "regular") + _parse_rows(tables[3], "untransferable")
    other_form_rows = _parse_rows(tables[2], "other_form")
    mega_rows = _parse_rows(tables[1], "mega")

    species_by_dex = _build_species(fetcher, roster_rows)
    _attach_forms(fetcher, species_by_dex, other_form_rows)
    _attach_megas(species_by_dex, mega_rows)

    species = []
    for dex in sorted(species_by_dex):
        item = species_by_dex[dex]
        item.pop("pokeapi_species", None)
        species.append(item)
    form_variants = sum(max(0, len(item["forms"]) - 1) for item in species)
    mega_count = sum(len(item["mega_evolutions"]) for item in species)
    roster = {
        "format": "champions",
        "roster_version": "Regular Roster M-A",
        "valid_until": "2026-06-16",
        "extracted_at": date.today().isoformat(),
        "data_source": {
            "primary": BULBAPEDIA_URL,
            "cross_check": SEREBII_URL,
            "official_reference": OFFICIAL_URL,
        },
        "counts": {
            "species": len(species),
            "form_variants": form_variants,
            "mega_evolutions": mega_count,
            "total_battle_entities": len(species) + form_variants + mega_count,
        },
        "species": species,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(roster, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"species: {len(species)}")
    print(f"form_variants: {form_variants}")
    print(f"mega_evolutions: {mega_count}")
    print(f"wrote {OUTPUT_PATH}")
    return 0


def _parse_rows(table: Tag, table_kind: str) -> list[ParsedRow]:
    rows: list[ParsedRow] = []
    current_dex = 0
    current_base = ""
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["th", "td"])
        texts = [cell.get_text(" ", strip=True) for cell in cells]
        if not texts:
            continue
        if texts[0].startswith("#"):
            current_dex = int(texts[0].replace("#", ""))
            current_base = _pokemon_link_text(cells) or texts[2]
            pokemon_index = 2
        else:
            pokemon_index = 1 if texts[0] == "" and len(texts) > 1 else 0
        display_name = texts[pokemon_index]
        tail = texts[pokemon_index + 1 :]
        availability = tail[-2]
        version_added = tail[-1]
        types = [value.lower() for value in tail[:-2] if value.lower() in TYPE_NAMES]
        rows.append(
            ParsedRow(
                national_dex=current_dex,
                base_display=current_base,
                display_name=display_name,
                types=types,
                availability=availability,
                version_added=version_added,
                table_kind=table_kind,
            )
        )
    return rows


def _build_species(fetcher: PokeAPIFetcher, rows: list[ParsedRow]) -> dict[int, dict[str, Any]]:
    species_by_dex: dict[int, dict[str, Any]] = {}
    for row in rows:
        species = fetcher.get_species(row.national_dex)
        name_en = _species_name_en(row, species)
        name_ko = species.get("names", {}).get("ko") or name_en
        availability = _availability(row.availability)
        entry = species_by_dex.setdefault(
            row.national_dex,
            {
                "national_dex": row.national_dex,
                "name_en": name_en,
                "name_ko": name_ko,
                "pokeapi_species": species["name"],
                "types": row.types,
                "version_added": row.version_added,
                "availability": availability,
                "forms": [],
                "mega_evolutions": [],
                "available_gimmicks": ["tera"],
            },
        )
        if availability == "transfer_only":
            entry["availability"] = "transfer_only"
        if name_en == "floette-eternal":
            entry["availability"] = "transfer_only"
            entry["transfer_note"] = "Must be transferred from Legends: Z-A through HOME"

        form = _form_from_row(row, species)
        form["is_default"] = not entry["forms"]
        entry["forms"].append(form)
    return species_by_dex


def _attach_forms(
    fetcher: PokeAPIFetcher,
    species_by_dex: dict[int, dict[str, Any]],
    rows: list[ParsedRow],
) -> None:
    for row in rows:
        species = fetcher.get_species(row.national_dex)
        entry = species_by_dex[row.national_dex]
        entry["forms"].append(_form_from_row(row, species))
        if _availability(row.availability) == "transfer_only" and entry["availability"] == "normal":
            entry.setdefault("form_availability_note", "Some cosmetic forms are transfer only")


def _attach_megas(species_by_dex: dict[int, dict[str, Any]], rows: list[ParsedRow]) -> None:
    for row in rows:
        if row.national_dex not in species_by_dex:
            continue
        entry = species_by_dex[row.national_dex]
        mega_id = _mega_id(row.display_name, entry["pokeapi_species"])
        entry["mega_evolutions"].append(
            {
                "mega_id": mega_id,
                "mega_name_en": _mega_display_name(row.display_name),
                "mega_name_ko": _mega_name_ko(entry["name_ko"], mega_id),
                "types": row.types,
                "required_item": _mega_item(mega_id),
            }
        )
        if "mega" not in entry["available_gimmicks"]:
            entry["available_gimmicks"].insert(0, "mega")


def _form_from_row(row: ParsedRow, species: dict[str, Any]) -> dict[str, Any]:
    form_id, supported = _resolve_form_id(row.display_name, species)
    form_name_en = _form_name_en(row.display_name, species.get("name", ""))
    return {
        "form_id": form_id,
        "form_name_en": form_name_en,
        "form_name_ko": _form_name_ko(form_name_en),
        "types": row.types,
        "is_default": False,
        "availability": _availability(row.availability),
        "pokeapi_supported": supported,
    }


def _resolve_form_id(display_name: str, species: dict[str, Any]) -> tuple[str, bool]:
    key = display_name.casefold()
    if key in FORM_ID_OVERRIDES:
        return FORM_ID_OVERRIDES[key]
    species_name = species["name"]
    varieties = species.get("varieties", [])
    if _slug(display_name) == species_name:
        default = next((item["name"] for item in varieties if item.get("is_default")), species_name)
        return default, True
    if species_name in COSMETIC_BASES:
        return species_name, False
    default = next((item["name"] for item in varieties if item.get("is_default")), species_name)
    return default, True


def _species_name_en(row: ParsedRow, species: dict[str, Any]) -> str:
    if row.national_dex == 670 and "Eternal Flower" in row.display_name:
        return "floette-eternal"
    return species["name"]


def _form_name_en(display_name: str, species_name: str) -> str:
    display_slug = _slug(display_name)
    if display_slug == species_name:
        return "default"
    cleaned = re.sub(r"^" + re.escape(species_name.replace("-", " ")) + r"\s*", "", display_name, flags=re.I)
    return cleaned.strip() or "default"


def _form_name_ko(form_name_en: str) -> str:
    if form_name_en == "default":
        return "기본"
    return form_name_en


def _mega_id(display_name: str, base_name_en: str) -> str:
    suffix = display_name.split("Mega", 1)[-1].strip()
    suffix_slug = _slug(suffix)
    if suffix_slug.endswith("-x"):
        return f"{base_name_en}-mega-x"
    if suffix_slug.endswith("-y"):
        return f"{base_name_en}-mega-y"
    return f"{base_name_en}-mega"


def _mega_display_name(display_name: str) -> str:
    return f"Mega {display_name.split('Mega', 1)[-1].strip()}"


def _mega_name_ko(base_ko: str, mega_id: str) -> str:
    if mega_id.endswith("-mega-x"):
        return f"메가{base_ko} X"
    if mega_id.endswith("-mega-y"):
        return f"메가{base_ko} Y"
    return f"메가{base_ko}"


def _mega_item(mega_id: str) -> str:
    base = mega_id.replace("-mega-x", "").replace("-mega-y", "").replace("-mega", "")
    if mega_id.endswith("-mega-x"):
        return f"{base}ite-x"
    if mega_id.endswith("-mega-y"):
        return f"{base}ite-y"
    return f"{base}ite"


def _availability(value: str) -> str:
    if value == "Transfer only":
        return "transfer_only"
    if value == "No":
        return "event"
    return "normal"


def _pokemon_link_text(cells: list[Tag]) -> str:
    for cell in cells:
        for link in cell.find_all("a"):
            href = link.get("href", "")
            text = link.get_text(" ", strip=True)
            if text and "_(Pok" in href:
                return text
    return ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
