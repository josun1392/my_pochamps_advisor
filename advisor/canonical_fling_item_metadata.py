"""Read-only resolver for the frozen Champions Fling metadata inventory."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "fling_item_effects.json"


@lru_cache(maxsize=1)
def _manifest() -> tuple[dict[str, Any] | None, str | None]:
    try: raw = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return None, "fling_manifest_unavailable"
    provenance, rows = raw.get("source_provenance"), raw.get("items")
    if not isinstance(provenance, Mapping) or not isinstance(rows, list) or raw.get("champions_item_universe_count") != 117 or len(rows) != 117: return None, "fling_manifest_shape_invalid"
    ids = [row.get("item_id") for row in rows if isinstance(row, Mapping)]
    if len(ids) != len(rows) or len(set(ids)) != 117 or any(not isinstance(item, str) or not item for item in ids): return None, "fling_manifest_duplicate_or_invalid_id"
    snapshot = _PATH.parents[1] / "vendor" / "pokemon_showdown" / provenance.get("commit_sha", "") / "items.ts"
    if not isinstance(provenance.get("sha256"), str) or not snapshot.is_file() or hashlib.sha256(snapshot.read_bytes()).hexdigest() != provenance["sha256"]: return None, "fling_manifest_source_checksum_mismatch"
    parsed = {row["item_id"]: dict(row) for row in rows}
    for row in parsed.values():
        flingable, power, effect = row.get("flingable"), row.get("base_power"), row.get("effect")
        if not isinstance(flingable, bool) or not isinstance(effect, Mapping) or effect.get("kind") not in {"none", "major_status", "flinch", "berry_effect", "known_unsupported"}: return None, "fling_manifest_effect_invalid"
        if flingable is not (isinstance(power, int) and not isinstance(power, bool) and power > 0): return None, "fling_manifest_power_invalid"
    return parsed, None


def resolve_canonical_fling_item_metadata(item_id: Any) -> dict[str, Any]:
    manifest, error = _manifest()
    if error: return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id: return {"status": "incomplete", "reason": "fling_item_identity_unknown"}
    row = manifest.get(item_id)
    if row is None: return {"status": "incomplete", "item_id": item_id, "reason": "fling_item_not_in_frozen_champions_manifest"}
    return {"status": "resolved", **row, "provenance": "frozen_pinned_showdown_fling_metadata_v1"}
