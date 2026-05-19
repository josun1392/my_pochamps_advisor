from __future__ import annotations

import json
from pathlib import Path

from core.champions_move_overrides import ChampionsMoveOverrides


def test_static_fixture_denies_tera_blast_with_source_metadata() -> None:
    overrides = ChampionsMoveOverrides()

    assert overrides.is_denied("tera-blast")
    metadata = overrides.metadata_for("tera-blast")
    assert metadata is not None
    assert metadata["source"] == "bulbapedia"
    assert metadata["confidence"] == "single_source"
    assert metadata["fetched_at"]


def test_filter_allowed_move_ids_removes_denied_moves(tmp_path: Path) -> None:
    path = _write_overrides(tmp_path, denied_moves={"tera-blast": {"source": "fixture"}})
    overrides = ChampionsMoveOverrides(path)

    filtered = overrides.filter_allowed_move_ids({"shadow-ball", "tera-blast", "ice-beam"})

    assert filtered == {"shadow-ball", "ice-beam"}


def test_missing_override_file_allows_existing_candidates(tmp_path: Path) -> None:
    overrides = ChampionsMoveOverrides(tmp_path / "missing.json")

    assert overrides.filter_allowed_move_ids({"tera-blast", "ice-beam"}) == {"tera-blast", "ice-beam"}


def _write_overrides(tmp_path: Path, denied_moves: dict) -> Path:
    path = tmp_path / "champions_move_overrides.json"
    data = {
        "schema_version": "champions-global-move-overrides-v1",
        "format": "pokemon_champions",
        "ruleset": "test",
        "sources": [],
        "global_denied_moves": denied_moves,
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file)
    return path
