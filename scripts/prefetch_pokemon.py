from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache_manager import CacheManager  # noqa: E402
from core.pokeapi_fetcher import PokeAPIFetcher  # noqa: E402


TIER_S_POKEMON = [
    "garchomp",
    "landorus-therian",
    "kingambit",
    "great-tusk",
    "gholdengo",
    "iron-valiant",
    "dragapult",
    "heatran",
    "rotom-wash",
    "ferrothorn",
    "tornadus-therian",
    "zapdos",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="PokeAPI 데이터를 로컬 캐시에 미리 다운로드합니다.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tier", choices=["s"], help="미리 정의된 메타 포켓몬 묶음")
    group.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help="포켓몬 ID 범위")
    group.add_argument("--pokemon", nargs="+", help="포켓몬 이름 또는 ID")
    parser.add_argument("--with-deps", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--force", action="store_true", help="이미 캐시된 항목도 다시 다운로드")
    args = parser.parse_args()

    cache = CacheManager(PROJECT_ROOT / "data" / "cache" / "pokeapi")
    fetcher = PokeAPIFetcher(cache)
    targets = _build_targets(args)

    for index, identifier in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] pokemon/{identifier}")
        pokemon = _get_or_fetch(
            cache=cache,
            fetcher=fetcher,
            category="pokemon",
            endpoint="pokemon",
            identifier=identifier,
            getter=fetcher.get_pokemon,
            normalizer=fetcher._normalize_pokemon,
            force=args.force,
        )
        if args.with_deps:
            _prefetch_dependencies(cache, fetcher, pokemon, force=args.force)

    print(f"cache stats: {cache.stats()}")
    return 0


def _build_targets(args: argparse.Namespace) -> list[int | str]:
    if args.tier == "s":
        return TIER_S_POKEMON
    if args.range:
        start, end = args.range
        if start > end:
            raise ValueError("--range START는 END보다 작거나 같아야 합니다.")
        return list(range(start, end + 1))
    return args.pokemon


def _prefetch_dependencies(
    cache: CacheManager,
    fetcher: PokeAPIFetcher,
    pokemon: dict,
    force: bool,
) -> None:
    for type_name in pokemon.get("types", []):
        _get_or_fetch(cache, fetcher, "types", "type", type_name, fetcher.get_type, fetcher._normalize_type, force)

    for ability in pokemon.get("abilities", []):
        ability_name = ability.get("name")
        if ability_name:
            _get_or_fetch(
                cache,
                fetcher,
                "abilities",
                "ability",
                ability_name,
                fetcher.get_ability,
                fetcher._normalize_ability,
                force,
            )

    moves = pokemon.get("moves", [])
    for index, move_name in enumerate(moves, start=1):
        print(f"  deps moves [{index}/{len(moves)}] {move_name}")
        _get_or_fetch(cache, fetcher, "moves", "move", move_name, fetcher.get_move, fetcher._normalize_move, force)


def _get_or_fetch(
    cache: CacheManager,
    fetcher: PokeAPIFetcher,
    category: str,
    endpoint: str,
    identifier: int | str,
    getter: Callable[[int | str], dict],
    normalizer: Callable[[dict], dict],
    force: bool,
) -> dict:
    if not force:
        cached = cache.get(category, identifier)
        if cached is not None:
            print(f"  {category}/{identifier}: skipped (cached)")
            return cached

    if force:
        raw = fetcher._fetch(endpoint, identifier)
        data = normalizer(raw)
        cache.put(category, int(data["id"]), data)
    else:
        data = getter(identifier)

    print(f"  {category}/{identifier}: downloaded -> {data['id']}.json")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
