from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache_manager import CacheManager  # noqa: E402
from core.ko_form_rules import FORM_SUFFIX_KO, apply_korean_form, split_pokemon_name  # noqa: E402
from core.pokeapi_fetcher import PokeAPIFetcher  # noqa: E402
from scripts.prefetch_pokemon import TIER_S_POKEMON  # noqa: E402


MAPPING_PATH = PROJECT_ROOT / "data" / "ko_mapping.json"
CATEGORIES = ("pokemon", "moves", "abilities", "types")


def main() -> int:
    parser = argparse.ArgumentParser(description="PokeAPI 캐시에서 한국어 이름 매핑을 빌드합니다.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tier", choices=["s"], help="미리 정의된 메타 포켓몬 묶음")
    group.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help="포켓몬 ID 범위")
    group.add_argument("--pokemon", nargs="+", help="포켓몬 이름 또는 ID")
    parser.add_argument("--rebuild", action="store_true", help="기존 ko_mapping.json을 무시하고 재빌드")
    args = parser.parse_args()

    cache = CacheManager(PROJECT_ROOT / "data" / "cache" / "pokeapi")
    fetcher = PokeAPIFetcher(cache)
    mapping = _empty_mapping() if args.rebuild or not MAPPING_PATH.exists() else _load_mapping()

    pokemon_targets = _pokemon_targets(args, cache)
    print(f"pokemon targets: {len(pokemon_targets)}")
    for index, identifier in enumerate(pokemon_targets, start=1):
        pokemon = fetcher.get_pokemon(identifier)
        print(f"[{index}/{len(pokemon_targets)}] pokemon/{pokemon['name']}")
        _map_pokemon(mapping, fetcher, pokemon)

    for category, getter in (
        ("moves", fetcher.get_move),
        ("abilities", fetcher.get_ability),
        ("types", fetcher.get_type),
    ):
        _map_cached_category(mapping, cache, category, getter)

    mapping["_built_at"] = _timestamp()
    _write_mapping(mapping)
    for category in CATEGORIES:
        print(f"unmapped {category}: {len(mapping['_unmapped'][category])}")
    print(f"wrote {MAPPING_PATH}")
    return 0


def _pokemon_targets(args: argparse.Namespace, cache: CacheManager) -> list[int | str]:
    if args.tier == "s":
        return TIER_S_POKEMON
    if args.range:
        start, end = args.range
        if start > end:
            raise ValueError("--range START는 END보다 작거나 같아야 합니다.")
        return list(range(start, end + 1))
    if args.pokemon:
        return args.pokemon
    return _cached_ids(cache, "pokemon")


def _map_pokemon(mapping: dict[str, Any], fetcher: PokeAPIFetcher, pokemon: dict[str, Any]) -> None:
    api_name = pokemon["name"]
    base_name, form_suffix = split_pokemon_name(api_name)
    species_id = _species_identifier(pokemon)
    species = fetcher.get_species(species_id if species_id is not None else base_name)
    base_ko = _ko_name(species)

    if not base_ko:
        _mark_unmapped(mapping, "pokemon", api_name)
        return
    if form_suffix not in FORM_SUFFIX_KO:
        _mark_unmapped(mapping, "pokemon", api_name)

    mapping["pokemon"][api_name] = apply_korean_form(base_ko, form_suffix)


def _map_cached_category(
    mapping: dict[str, Any],
    cache: CacheManager,
    category: str,
    getter: Any,
) -> None:
    for identifier in _cached_ids(cache, category):
        data = getter(identifier)
        data = _ensure_localized_names(cache, category, identifier, data)
        ko_name = _ko_name(data)
        en_name = data.get("name")
        if isinstance(en_name, str) and ko_name:
            mapping[category][en_name] = ko_name
        elif isinstance(en_name, str):
            _mark_unmapped(mapping, category, en_name)


def _ensure_localized_names(
    cache: CacheManager,
    category: str,
    identifier: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(data.get("names"), dict):
        return data

    endpoint_by_category = {
        "moves": "move",
        "abilities": "ability",
        "types": "type",
    }
    normalizer_by_category = {
        "moves": PokeAPIFetcher._normalize_move,
        "abilities": PokeAPIFetcher._normalize_ability,
        "types": PokeAPIFetcher._normalize_type,
    }
    endpoint = endpoint_by_category[category]
    normalizer = normalizer_by_category[category]
    fetcher = PokeAPIFetcher(cache)
    normalized = normalizer(fetcher._fetch(endpoint, identifier))
    cache.put(category, int(normalized["id"]), normalized)
    return normalized


def _ko_name(data: dict[str, Any]) -> str | None:
    names = data.get("names")
    if isinstance(names, dict):
        value = names.get("ko")
        return value if isinstance(value, str) and value else None
    return None


def _species_identifier(pokemon: dict[str, Any]) -> int | None:
    species_url = pokemon.get("species_url")
    if not isinstance(species_url, str):
        return None
    return int(species_url.rstrip("/").split("/")[-1])


def _cached_ids(cache: CacheManager, category: str) -> list[int]:
    directory = cache.cache_root / category
    if not directory.exists():
        return []
    return sorted(int(path.stem) for path in directory.glob("*.json") if path.stem.isdigit())


def _mark_unmapped(mapping: dict[str, Any], category: str, name: str) -> None:
    entries = mapping["_unmapped"][category]
    if name not in entries:
        entries.append(name)


def _empty_mapping() -> dict[str, Any]:
    return {
        "_built_at": None,
        "_version": 1,
        "pokemon": {},
        "moves": {},
        "abilities": {},
        "types": {},
        "_unmapped": {
            "pokemon": [],
            "moves": [],
            "abilities": [],
            "types": [],
        },
    }


def _load_mapping() -> dict[str, Any]:
    with MAPPING_PATH.open("r", encoding="utf-8") as file:
        mapping = json.load(file)
    for category in CATEGORIES:
        mapping.setdefault(category, {})
        mapping.setdefault("_unmapped", {}).setdefault(category, [])
    return mapping


def _write_mapping(mapping: dict[str, Any]) -> None:
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MAPPING_PATH.open("w", encoding="utf-8") as file:
        json.dump(mapping, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
