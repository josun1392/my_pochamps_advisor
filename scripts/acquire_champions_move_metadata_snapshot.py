from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pokeapi_fetcher import PokeAPIFetcher
from scripts.canonical_move_metadata_common import (
    SOURCE_SCHEMA_VERSION,
    atomic_write_json,
    derive_champions_legal_move_ids,
    legal_move_set_sha256,
    records_by_move_id,
    validate_exact_move_set,
)

MOVEPOOL_DIR = PROJECT_ROOT / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"
OUTPUT_PATH = PROJECT_ROOT / "data" / "source" / "pokeapi" / "champions_move_metadata_snapshot_v1.json"
POKEAPI_MOVE_URL = "https://pokeapi.co/api/v2/move/{move_id}/"
USER_AGENT = "PokemonCopilot/0.1 canonical move metadata acquisition"

RawMoveFetcher = Callable[[str], dict[str, Any]]


def acquire_snapshot(
    *,
    movepool_dir: Path = MOVEPOOL_DIR,
    output_path: Path = OUTPUT_PATH,
    fetch_raw_move: RawMoveFetcher,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    move_ids = derive_champions_legal_move_ids(movepool_dir)

    records: list[dict[str, Any]] = []
    for move_id in move_ids:
        raw = fetch_raw_move(move_id)
        if not isinstance(raw, dict):
            raise ValueError(f"PokeAPI move response must be an object: {move_id}")
        normalized = PokeAPIFetcher._normalize_move(raw)
        normalized.pop("_fetched_at", None)
        if normalized.get("name") != move_id:
            raise ValueError(
                f"Requested/returned move identity mismatch: requested={move_id} returned={normalized.get('name')!r}"
            )
        records.append(normalized)

    by_move_id = records_by_move_id(records)
    validate_exact_move_set(actual=by_move_id, expected=move_ids, label="acquisition")
    if len(records) != len(move_ids):
        raise ValueError(f"Requested/normalized move count mismatch: {len(move_ids)} != {len(records)}")

    timestamp = retrieved_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    snapshot = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "source": {
            "provider": "pokeapi",
            "api_family": "v2",
            "endpoint_family": "move",
            "retrieved_at": timestamp,
            "normalizer": "PokeAPIFetcher._normalize_move",
        },
        "requested_legal_move_count": len(move_ids),
        "legal_move_set_sha256": legal_move_set_sha256(move_ids),
        "normalized_record_count": len(records),
        "records": [by_move_id[move_id] for move_id in move_ids],
    }
    atomic_write_json(output_path, snapshot)
    return snapshot


def _network_fetcher() -> RawMoveFetcher:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    def fetch(move_id: str) -> dict[str, Any]:
        response = session.get(POKEAPI_MOVE_URL.format(move_id=move_id), timeout=20)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"PokeAPI response is not an object: {move_id}")
        return data

    return fetch


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-time network-capable acquisition of normalized PokeAPI metadata for the current Champions legal move set."
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--movepool-dir", type=Path, default=MOVEPOOL_DIR)
    args = parser.parse_args()

    snapshot = acquire_snapshot(
        movepool_dir=args.movepool_dir,
        output_path=args.output,
        fetch_raw_move=_network_fetcher(),
    )
    print(f"source snapshot: {args.output}")
    print(f"coverage: {snapshot['normalized_record_count']}/{snapshot['requested_legal_move_count']}")
    print(f"legal move set sha256: {snapshot['legal_move_set_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
