from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.acquire_champions_move_metadata_snapshot import acquire_snapshot
from scripts.build_canonical_move_metadata import build_canonical_metadata
from scripts.canonical_move_metadata_common import (
    atomic_write_json,
    canonical_json_bytes,
    derive_champions_legal_move_ids,
    legal_move_set_sha256,
)
from scripts.verify_canonical_move_metadata import verify_canonical_metadata


def _write_movepools(root: Path, move_ids: list[str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        root / "sample.json",
        {
            "pokemon_id": "sample",
            "format": "pokemon_champions",
            "regulation": "M-A",
            "moves": [{"move_id": move_id} for move_id in move_ids],
        },
    )


def _raw_move(name: str, identifier: int, priority: object) -> dict:
    return {
        "id": identifier,
        "name": name,
        "names": [{"language": {"name": "en"}, "name": name.replace("-", " ").title()}],
        "type": {"name": "normal"},
        "damage_class": {"name": "physical"},
        "power": 40,
        "accuracy": 100,
        "pp": 20,
        "priority": priority,
        "effect_chance": None,
        "target": {"name": "selected-pokemon"},
        "meta": {
            "ailment": {"name": "none"},
            "category": {"name": "damage"},
            "drain": 0,
            "healing": 0,
            "min_hits": None,
            "max_hits": None,
        },
        "stat_changes": [],
    }


def _valid_source(tmp_path: Path) -> tuple[Path, Path, dict]:
    movepools = tmp_path / "movepools"
    source = tmp_path / "source.json"
    _write_movepools(movepools, ["earthquake", "quick-attack"])
    rows = {
        "earthquake": _raw_move("earthquake", 89, 0),
        "quick-attack": _raw_move("quick-attack", 98, 1),
    }
    snapshot = acquire_snapshot(
        movepool_dir=movepools,
        output_path=source,
        fetch_raw_move=lambda move_id: deepcopy(rows[move_id]),
        retrieved_at="2026-09-28T00:00:00Z",
    )
    return movepools, source, snapshot


def test_current_authoritative_champions_legal_move_union_is_490() -> None:
    project_root = Path(__file__).resolve().parents[1]
    movepools = project_root / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"
    assert len(derive_champions_legal_move_ids(movepools)) == 490


def test_legal_set_comes_only_from_movepools_not_stale_mapping(tmp_path: Path) -> None:
    movepools = tmp_path / "movepools"
    _write_movepools(movepools, ["earthquake"])
    (tmp_path / "ko_mapping.json").write_text(
        json.dumps({"moves": {"earthquake": "지진", "historical-extra": "과거기술"}}),
        encoding="utf-8",
    )
    assert derive_champions_legal_move_ids(movepools) == ["earthquake"]


def test_legal_set_applies_global_denied_move_semantics_and_hash_is_deterministic(tmp_path: Path) -> None:
    movepools = tmp_path / "movepools"
    _write_movepools(movepools, ["quick-attack", "tera-blast", "earthquake"])
    move_ids = derive_champions_legal_move_ids(movepools)
    assert move_ids == ["earthquake", "quick-attack"]
    assert legal_move_set_sha256(move_ids) == legal_move_set_sha256(reversed(move_ids))


def test_acquisition_is_offline_injectable_complete_and_deterministic(tmp_path: Path) -> None:
    movepools = tmp_path / "movepools"
    _write_movepools(movepools, ["quick-attack", "earthquake"])
    rows = {
        "earthquake": _raw_move("earthquake", 89, 0),
        "quick-attack": _raw_move("quick-attack", 98, 1),
    }
    calls: list[str] = []

    def fetch(move_id: str) -> dict:
        calls.append(move_id)
        return deepcopy(rows[move_id])

    first_path, second_path = tmp_path / "a.json", tmp_path / "b.json"
    first = acquire_snapshot(
        movepool_dir=movepools,
        output_path=first_path,
        fetch_raw_move=fetch,
        retrieved_at="2026-09-28T00:00:00Z",
    )
    second = acquire_snapshot(
        movepool_dir=movepools,
        output_path=second_path,
        fetch_raw_move=fetch,
        retrieved_at="2026-09-28T00:00:00Z",
    )
    assert calls[:2] == ["earthquake", "quick-attack"]
    assert first["requested_legal_move_count"] == first["normalized_record_count"] == 2
    assert [row["name"] for row in first["records"]] == ["earthquake", "quick-attack"]
    assert "target" in first["records"][0] and "meta" in first["records"][0]
    assert "_fetched_at" not in first["records"][0]
    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()


@pytest.mark.parametrize("bad_priority", [None, True, "0", 8, -8])
def test_acquisition_rejects_invalid_priority_without_overwriting_existing_snapshot(
    tmp_path: Path, bad_priority: object,
) -> None:
    movepools = tmp_path / "movepools"
    output = tmp_path / "source.json"
    _write_movepools(movepools, ["earthquake"])
    output.write_bytes(b"previous-valid-snapshot\n")
    with pytest.raises(ValueError):
        acquire_snapshot(
            movepool_dir=movepools,
            output_path=output,
            fetch_raw_move=lambda _move_id: _raw_move("earthquake", 89, bad_priority),
            retrieved_at="2026-09-28T00:00:00Z",
        )
    assert output.read_bytes() == b"previous-valid-snapshot\n"
    assert not output.with_suffix(".json.tmp").exists()


def test_acquisition_rejects_identity_duplicate_and_partial_failure_atomically(tmp_path: Path) -> None:
    movepools = tmp_path / "movepools"
    output = tmp_path / "source.json"
    _write_movepools(movepools, ["earthquake", "quick-attack"])

    with pytest.raises(ValueError, match="identity mismatch"):
        acquire_snapshot(
            movepool_dir=movepools,
            output_path=output,
            fetch_raw_move=lambda move_id: _raw_move("wrong-move", 89, 0)
            if move_id == "earthquake"
            else _raw_move(move_id, 98, 1),
            retrieved_at="2026-09-28T00:00:00Z",
        )

    with pytest.raises(ValueError, match="Duplicate normalized PokeAPI id"):
        acquire_snapshot(
            movepool_dir=movepools,
            output_path=output,
            fetch_raw_move=lambda move_id: _raw_move(move_id, 89, 0 if move_id == "earthquake" else 1),
            retrieved_at="2026-09-28T00:00:00Z",
        )

    output.write_bytes(b"keep-me\n")

    def partial(move_id: str) -> dict:
        if move_id == "quick-attack":
            raise RuntimeError("simulated retrieval failure")
        return _raw_move(move_id, 89, 0)

    with pytest.raises(RuntimeError, match="simulated retrieval failure"):
        acquire_snapshot(
            movepool_dir=movepools,
            output_path=output,
            fetch_raw_move=partial,
            retrieved_at="2026-09-28T00:00:00Z",
        )
    assert output.read_bytes() == b"keep-me\n"


def test_offline_builder_and_verifier_exact_set_success(tmp_path: Path) -> None:
    movepools, source, _snapshot = _valid_source(tmp_path)
    artifact_path = tmp_path / "canonical.json"
    artifact = build_canonical_metadata(
        source_path=source, movepool_dir=movepools, output_path=artifact_path,
    )
    assert artifact["moves"]["earthquake"] == {"pokeapi_id": 89, "priority": 0}
    assert artifact["moves"]["quick-attack"] == {"pokeapi_id": 98, "priority": 1}
    result = verify_canonical_metadata(
        artifact_path=artifact_path, movepool_dir=movepools, source_path=source,
    )
    assert result["status"] == "valid"
    assert result["move_count"] == 2
    assert artifact_path.read_bytes() == canonical_json_bytes(artifact)


def test_builder_rejects_missing_and_extra_source_rows(tmp_path: Path) -> None:
    movepools, source, snapshot = _valid_source(tmp_path)
    artifact = tmp_path / "canonical.json"

    missing = deepcopy(snapshot)
    missing["records"] = missing["records"][:-1]
    missing["normalized_record_count"] = 1
    atomic_write_json(source, missing)
    with pytest.raises(ValueError, match="source snapshot move-set mismatch"):
        build_canonical_metadata(source_path=source, movepool_dir=movepools, output_path=artifact)

    extra = deepcopy(snapshot)
    extra["records"].append({**deepcopy(snapshot["records"][0]), "id": 999, "name": "extra-move"})
    extra["normalized_record_count"] = 3
    atomic_write_json(source, extra)
    with pytest.raises(ValueError, match="source snapshot move-set mismatch"):
        build_canonical_metadata(source_path=source, movepool_dir=movepools, output_path=artifact)


@pytest.mark.parametrize("bad_priority", [None, True, "0", 8, -8])
def test_builder_rejects_invalid_priority(tmp_path: Path, bad_priority: object) -> None:
    movepools, source, snapshot = _valid_source(tmp_path)
    snapshot["records"][0]["priority"] = bad_priority
    atomic_write_json(source, snapshot)
    with pytest.raises(ValueError, match="Priority"):
        build_canonical_metadata(
            source_path=source, movepool_dir=movepools, output_path=tmp_path / "canonical.json",
        )


def test_verifier_rejects_set_hash_source_hash_and_noncanonical_serialization(tmp_path: Path) -> None:
    movepools, source, _snapshot = _valid_source(tmp_path)
    artifact_path = tmp_path / "canonical.json"
    artifact = build_canonical_metadata(
        source_path=source, movepool_dir=movepools, output_path=artifact_path,
    )

    broken = deepcopy(artifact)
    broken["scope"]["legal_move_set_sha256"] = "0" * 64
    atomic_write_json(artifact_path, broken)
    with pytest.raises(ValueError, match="legal move set SHA-256"):
        verify_canonical_metadata(
            artifact_path=artifact_path, movepool_dir=movepools, source_path=source,
        )

    atomic_write_json(artifact_path, artifact)
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(ValueError, match="source snapshot SHA-256"):
        verify_canonical_metadata(
            artifact_path=artifact_path, movepool_dir=movepools, source_path=source,
        )

    source.write_bytes(source.read_bytes()[:-1])
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="serialization"):
        verify_canonical_metadata(
            artifact_path=artifact_path, movepool_dir=movepools, source_path=None,
        )
