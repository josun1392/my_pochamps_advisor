from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.canonical_move_metadata_common import (
    CANONICAL_SCHEMA_VERSION,
    canonical_json_bytes,
    derive_champions_legal_move_ids,
    legal_move_set_sha256,
    load_json,
    sha256_bytes,
    validate_exact_move_set,
    validate_move_id,
    validate_pokeapi_id,
    validate_priority,
)

MOVEPOOL_DIR = PROJECT_ROOT / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"
ARTIFACT_PATH = PROJECT_ROOT / "data" / "static" / "canonical_move_metadata_v1.json"
SOURCE_PATH = PROJECT_ROOT / "data" / "source" / "pokeapi" / "champions_move_metadata_snapshot_v1.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_canonical_metadata(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    movepool_dir: Path = MOVEPOOL_DIR,
    source_path: Path | None = None,
) -> dict[str, Any]:
    artifact_bytes = artifact_path.read_bytes()
    artifact = load_json(artifact_path)
    if artifact.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        raise ValueError(f"Unexpected canonical metadata schema: {artifact.get('schema_version')!r}")
    if artifact_bytes != canonical_json_bytes(artifact):
        raise ValueError("Canonical metadata serialization is not deterministic")

    legal_move_ids = derive_champions_legal_move_ids(movepool_dir)
    legal_hash = legal_move_set_sha256(legal_move_ids)

    scope = artifact.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("Canonical metadata scope block is missing")
    if scope.get("format") != "pokemon_champions" or scope.get("regulation") != "M-A":
        raise ValueError("Canonical metadata scope is not Champions regulation M-A")
    if scope.get("legal_move_count") != len(legal_move_ids):
        raise ValueError("Canonical metadata legal move count mismatch")
    if scope.get("legal_move_set_sha256") != legal_hash:
        raise ValueError("Canonical metadata legal move set SHA-256 mismatch")

    source = artifact.get("source")
    if not isinstance(source, dict):
        raise ValueError("Canonical metadata source block is missing")
    for key, expected in {
        "provider": "pokeapi",
        "api_family": "v2",
        "endpoint_family": "move",
        "normalizer": "PokeAPIFetcher._normalize_move",
    }.items():
        if source.get(key) != expected:
            raise ValueError(f"Invalid canonical source provenance {key}: {source.get(key)!r}")
    snapshot_sha256 = source.get("snapshot_sha256")
    if not isinstance(snapshot_sha256, str) or not _SHA256_RE.fullmatch(snapshot_sha256):
        raise ValueError("Canonical source snapshot SHA-256 is missing or malformed")
    if not isinstance(source.get("source_retrieved_at"), str) or not source["source_retrieved_at"]:
        raise ValueError("Canonical source retrieval timestamp is missing")
    if source_path is not None and sha256_bytes(source_path.read_bytes()) != snapshot_sha256:
        raise ValueError("Canonical source snapshot SHA-256 does not match source bytes")

    moves = artifact.get("moves")
    if not isinstance(moves, dict):
        raise ValueError("Canonical metadata moves must be an object")
    move_ids = list(moves)
    if move_ids != sorted(move_ids):
        raise ValueError("Canonical metadata move ids are not deterministically sorted")
    validate_exact_move_set(actual=move_ids, expected=legal_move_ids, label="canonical artifact")

    pokeapi_ids: set[int] = set()
    for move_id in move_ids:
        validate_move_id(move_id)
        row = moves[move_id]
        if not isinstance(row, dict):
            raise ValueError(f"Canonical move row must be an object: {move_id}")
        pokeapi_id = validate_pokeapi_id(row.get("pokeapi_id"), move_id=move_id)
        if pokeapi_id in pokeapi_ids:
            raise ValueError(f"Duplicate canonical PokeAPI id: {pokeapi_id}")
        pokeapi_ids.add(pokeapi_id)
        validate_priority(row.get("priority"), move_id=move_id)

    return {
        "status": "valid",
        "move_count": len(move_ids),
        "legal_move_set_sha256": legal_hash,
        "source_snapshot_sha256": snapshot_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify offline canonical move metadata against current Champions legality.")
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--movepool-dir", type=Path, default=MOVEPOOL_DIR)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    args = parser.parse_args()
    result = verify_canonical_metadata(
        artifact_path=args.artifact,
        movepool_dir=args.movepool_dir,
        source_path=args.source,
    )
    print("Canonical move metadata verification passed")
    print(f"coverage: {result['move_count']}/{result['move_count']}")
    print(f"legal move set sha256: {result['legal_move_set_sha256']}")
    print(f"source snapshot sha256: {result['source_snapshot_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
