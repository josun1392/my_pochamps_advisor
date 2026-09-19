"""Pinned canonical Persim Berry family for Fling confusion cure."""
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


SCHEMA_VERSION = "canonical-fling-persim-confusion-cure-berry-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
_SOURCE_PATH = "data/items.ts"
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT / "items.ts"
_ITEM_ID = "persim-berry"
_SHOWDOWN_ID = "persimberry"


@lru_cache(maxsize=1)
def _source_binding() -> tuple[dict[str, Any] | None, str | None]:
    if COMMIT != FLING_BERRY_COMMIT:
        return None, "fling_persim_commit_binding_mismatch"
    try:
        raw = _VENDOR.read_bytes()
    except OSError:
        return None, "fling_persim_pinned_source_missing"
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_ITEMS_SHA256:
        return None, "fling_persim_pinned_source_hash_mismatch"
    text = raw.decode("utf-8")
    marker = f"\n\t{_SHOWDOWN_ID}: {{"
    start = text.find(marker)
    if start < 0:
        return None, "fling_persim_source_item_missing"
    next_item = re.search(r"\n\t[a-z0-9]+: \{", text[start + len(marker):])
    end = len(text) if next_item is None else start + len(marker) + next_item.start()
    block = text[start:end]
    required = (
        "isBerry: true",
        "if (pokemon.volatiles['confusion'])",
        "pokemon.eatItem();",
        "onEat(pokemon)",
        "pokemon.removeVolatile('confusion');",
    )
    if any(token not in block for token in required):
        return None, "fling_persim_confusion_cure_contract_changed"
    return {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "source_path": _SOURCE_PATH,
        "local_snapshot": f"data/vendor/pokemon_showdown/{COMMIT}/items.ts",
        "sha256": digest,
        "source_item_id": _SHOWDOWN_ID,
        "held_update_trigger": "confusion_present_then_eat_item",
        "intrinsic_on_eat": "remove_confusion_volatile",
    }, None


def resolve_canonical_fling_persim_confusion_cure_berry(item_id: Any) -> dict[str, Any]:
    source, error = _source_binding()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "fling_persim_item_identity_unknown"}
    if item_id != _ITEM_ID:
        return {
            "status": "not_applicable",
            "item_id": item_id,
            "reason": "fling_item_not_persim_confusion_cure_berry",
        }
    berry = resolve_canonical_fling_berry_item_identity(item_id)
    metadata = resolve_canonical_fling_item_metadata(item_id)
    if berry.get("status") != "resolved":
        return {
            "status": "rejected",
            "item_id": item_id,
            "reason": berry.get("reason", "fling_persim_berry_identity_binding_invalid"),
        }
    if (
        metadata.get("status") != "resolved"
        or metadata.get("item_id") != _ITEM_ID
        or metadata.get("flingable") is not True
        or metadata.get("base_power") != 10
        or metadata.get("effect", {}).get("kind") != "berry_effect"
        or metadata.get("effect", {}).get("item_id") != _SHOWDOWN_ID
        or metadata.get("support_status") != "unsupported_now"
        or metadata.get("source", {}).get("upstream_item_id") != _SHOWDOWN_ID
        or metadata.get("source", {}).get("upstream_commit") != COMMIT
    ):
        return {
            "status": "rejected",
            "item_id": item_id,
            "reason": "fling_persim_manifest_binding_invalid",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "item_id": _ITEM_ID,
        "showdown_item_id": _SHOWDOWN_ID,
        "effect_family": "persim_confusion_cure",
        "fling_base_power": 10,
        "is_berry": True,
        "intrinsic_on_eat": "remove_confusion_volatile",
        "berry_identity_authority": berry,
        "fling_item_metadata": metadata,
        "source_provenance": source,
        "provenance": "pinned_showdown_fling_persim_confusion_cure_berry_v1",
    }
