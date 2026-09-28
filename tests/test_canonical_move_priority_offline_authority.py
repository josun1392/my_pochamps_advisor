from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.cache_manager import CacheManager
from core.canonical_move_metadata import CanonicalMoveMetadataRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository
from core.pokeapi_fetcher import PokeAPIFetcher


def _write_artifact(path: Path, moves: dict[str, dict[str, object]]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": "canonical-move-metadata-v1",
                "scope": {
                    "format": "pokemon_champions",
                    "regulation": "M-A",
                    "legal_move_count": len(moves),
                    "legal_move_set_sha256": "0" * 64,
                },
                "source": {
                    "provider": "pokeapi",
                    "api_family": "v2",
                    "endpoint_family": "move",
                    "snapshot_sha256": "1" * 64,
                    "source_retrieved_at": "2026-09-28T00:00:00Z",
                    "normalizer": "PokeAPIFetcher._normalize_move",
                },
                "moves": moves,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _raw_move(name: str, identifier: int, priority: object) -> dict:
    return {
        "id": identifier,
        "name": name,
        "names": [],
        "type": {"name": "normal"},
        "damage_class": {"name": "physical"},
        "power": 40,
        "accuracy": 100,
        "pp": 20,
        "priority": priority,
        "target": {"name": "selected-pokemon"},
        "meta": {},
        "stat_changes": [],
    }


def test_default_repository_supplies_real_canonical_priorities() -> None:
    repository = MoveRepository(CacheManager(), KoMappingLoader())

    assert repository.get("earthquake").priority == 0
    assert repository.get("quick-attack").priority == 1
    assert repository.get("thunderbolt").priority == 0


def test_canonical_repository_rejects_missing_and_malformed_priority(tmp_path: Path) -> None:
    missing_path = _write_artifact(tmp_path / "missing.json", {"earthquake": {"pokeapi_id": 89}})
    with pytest.raises(RuntimeError, match="explicit integer"):
        CanonicalMoveMetadataRepository(missing_path)

    for index, bad in enumerate((None, True, "0", 8, -8), start=1):
        path = _write_artifact(
            tmp_path / f"bad-{index}.json",
            {"earthquake": {"pokeapi_id": 89, "priority": bad}},
        )
        with pytest.raises(RuntimeError):
            CanonicalMoveMetadataRepository(path)


def test_missing_canonical_move_fails_closed_before_fallback(tmp_path: Path) -> None:
    artifact_path = _write_artifact(
        tmp_path / "canonical.json",
        {"quick-attack": {"pokeapi_id": 98, "priority": 1}},
    )
    repository = MoveRepository(
        CacheManager(),
        KoMappingLoader(),
        canonical_move_metadata=CanonicalMoveMetadataRepository(artifact_path),
    )

    with pytest.raises(RuntimeError, match="Canonical move priority is unavailable: earthquake"):
        repository.get("earthquake")


def test_cached_priority_conflict_fails_explicitly(tmp_path: Path) -> None:
    artifact_path = _write_artifact(
        tmp_path / "canonical.json",
        {"quick-attack": {"pokeapi_id": 98, "priority": 1}},
    )
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    cache.put("moves", 98, PokeAPIFetcher._normalize_move(_raw_move("quick-attack", 98, 0)))
    repository = MoveRepository(
        cache,
        KoMappingLoader(),
        canonical_move_metadata=CanonicalMoveMetadataRepository(artifact_path),
    )

    with pytest.raises(RuntimeError, match="Move priority metadata conflict"):
        repository.get("quick-attack")


def test_cached_priority_agreement_uses_canonical_value(tmp_path: Path) -> None:
    artifact_path = _write_artifact(
        tmp_path / "canonical.json",
        {
            "quick-attack": {"pokeapi_id": 98, "priority": 1},
            "thunderbolt": {"pokeapi_id": 85, "priority": 0},
        },
    )
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    cache.put("moves", 98, PokeAPIFetcher._normalize_move(_raw_move("quick-attack", 98, 1)))
    cache.put("moves", 85, PokeAPIFetcher._normalize_move(_raw_move("thunderbolt", 85, 0)))
    repository = MoveRepository(
        cache,
        KoMappingLoader(),
        canonical_move_metadata=CanonicalMoveMetadataRepository(artifact_path),
    )

    assert repository.get("quick-attack").priority == 1
    assert repository.get("thunderbolt").priority == 0
