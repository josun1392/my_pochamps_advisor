from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.canonical_move_metadata_common import (
    CANONICAL_SCHEMA_VERSION,
    SOURCE_SCHEMA_VERSION,
    atomic_write_json,
    derive_champions_legal_move_ids,
    legal_move_set_sha256,
    load_json,
    records_by_move_id,
    sha256_bytes,
    validate_exact_move_set,
    validate_pokeapi_id,
    validate_priority,
)

MOVEPOOL_DIR = PROJECT_ROOT / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"
SOURCE_PATH = PROJECT_ROOT / "data" / "source" / "pokeapi" / "champions_move_metadata_snapshot_v1.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "static" / "canonical_move_metadata_v1.json"


def build_canonical_metadata(
    *,
    source_path: Path = SOURCE_PATH,
    movepool_dir: Path = MOVEPOOL_DIR,
    output_path: Path = OUTPUT_PATH,
) -> dict[str, Any]:
    legal_move_ids = derive_champions_legal_move_ids(movepool_dir)
    legal_hash = legal_move_set_sha256(legal_move_ids)

    source_bytes = source_path.read_bytes()
    snapshot = load_json(source_path)
    if snapshot.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise ValueError(f"Unexpected source snapshot schema: {snapshot.get('schema_version')!r}")
    source = snapshot.get("source")
    if not isinstance(source, dict):
        raise ValueError("Source snapshot provenance block is missing")
    for key, expected in {
        "provider": "pokeapi",
        "api_family": "v2",
        "endpoint_family": "move",
        "normalizer": "PokeAPIFetcher._normalize_move",
    }.items():
        if source.get(key) != expected:
            raise ValueError(f"Invalid source provenance {key}: {source.get(key)!r}")
    retrieved_at = source.get("retrieved_at")
    if not isinstance(retrieved_at, str) or not retrieved_at:
        raise ValueError("Source retrieved_at is missing")

    if snapshot.get("requested_legal_move_count") != len(legal_move_ids):
        raise ValueError("Source requested legal move count does not match current Champions legal set")
    if snapshot.get("legal_move_set_sha256") != legal_hash:
        raise ValueError("Source legal move set SHA-256 does not match current Champions legal set")

    records = records_by_move_id(snapshot.get("records"))
    if snapshot.get("normalized_record_count") != len(records):
        raise ValueError("Source normalized record count does not match source records")
    validate_exact_move_set(actual=records, expected=legal_move_ids, label="source snapshot")

    moves: dict[str, dict[str, int]] = {}
    for move_id in legal_move_ids:
        record = records[move_id]
        moves[move_id] = {
            "pokeapi_id": validate_pokeapi_id(record.get("id"), move_id=move_id),
            "priority": validate_priority(record.get("priority"), move_id=move_id),
        }

    artifact = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "scope": {
            "format": "pokemon_champions",
            "regulation": "M-A",
            "legal_move_count": len(legal_move_ids),
            "legal_move_set_sha256": legal_hash,
        },
        "source": {
            "provider": "pokeapi",
            "api_family": "v2",
            "endpoint_family": "move",
            "snapshot_sha256": sha256_bytes(source_bytes),
            "source_retrieved_at": retrieved_at,
            "normalizer": source["normalizer"],
        },
        "moves": moves,
    }
    atomic_write_json(output_path, artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Build offline canonical move metadata from a local source snapshot.")
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument("--movepool-dir", type=Path, default=MOVEPOOL_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    artifact = build_canonical_metadata(
        source_path=args.source,
        movepool_dir=args.movepool_dir,
        output_path=args.output,
    )
    print(f"canonical artifact: {args.output}")
    print(f"coverage: {len(artifact['moves'])}/{artifact['scope']['legal_move_count']}")
    print(f"source snapshot sha256: {artifact['source']['snapshot_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
