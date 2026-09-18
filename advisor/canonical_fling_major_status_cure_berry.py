"""Pinned canonical family for Flinged single-major-status cure Berries."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.canonical_fling_berry_eat_item_interactions import (
    COMMIT as FLING_BERRY_COMMIT,
    resolve_canonical_fling_berry_item_identity,
)
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata


SCHEMA_VERSION = "canonical-fling-major-status-cure-berry-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
_SOURCE_PATH = "data/items.ts"
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT / "items.ts"

_FAMILY: dict[str, tuple[str, ...]] = {
    "cheri-berry": ("paralysis",),
    "chesto-berry": ("sleep",),
    "aspear-berry": ("freeze",),
    "pecha-berry": ("poison", "toxic"),
    "rawst-berry": ("burn",),
}


@lru_cache(maxsize=1)
def _source_binding() -> tuple[dict[str, str] | None, str | None]:
    if COMMIT != FLING_BERRY_COMMIT:
        return None, "fling_status_cure_berry_commit_binding_mismatch"
    try:
        digest = hashlib.sha256(_VENDOR.read_bytes()).hexdigest()
    except OSError:
        return None, "fling_status_cure_berry_pinned_source_missing"
    if digest != EXPECTED_ITEMS_SHA256:
        return None, "fling_status_cure_berry_pinned_source_hash_mismatch"
    return {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "source_path": _SOURCE_PATH,
        "local_snapshot": f"data/vendor/pokemon_showdown/{COMMIT}/items.ts",
        "sha256": digest,
    }, None


def resolve_canonical_fling_major_status_cure_berry(item_id: Any) -> dict[str, Any]:
    """Resolve only the five pinned single-major-status cure Berry families."""
    source, error = _source_binding()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "fling_status_cure_berry_item_identity_unknown"}
    removable = _FAMILY.get(item_id)
    if removable is None:
        return {
            "status": "not_applicable",
            "item_id": item_id,
            "reason": "fling_item_not_single_major_status_cure_berry",
        }
    berry = resolve_canonical_fling_berry_item_identity(item_id)
    metadata = resolve_canonical_fling_item_metadata(item_id)
    if berry.get("status") != "resolved":
        return {
            "status": "rejected",
            "item_id": item_id,
            "reason": berry.get("reason", "fling_status_cure_berry_identity_binding_invalid"),
        }
    if (
        metadata.get("status") != "resolved"
        or metadata.get("item_id") != item_id
        or metadata.get("effect", {}).get("kind") != "berry_effect"
        or metadata.get("source", {}).get("upstream_commit") != COMMIT
    ):
        return {
            "status": "rejected",
            "item_id": item_id,
            "reason": "fling_status_cure_berry_manifest_binding_invalid",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "item_id": item_id,
        "effect_family": "single_major_status_cure",
        "removable_conditions": removable,
        "berry_identity_authority": berry,
        "fling_item_metadata": metadata,
        "source_provenance": source,
        "provenance": "pinned_showdown_fling_major_status_cure_berry_v1",
    }


def canonical_fling_major_status_cure_berry_ids() -> tuple[str, ...]:
    return tuple(_FAMILY)
