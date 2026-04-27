from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.cache_config import (  # noqa: E402
    CACHE_DIR,
    CONCURRENT_LIMIT,
    MAX_RETRIES,
    POKEAPI_BASE,
    POKEMON_CACHE_META,
    POKEMON_FAILURE_LOG,
    REQUEST_DELAY_MS,
)


ROSTER_PATH = PROJECT_ROOT / "data" / "static" / "champions_roster.json"
MANUAL_KO_PATH = PROJECT_ROOT / "data" / "static" / "manual_ko_names.json"
STAT_MAP = {
    "hp": "hp",
    "attack": "atk",
    "defense": "def",
    "special-attack": "spa",
    "special-defense": "spd",
    "speed": "spe",
}
GEN9_VERSION_GROUPS = {"scarlet-violet"}
MOVE_METHOD_MAP = {
    "level-up": "level_up",
    "machine": "machine",
    "tutor": "tutor",
    "egg": "egg",
}


@dataclass(frozen=True)
class EntityTarget:
    entity_id: str
    pokeapi_slug: str
    species: str
    species_dex: int
    form_type: str
    name_en: str
    name_ko: str
    availability: str


async def main(force: bool = False, only: list[str] | None = None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    roster = _load_json(ROSTER_PATH)
    manual_ko = _load_json(MANUAL_KO_PATH)
    targets = _build_targets(roster, manual_ko)
    if only:
        only_set = set(only)
        targets = [target for target in targets if target.entity_id in only_set]

    index: dict[str, str] = {}
    skipped = 0
    failures: list[str] = []
    lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    ability_cache: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(base_url=POKEAPI_BASE, timeout=20.0) as client:
        progress = tqdm(targets, desc="prefetch champions pokemon", unit="entity")

        async def run_target(target: EntityTarget) -> None:
            nonlocal skipped
            cache_path = CACHE_DIR / f"{target.entity_id}.json"
            if cache_path.exists() and not force:
                async with lock:
                    index[target.entity_id] = str(cache_path.as_posix())
                    skipped += 1
                return

            try:
                data = await _fetch_entity(client, semaphore, ability_cache, target)
                _write_json(cache_path, data)
                if cache_path.stat().st_size > 50 * 1024:
                    print(f"WARNING: cache file over 50KB: {cache_path}")
                async with lock:
                    index[target.entity_id] = str(cache_path.as_posix())
            except Exception as exc:  # noqa: BLE001
                async with lock:
                    failures.append(f"{target.entity_id}: {type(exc).__name__}: {exc}")
            finally:
                progress.update(1)

        await asyncio.gather(*(run_target(target) for target in targets))
        progress.close()

    _write_json(CACHE_DIR / "_index.json", dict(sorted(index.items())))
    _write_meta(roster, len(targets), len(index), skipped, failures)
    _write_failures(failures)
    if skipped:
        print(f"Skipping cached: {skipped} entities.")
    print(f"pokemon entities: {len(index)}/{len(targets)}")
    print(f"failures: {len(failures)}")


async def _fetch_entity(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    ability_cache: dict[str, dict[str, Any]],
    target: EntityTarget,
) -> dict[str, Any]:
    pokemon = await _get_json(client, semaphore, f"/pokemon/{target.pokeapi_slug}/")
    abilities = []
    for item in pokemon.get("abilities", []):
        ability_name = item["ability"]["name"]
        if ability_name not in ability_cache:
            ability_cache[ability_name] = await _get_json(client, semaphore, f"/ability/{ability_name}/")
        ability_data = ability_cache[ability_name]
        abilities.append(
            {
                "name": ability_name,
                "name_ko": _localized_name(ability_data) or ability_name,
                "is_hidden": bool(item.get("is_hidden", False)),
                "slot": item.get("slot"),
            }
        )

    return {
        "entity_id": target.entity_id,
        "species": target.species,
        "form_type": target.form_type,
        "pokeapi_id": pokemon["id"],
        "name": {
            "en": target.name_en,
            "ko": target.name_ko or target.name_en,
        },
        "types": [
            item["type"]["name"]
            for item in sorted(pokemon.get("types", []), key=lambda value: value.get("slot", 0))
        ],
        "base_stats": {
            STAT_MAP[item["stat"]["name"]]: item["base_stat"]
            for item in pokemon.get("stats", [])
            if item["stat"]["name"] in STAT_MAP
        },
        "abilities": abilities,
        "weight_kg": pokemon["weight"] / 10,
        "height_m": pokemon["height"] / 10,
        "movepool": _movepool(pokemon),
        "sprites": {
            "front_default": pokemon.get("sprites", {}).get("front_default"),
            "front_shiny": pokemon.get("sprites", {}).get("front_shiny"),
        },
        "availability": target.availability,
        "fetched_at": _timestamp(),
        "pokeapi_version": "v2",
    }


async def _get_json(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, path: str) -> dict[str, Any]:
    async with semaphore:
        await asyncio.sleep(REQUEST_DELAY_MS / 1000)
        for attempt in range(MAX_RETRIES + 1):
            response = await client.get(path)
            if response.status_code in {429, 503} and attempt < MAX_RETRIES:
                await asyncio.sleep(2**attempt)
                continue
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError(f"PokeAPI response is not an object: {path}")
            return data
    raise RuntimeError(f"PokeAPI request failed: {path}")


def _movepool(pokemon: dict[str, Any]) -> dict[str, list[str]]:
    pools: dict[str, set[str]] = {
        "level_up": set(),
        "machine": set(),
        "tutor": set(),
        "egg": set(),
    }
    for move in pokemon.get("moves", []):
        move_name = move["move"]["name"]
        for detail in move.get("version_group_details", []):
            version_group = detail.get("version_group", {}).get("name")
            method = detail.get("move_learn_method", {}).get("name")
            if version_group in GEN9_VERSION_GROUPS and method in MOVE_METHOD_MAP:
                pools[MOVE_METHOD_MAP[method]].add(move_name)
    return {key: sorted(values) for key, values in pools.items()}


def _build_targets(roster: dict[str, Any], manual_ko: dict[str, Any]) -> list[EntityTarget]:
    targets: dict[str, EntityTarget] = {}
    for species in roster["species"]:
        for form in species["forms"]:
            if form.get("pokeapi_supported") is not True:
                continue
            entity_id = form["form_id"]
            form_type = "default" if form.get("is_default") else "form"
            name_ko = _form_ko_name(species, form, manual_ko)
            targets[entity_id] = EntityTarget(
                entity_id=entity_id,
                pokeapi_slug=entity_id,
                species=species["name_en"],
                species_dex=species["national_dex"],
                form_type=form_type,
                name_en=_form_en_name(species, form),
                name_ko=name_ko,
                availability=form.get("availability", species["availability"]),
            )
        for mega in species["mega_evolutions"]:
            entity_id = mega["mega_id"]
            targets[entity_id] = EntityTarget(
                entity_id=entity_id,
                pokeapi_slug=entity_id,
                species=species["name_en"],
                species_dex=species["national_dex"],
                form_type="mega",
                name_en=mega["mega_name_en"],
                name_ko=mega["mega_name_ko"],
                availability=species["availability"],
            )
    return [targets[key] for key in sorted(targets)]


def _form_en_name(species: dict[str, Any], form: dict[str, Any]) -> str:
    if form.get("is_default"):
        return species["name_en"]
    return f"{species['name_en']} {form['form_name_en']}"


def _form_ko_name(species: dict[str, Any], form: dict[str, Any], manual_ko: dict[str, Any]) -> str:
    if form.get("is_default"):
        return species["name_ko"]
    form_name = form["form_name_en"]
    form_key = form_name.casefold().replace(" ", "-")
    form_ko = manual_ko.get("forms", {}).get(form_key)
    if form_ko:
        return f"{species['name_ko']} {form_ko}"
    return f"{species['name_ko']} {form_name}"


def _localized_name(data: dict[str, Any]) -> str | None:
    for item in data.get("names", []):
        if item.get("language", {}).get("name") == "ko":
            value = item.get("name")
            return value if isinstance(value, str) and value else None
    return None


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    temp_path.replace(path)


def _write_meta(
    roster: dict[str, Any],
    total_targets: int,
    cached_entities: int,
    skipped: int,
    failures: list[str],
) -> None:
    meta = {
        "generated_at": _timestamp(),
        "source": {
            "roster_version": roster["roster_version"],
            "valid_until": roster["valid_until"],
            "roster_counts": roster["counts"],
        },
        "target_entities": total_targets,
        "cached_entities": cached_entities,
        "skipped_entities": skipped,
        "failures": len(failures),
        "pokeapi_version": "v2",
    }
    _write_json(POKEMON_CACHE_META, meta)


def _write_failures(failures: list[str]) -> None:
    POKEMON_FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    if failures:
        POKEMON_FAILURE_LOG.write_text("\n".join(failures) + "\n", encoding="utf-8")
    elif POKEMON_FAILURE_LOG.exists():
        POKEMON_FAILURE_LOG.unlink()


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prefetch Champions Pokemon battle data.")
    parser.add_argument("--force", action="store_true", help="기존 캐시를 무시하고 재다운로드")
    parser.add_argument("--only", nargs="+", help="특정 entity_id만 갱신")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(force=args.force, only=args.only))
