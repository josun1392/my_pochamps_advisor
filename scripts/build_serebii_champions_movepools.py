from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.champions_move_overrides import ChampionsMoveOverrides  # noqa: E402


ROSTER_PATH = PROJECT_ROOT / "data" / "static" / "champions_roster.json"
OUT_DIR = PROJECT_ROOT / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"
SEREBII_BASE_URL = "https://www.serebii.net/pokedex-champions"
USER_AGENT = "PokemonCopilot/0.1 (educational Champions movepool cache builder)"


@dataclass(frozen=True)
class MovepoolTarget:
    entity_id: str
    species_id: str
    form_type: str
    table_label: str
    source_url: str
    notes: list[str]


@dataclass(frozen=True)
class ParsedMove:
    move_id: str
    name_en: str
    move_type: str | None
    category: str | None
    power: int | None
    accuracy: int | None
    pp: int | None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Serebii-derived Pokemon Champions movepool cache.")
    parser.add_argument("--only", nargs="*", help="Optional entity ids to rebuild.")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between Serebii page requests.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    roster = _load_json(ROSTER_PATH)
    targets = _build_targets(roster)
    if args.only:
        only = set(args.only)
        targets = [target for target in targets if target.entity_id in only]

    page_cache: dict[str, dict[str, list[ParsedMove]]] = {}
    failures: list[dict[str, str]] = []
    written: list[str] = []
    overrides = ChampionsMoveOverrides()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    fetched_at = _timestamp()

    for target in targets:
        try:
            tables = page_cache.get(target.species_id)
            if tables is None:
                tables = _fetch_and_parse_tables(session, target.source_url)
                page_cache[target.species_id] = tables
                time.sleep(args.delay)
            moves = _select_table(tables, target.table_label)
            if moves is None:
                available_labels = ", ".join(sorted(tables)) or "<none>"
                raise ValueError(f"table not found: {target.table_label}; available: {available_labels}")
            payload = _cache_payload(target, moves, overrides, fetched_at)
            _write_json(OUT_DIR / f"{target.entity_id}.json", payload)
            written.append(target.entity_id)
        except Exception as exc:  # noqa: BLE001
            _write_json(OUT_DIR / f"{target.entity_id}.json", _unavailable_payload(target, fetched_at, exc))
            written.append(target.entity_id)
            failures.append(
                {
                    "entity_id": target.entity_id,
                    "source_url": target.source_url,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    _write_json(OUT_DIR.parent / "_index.json", {"pokemon_movepools": sorted(written)})
    _write_json(
        OUT_DIR.parent / "_meta.json",
        {
            "format": "pokemon_champions",
            "regulation": "M-A",
            "source": "serebii_champions_pokedex",
            "source_base_url": SEREBII_BASE_URL,
            "generated_at": fetched_at,
            "target_count": len(targets),
            "written_count": len(written),
            "failure_count": len(failures),
        },
    )
    _write_json(OUT_DIR.parent / "_failures.json", {"failures": failures})

    print(f"written: {len(written)}/{len(targets)}")
    print(f"failures: {len(failures)}")
    if failures:
        for failure in failures[:20]:
            print(f"- {failure['entity_id']}: {failure['error']}")
    return 0


def _build_targets(roster: dict[str, Any]) -> list[MovepoolTarget]:
    targets: dict[str, MovepoolTarget] = {}
    for species in roster["species"]:
        species_id = species["name_en"]
        source_slug = _source_slug(species_id)
        source_url = f"{SEREBII_BASE_URL}/{source_slug}/"
        for form in species["forms"]:
            entity_id = form["form_id"]
            form_name = form.get("form_name_en", "")
            is_default = form.get("is_default") is True
            table_label = _table_label_for_form(entity_id, species_id, form_name, is_default)
            notes = _notes_for_target(entity_id, species_id, table_label)
            targets.setdefault(
                entity_id,
                MovepoolTarget(
                    entity_id=entity_id,
                    species_id=species_id,
                    form_type="default" if is_default else "form",
                    table_label=table_label,
                    source_url=source_url,
                    notes=notes,
                ),
            )
        for mega in species["mega_evolutions"]:
            entity_id = mega["mega_id"]
            table_label = _table_label_for_form(entity_id, species_id, "", is_default=False)
            targets.setdefault(
                entity_id,
                MovepoolTarget(
                    entity_id=entity_id,
                    species_id=species_id,
                    form_type="mega",
                    table_label=table_label,
                    source_url=source_url,
                    notes=[
                        "Mega form uses the base species Champions move table; Mega-specific stats/items remain separate.",
                    ],
                ),
            )
    return [targets[key] for key in sorted(targets)]


def _table_label_for_form(entity_id: str, species_id: str, form_name: str, is_default: bool) -> str:
    normalized_form = form_name.casefold()
    if entity_id == "basculegion-male":
        return "Standard Moves - Male"
    if entity_id == "basculegion-female":
        return "Standard Moves - Female"
    if entity_id == "meowstic-male":
        return "Standard Moves - Male"
    if entity_id == "meowstic-female":
        return "Standard Moves - Female"
    if entity_id == "meowstic-mega":
        return "Standard Moves - Male"
    if entity_id in {"floette-eternal", "floette-mega"}:
        return "Standard Moves - Eternal Floette"
    if is_default or entity_id == species_id:
        return "Standard Moves"
    if "hisui" in entity_id or "hisuian" in normalized_form:
        return "Hisuian Form Standard Moves"
    if "alola" in entity_id or "alolan" in normalized_form:
        return "Alola Form Standard Moves"
    if "galar" in entity_id or "galarian" in normalized_form:
        return "Galarian Form Standard Moves"
    if entity_id == "tauros-paldea-combat-breed":
        return "Paldean Form Standard Moves"
    if entity_id == "tauros-paldea-blaze-breed":
        return "Standard Moves - Blaze Breed"
    if entity_id == "tauros-paldea-aqua-breed":
        return "Standard Moves - Aqua Breed"
    if entity_id == "lycanroc-midnight":
        return "Standard Moves - Midnight Form"
    if entity_id == "lycanroc-dusk":
        return "Standard Moves - Dusk Form"
    return "Standard Moves"


def _source_slug(species_id: str) -> str:
    return {
        "floette-eternal": "floette",
        "mr-rime": "mr.rime",
    }.get(species_id, species_id)


def _notes_for_target(entity_id: str, species_id: str, table_label: str) -> list[str]:
    notes = [
        "Serebii Champions Pokédex is used as the legality source.",
        "PokeAPI pokemon learnset is not used as a Champions legality source.",
        "PokeAPI move cache is used only for move metadata.",
    ]
    if table_label == "Standard Moves" and entity_id != species_id:
        notes.append("No separate Serebii form move table was selected for this entity.")
    return notes


def _fetch_and_parse_tables(session: requests.Session, url: str) -> dict[str, list[ParsedMove]]:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    tables: dict[str, list[ParsedMove]] = {}
    for heading in soup.find_all("h3"):
        label = _squash_space(heading.get_text(" ", strip=True))
        if "Standard Moves" not in label:
            continue
        table = heading.find_parent("table")
        if table is None:
            continue
        tables[label] = _parse_move_table(table)
    return tables


def _parse_move_table(table) -> list[ParsedMove]:
    moves: list[ParsedMove] = []
    seen: set[str] = set()
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 7:
            continue
        name = _squash_space(cells[0].get_text(" ", strip=True))
        if not name or name == "Attack Name":
            continue
        move_id = _move_id(name)
        if not move_id or move_id in seen:
            continue
        moves.append(
            ParsedMove(
                move_id=move_id,
                name_en=name,
                move_type=_type_from_cell(cells[1]),
                category=_category_from_cell(cells[2]),
                power=_optional_int(cells[3].get_text(" ", strip=True)),
                accuracy=_optional_int(cells[4].get_text(" ", strip=True)),
                pp=_optional_int(cells[5].get_text(" ", strip=True)),
            )
        )
        seen.add(move_id)
    return moves


def _cache_payload(
    target: MovepoolTarget,
    moves: list[ParsedMove],
    overrides: ChampionsMoveOverrides,
    fetched_at: str,
) -> dict[str, Any]:
    denied = overrides.denied_move_ids()
    allowed_moves = [move for move in moves if move.move_id not in denied]
    excluded_moves = [
        {
            "move_id": move_id,
            "reason": "globally_denied_in_champions_override",
            "source_refs": ["champions_move_overrides"],
        }
        for move_id in sorted(denied)
        if move_id in {move.move_id for move in moves} or move_id == "tera-blast"
    ]
    return {
        "pokemon_id": target.entity_id,
        "format": "pokemon_champions",
        "regulation": "M-A",
        "source_kind": "pokemon_movepool",
        "source_table": target.table_label,
        "moves": [
            {
                "move_id": move.move_id,
                "name_en": move.name_en,
                "type": move.move_type,
                "category": move.category,
                "power": move.power,
                "accuracy": move.accuracy,
                "pp": move.pp,
                "source_refs": ["serebii"],
                "confidence": "third_party_primary",
                "metadata_source": "pokeapi",
            }
            for move in allowed_moves
        ],
        "excluded_moves": excluded_moves,
        "fetched_at": fetched_at,
        "source_refs": {
            "primary": [
                {
                    "source": "serebii",
                    "url": target.source_url,
                    "table": target.table_label,
                }
            ],
            "metadata": ["pokeapi"],
        },
        "notes": target.notes,
    }


def _unavailable_payload(target: MovepoolTarget, fetched_at: str, exc: Exception) -> dict[str, Any]:
    return {
        "pokemon_id": target.entity_id,
        "format": "pokemon_champions",
        "regulation": "M-A",
        "source_kind": "pokemon_movepool",
        "status": "unavailable_source_error",
        "source_table": target.table_label,
        "moves": [],
        "excluded_moves": [],
        "fetched_at": fetched_at,
        "source_refs": {
            "primary": [
                {
                    "source": "serebii",
                    "url": target.source_url,
                    "table": target.table_label,
                }
            ],
            "metadata": ["pokeapi"],
        },
        "notes": [
            *target.notes,
            f"Serebii Champions movepool could not be parsed for this entity: {type(exc).__name__}: {exc}",
        ],
    }


def _select_table(tables: dict[str, list[ParsedMove]], preferred_label: str) -> list[ParsedMove] | None:
    if preferred_label in tables:
        return tables[preferred_label]
    if preferred_label != "Standard Moves":
        return None
    return tables.get("Standard Moves")


def _type_from_cell(cell) -> str | None:
    for image in cell.find_all("img"):
        alt = image.get("alt")
        if not isinstance(alt, str):
            continue
        match = re.search(r"- ([A-Za-z]+)-type", alt)
        if match:
            return match.group(1).casefold()
    return None


def _category_from_cell(cell) -> str | None:
    for image in cell.find_all("img"):
        alt = image.get("alt")
        if not isinstance(alt, str):
            continue
        match = re.search(r": ([A-Za-z]+) Move", alt)
        if match:
            category = match.group(1).casefold()
            return "status" if category == "other" else category
    return None


def _move_id(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold().replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.isdigit() else None


def _squash_space(value: str) -> str:
    return " ".join(value.split())


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
