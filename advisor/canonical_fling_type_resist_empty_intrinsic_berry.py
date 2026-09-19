"""Pinned canonical family for Flinged type-resist Berries with empty intrinsic onEat."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.canonical_fling_berry_eat_item_interactions import (
    COMMIT as FLING_BERRY_COMMIT,
    resolve_canonical_fling_berry_item_identity,
)
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata


SCHEMA_VERSION = "canonical-fling-type-resist-empty-intrinsic-berry-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
_SOURCE_PATH = "data/items.ts"
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT / "items.ts"

_FAMILY = (
    "babiri-berry", "charti-berry", "chilan-berry", "chople-berry",
    "coba-berry", "colbur-berry", "haban-berry", "kasib-berry",
    "kebia-berry", "occa-berry", "passho-berry", "payapa-berry",
    "rindo-berry", "roseli-berry", "shuca-berry", "tanga-berry",
    "wacan-berry", "yache-berry",
)


def _showdown_id(item_id: str) -> str:
    return item_id.replace("-", "")


def _item_block(text: str, showdown_id: str) -> str | None:
    marker = f"\n\t{showdown_id}: {{"
    start = text.find(marker)
    if start < 0:
        return None
    match = re.search(r"\n\t[a-z0-9]+: \{", text[start + len(marker):])
    end = len(text) if match is None else start + len(marker) + match.start()
    return text[start:end]


@lru_cache(maxsize=1)
def _source_binding() -> tuple[dict[str, Any] | None, str | None]:
    if COMMIT != FLING_BERRY_COMMIT:
        return None, "fling_type_resist_berry_commit_binding_mismatch"
    try:
        raw = _VENDOR.read_bytes()
    except OSError:
        return None, "fling_type_resist_berry_pinned_source_missing"
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_ITEMS_SHA256:
        return None, "fling_type_resist_berry_pinned_source_hash_mismatch"
    text = raw.decode("utf-8")
    proofs: dict[str, dict[str, Any]] = {}
    for item_id in _FAMILY:
        upstream = _showdown_id(item_id)
        block = _item_block(text, upstream)
        if block is None:
            return None, "fling_type_resist_berry_source_item_missing"
        if (
            "isBerry: true" not in block
            or "onSourceModifyDamage(" not in block
            or "target.eatItem()" not in block
            or "onEat() { }" not in block
        ):
            return None, "fling_type_resist_berry_empty_intrinsic_contract_changed"
        proofs[item_id] = {
            "upstream_item_id": upstream,
            "is_berry": True,
            "held_resist_hook_present": True,
            "intrinsic_on_eat": "empty",
        }
    return {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "source_path": _SOURCE_PATH,
        "local_snapshot": f"data/vendor/pokemon_showdown/{COMMIT}/items.ts",
        "sha256": digest,
        "item_proofs": proofs,
    }, None


def resolve_canonical_fling_type_resist_empty_intrinsic_berry(
    item_id: Any,
) -> dict[str, Any]:
    """Resolve exactly the 18 pinned resist Berries whose intrinsic onEat is empty."""
    source, error = _source_binding()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "fling_type_resist_berry_item_identity_unknown"}
    if item_id not in _FAMILY:
        return {
            "status": "not_applicable",
            "item_id": item_id,
            "reason": "fling_item_not_type_resist_empty_intrinsic_berry",
        }
    berry = resolve_canonical_fling_berry_item_identity(item_id)
    metadata = resolve_canonical_fling_item_metadata(item_id)
    proof = source["item_proofs"][item_id]
    if berry.get("status") != "resolved":
        return {
            "status": "rejected", "item_id": item_id,
            "reason": berry.get("reason", "fling_type_resist_berry_identity_binding_invalid"),
        }
    if (
        metadata.get("status") != "resolved"
        or metadata.get("item_id") != item_id
        or metadata.get("flingable") is not True
        or metadata.get("base_power") != 10
        or metadata.get("effect", {}).get("kind") != "berry_effect"
        or metadata.get("effect", {}).get("item_id") != proof["upstream_item_id"]
        or metadata.get("support_status") != "unsupported_now"
        or metadata.get("source", {}).get("upstream_item_id") != proof["upstream_item_id"]
        or metadata.get("source", {}).get("upstream_commit") != COMMIT
    ):
        return {
            "status": "rejected", "item_id": item_id,
            "reason": "fling_type_resist_berry_manifest_binding_invalid",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "item_id": item_id,
        "showdown_item_id": proof["upstream_item_id"],
        "effect_family": "type_resist_empty_intrinsic",
        "fling_base_power": 10,
        "is_berry": True,
        "intrinsic_on_eat": "empty",
        "held_resist_hook_present": True,
        "berry_identity_authority": berry,
        "fling_item_metadata": metadata,
        "source_provenance": {
            key: value for key, value in source.items() if key != "item_proofs"
        },
        "source_item_proof": proof,
        "provenance": "pinned_showdown_fling_type_resist_empty_intrinsic_berry_v1",
    }


def canonical_fling_type_resist_empty_intrinsic_berry_ids() -> tuple[str, ...]:
    return _FAMILY
